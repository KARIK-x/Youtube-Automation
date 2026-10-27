"""Quality control checks for rendered Shorts."""
import os, subprocess, json

def ffprobe_streams(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,codec_name,width,height,r_frame_rate",
                        "-of","json", path], capture_output=True, text=True)
    return json.loads(r.stdout).get("streams", [])

def probe_duration(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json", path],
                       capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])

def qc(path, cfg):
    result = {"path": path, "passed": True, "checks": {}, "errors": []}
    if not os.path.exists(path):
        result["passed"]=False; result["errors"].append("file missing"); return result
    streams = ffprobe_streams(path)
    v = [s for s in streams if s["codec_type"]=="video"]
    a = [s for s in streams if s["codec_type"]=="audio"]
    result["checks"]["has_video"] = bool(v)
    result["checks"]["has_audio"] = bool(a)
    if not v: result["passed"]=False; result["errors"].append("no video stream")
    if not a: result["passed"]=False; result["errors"].append("no audio stream")
    if v:
        w,h = v[0].get("width"), v[0].get("height")
        result["checks"]["dimensions"] = f"{w}x{h}"
        if (w,h) != (cfg["video"]["width"], cfg["video"]["height"]):
            result["passed"]=False; result["errors"].append(f"bad dims {w}x{h}")
    dur = probe_duration(path)
    result["checks"]["duration"] = dur
    vmin, vmax = cfg["video"]["short_min"], cfg["video"]["short_max"]
    if not (vmin <= dur <= vmax):
        result["passed"]=False; result["errors"].append(f"duration {dur:.2f} not in [{vmin},{vmax}]")
    # black frame check (ffmpeg blackdetect)
    r = subprocess.run(["ffmpeg","-i",path,"-vf","blackdetect=d=0.5:pix_th=0.10","-an","-f","null","-"],
                       capture_output=True, text=True)
    blacks = r.stderr.count("blackdetect")
    result["checks"]["black_segments"] = blacks
    if blacks > 3:
        result["passed"]=False; result["errors"].append(f"too many black segments: {blacks}")
    # loudness/clipping via volumedetect
    r = subprocess.run(["ffmpeg","-i",path,"-af","volumedetect","-f","null","-"],
                       capture_output=True, text=True)
    maxv = None
    for line in r.stderr.splitlines():
        if "max_volume" in line:
            try: maxv = float(line.split("max_volume:")[1].split("dB")[0].strip())
            except Exception: pass
    result["checks"]["max_volume_db"] = maxv
    if maxv is not None and maxv > -0.5:
        result["passed"]=False; result["errors"].append(f"clipping risk: max_volume {maxv} dB")
    return result

def qc_longform(path, cfg):
    result = qc(path, cfg)
    # override duration check for long-form (>300s)
    dur = result["checks"].get("duration", 0)
    if dur < 300:
        result["passed"] = False
        result["errors"].append(f"long-form duration {dur:.2f} < 300s")
    else:
        # remove the shorts-duration error if present
        result["errors"] = [e for e in result["errors"] if "not in [10,60]" not in e]
        if not result["errors"]:
            result["passed"] = True
    result["checks"]["long_form"] = dur >= 300
    return result
