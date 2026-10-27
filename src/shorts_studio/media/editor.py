"""Video editing with OpenCV frame renderer. CapCut-style presets, captions burned in Python."""
import os, subprocess, json, math, shutil
from pathlib import Path

def probe(path):
    cmd = ["ffprobe","-v","error","-select_streams","v:0","-show_entries",
           "stream=width,height,r_frame_rate,duration","-of","json", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(r.stdout)
    s = info["streams"][0]
    w,h = s["width"], s["height"]
    fr = s.get("r_frame_rate","30/1")
    num,den = fr.split("/")
    fps = float(num)/float(den) if den not in ("0",) else 30.0
    dur = float(s.get("duration") or 0)
    if not dur:
        cmd2 = ["ffprobe","-v","error","-show_entries","format=duration","-of","json",path]
        r2 = subprocess.run(cmd2, capture_output=True, text=True)
        dur = float(json.loads(r2.stdout)["format"]["duration"])
    return {"w":w,"h":h,"fps":fps,"dur":dur}

def run(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-500:]}")
    return r

_CAPTION_OVERLAY_CACHE = {}


def _caption_overlay(text, cfg, h, w):
    """Render a caption onto a transparent (zero) frame once, and reuse it.

    Drawing text with cv2.putText was ~5s for an 890-frame clip because it runs
    52 putText calls *per frame*. Rendering the text once per unique caption string
    and compositing by mask cuts that to a single array assignment per frame.
    """
    import cv2, numpy as np
    key = (text, h, w, tuple(cfg.get("editing", {}).get("emphasis_keywords") or []))
    cached = _CAPTION_OVERLAY_CACHE.get(key)
    if cached is not None:
        return cached
    blank = np.zeros((h, w, 3), dtype=np.uint8)
    _draw_caption(blank, text, cfg)
    mask = cv2.cvtColor(blank, cv2.COLOR_BGR2GRAY) > 0
    _CAPTION_OVERLAY_CACHE[key] = (blank, mask)
    return _CAPTION_OVERLAY_CACHE[key]


def _active_seg(segments, t):
    if not segments:
        return None
    for seg in segments:
        if seg.start <= t <= seg.end:
            return seg
    for seg in segments:
        if seg.start <= t <= seg.end + 0.3:
            return seg
    return None


def clear_caption_cache():
    _CAPTION_OVERLAY_CACHE.clear()
    if not segments:
        return None
    for seg in segments:
        if seg.start <= t <= seg.end:
            return seg
    for seg in segments:
        if seg.start <= t <= seg.end + 0.3:
            return seg
    return None

def _draw_caption(frame, text, cfg):
    import cv2
    h, w = frame.shape[:2]
    if not text:
        return frame
    text = text.strip()
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.35
    thick = 4
    emphasis = set(kw.lower() for kw in (cfg.get("editing", {}).get("emphasis_keywords") or []))
    words = text.split()
    lines = []
    cur = []
    maxchars = 20
    for wd in words:
        if sum(len(x) for x in cur) + len(wd) + len(cur) <= maxchars:
            cur.append(wd)
        else:
            if cur: lines.append(cur)
            cur = [wd]
    if cur: lines.append(cur)
    lines = lines[:3]
    line_h = int(46 * scale)
    total = len(lines) * (line_h + 8)
    y0 = h - 300 - total
    # semi-transparent background box
    if lines:
        maxw = 0
        for line_words in lines:
            full = " ".join(line_words)
            (tw, _), _ = cv2.getTextSize(full, font, scale, thick)
            maxw = max(maxw, tw)
        x_box = (w - maxw) // 2 - 24
        y_box = y0 - 12
        box_w = maxw + 48
        box_h = total + 24
        overlay = frame.copy()
        cv2.rectangle(overlay, (x_box, y_box), (x_box + box_w, y_box + box_h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
    for i, line_words in enumerate(lines):
        full = " ".join(line_words)
        (tw, th), _ = cv2.getTextSize(full, font, scale, thick)
        x = (w - tw) // 2
        y = y0 + i * (line_h + 8) + th
        cx = x
        for wd in line_words:
            is_emp = wd.strip(".,!?").lower() in emphasis
            color = (0, 220, 255) if is_emp else (255, 255, 255)
            thick_w = thick + 2 if is_emp else thick
            for dx in (-3, -2, -1, 0, 1, 2, 3):
                for dy in (-3, -2, -1, 0, 1, 2, 3):
                    if dx == 0 and dy == 0:
                        continue
                    cv2.putText(frame, wd, (cx+dx, y+dy), font, scale, (0, 0, 0), thick_w+3, cv2.LINE_AA)
            cv2.putText(frame, wd, (cx, y), font, scale, color, thick_w, cv2.LINE_AA)
            (ww, _), _ = cv2.getTextSize(wd + " ", font, scale, thick)
            cx += ww
    return frame

def render_visual(src, dst, cfg, segments=None, crop_mode="face", zooms=None, hook_title=None):
    import cv2
    info = probe(src)
    sw, sh = info["w"], info["h"]
    fps = info["fps"] or 30.0
    target_w, target_h = cfg["video"]["width"], cfg["video"]["height"]
    crop_h = sh
    crop_w = int(sh * 9 / 16)
    if crop_w > sw:
        crop_w = sw
        crop_h = int(sw * 16 / 9)
    import numpy as np
    cascade = None
    if crop_mode == "face":
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(src)
    # Stream raw frames to ffmpeg -> libx264. This replaces cv2.VideoWriter (mp4v),
    # which was the slowest single step (~40% of render time) and forced a second
    # full re-encode in mux(). ffmpeg now produces the final h264 directly.
    ffmpeg_cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                  "-f", "rawvideo", "-pix_fmt", "bgr24",
                  "-s", f"{target_w}x{target_h}", "-r", f"{fps:.6f}", "-i", "pipe:0",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                  "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    write_frame = proc.stdin.write
    cx_smooth = sw // 2
    alpha = 0.15
    zoom = 1.0
    zoom_target = 1.0
    zoom_on = cfg["editing"].get("zoom_on_reaction", True)
    zoom_factor = cfg["editing"].get("zoom_factor", 1.15)
    frame_idx = 0
    sharpen = cfg["editing"].get("sharpen", False)
    contrast = cfg["editing"].get("contrast", 1.0)
    captions_on = cfg["video"].get("captions", True)
    speed_ramp_mode = cfg["editing"].get("speed_ramp", "none")
    do_speed_ramp = speed_ramp_mode in ("fast", "slowmo", "slowmo_payoff", "none") and speed_ramp_mode != "none"
    detect_interval = int(cfg["video"].get("face_detect_interval", 15))
    if detect_interval < 1:
        detect_interval = 1
    det_scale = 0.5
    total_frames = int(info["dur"] * fps)
    last_log = 0
    zooms = zooms or []
    print(f"[render_visual] {src}: {sw}x{sh} @ {fps:.2f}fps, {total_frames} frames, crop_mode={crop_mode}, detect_interval={detect_interval}, zooms={len(zooms)}", flush=True)
    frame_accumulator = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = frame_idx / fps
        active_zoom_factor = None
        for z in zooms:
            if z["start"] <= t <= z["end"]:
                active_zoom_factor = z.get("factor", zoom_factor)
                break
        if crop_mode == "face" and cascade is not None:
            if frame_idx % detect_interval == 0:
                small = cv2.resize(frame, (int(sw*det_scale), int(sh*det_scale)))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                faces = cascade.detectMultiScale(gray, 1.2, 5, minSize=(int(60*det_scale), int(60*det_scale)))
                if len(faces):
                    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                    fcx = int((x + w//2) / det_scale)
                    cx_smooth = int(cx_smooth * (1 - alpha) + fcx * alpha)
                    face_ratio = (w*h)/(sw*sh) / (det_scale*det_scale)
                    if active_zoom_factor is not None:
                        zoom_target = active_zoom_factor
                    elif zoom_on and face_ratio > 0.015:
                        zoom_target = zoom_factor
                    else:
                        zoom_target = 1.0
                else:
                    if active_zoom_factor is not None:
                        zoom_target = active_zoom_factor
                    else:
                        zoom_target = 1.0
            zoom += (zoom_target - zoom) * 0.2
        else:
            if active_zoom_factor is not None:
                zoom_target = active_zoom_factor
                zoom += (zoom_target - zoom) * 0.2
            else:
                zoom = 1.0
        x0 = int(cx_smooth - crop_w / 2) if crop_mode == "face" else (sw - crop_w) // 2
        x0 = max(0, min(sw - crop_w, x0))
        y0 = max(0, (sh - crop_h) // 2)
        region = frame[y0:y0 + crop_h, x0:x0 + crop_w]
        if region.shape[1] != crop_w or region.shape[0] != crop_h:
            region = cv2.resize(region, (crop_w, crop_h))
        if zoom > 1.01:
            zh = int(crop_h / zoom)
            zw = int(crop_w / zoom)
            zx = (crop_w - zw) // 2
            zy = (crop_h - zh) // 2
            region = region[zy:zy + zh, zx:zx + zw]
            region = cv2.resize(region, (crop_w, crop_h))
        region = cv2.resize(region, (target_w, target_h))
        if sharpen:
            kernel = np.array([[0, -0.2, 0], [-0.2, 1.8, -0.2], [0, -0.2, 0]], dtype=np.float32)
            region = cv2.filter2D(region, -1, kernel)
        if contrast != 1.0:
            region = cv2.convertScaleAbs(region, alpha=contrast, beta=0)
        if captions_on:
            seg = _active_seg(segments, t)
            if seg is not None:
                overlay, mask = _caption_overlay(seg.text, cfg, region.shape[0], region.shape[1])
                if mask.any():
                    region = region.copy()
                    region[mask] = overlay[mask]
        # hook title overlay for the first 2.5s (viral pattern)
        if hook_title and t < 2.5:
            import cv2
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 1.6
            thick = 5
            (tw, th), _ = cv2.getTextSize(hook_title, font, scale, thick)
            x = (region.shape[1] - tw) // 2
            y = 180 + th
            # background box
            overlay = region.copy()
            cv2.rectangle(overlay, (x-20, y-th-16), (x+tw+20, y+16), (0,0,0), -1)
            region = cv2.addWeighted(overlay, 0.6, region, 0.4, 0)
            # outline
            for dx in (-3,-2,-1,0,1,2,3):
                for dy in (-3,-2,-1,0,1,2,3):
                    if dx==0 and dy==0: continue
                    cv2.putText(region, hook_title, (x+dx, y+dy), font, scale, (0,0,0), thick+3, cv2.LINE_AA)
            cv2.putText(region, hook_title, (x, y), font, scale, (0,220,255), thick, cv2.LINE_AA)
        proc.stdin.write(region.tobytes())
        if do_speed_ramp and t < 2.5:
            proc.stdin.write(region.tobytes())
        frame_idx += 1
        if frame_idx - last_log >= 300:
            print(f"[render_visual] progress {frame_idx}/{total_frames} ({100*frame_idx/max(1,total_frames):.1f}%)", flush=True)
            last_log = frame_idx
    cap.release()
    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg render failed (rc={rc}): {proc.stderr.read().decode(errors='replace')[-500:]}")
    print(f"[render_visual] done: {frame_idx} frames -> {dst}", flush=True)
    return dst

def face_crop_pass(src, dst, cfg, segments=None, zooms=None):
    return render_visual(src, dst, cfg, segments=segments, crop_mode="face", zooms=zooms)

def center_crop_pass(src, dst, cfg, segments=None, zooms=None):
    return render_visual(src, dst, cfg, segments=segments, crop_mode="center", zooms=zooms)

def process_audio(src_video, dst_audio, cfg):
    cmd = ["ffmpeg","-y","-i",src_video,"-vn","-ac","1","-ar","44100", dst_audio]
    run(cmd)
    filters = []
    if cfg["video"].get("noise_reduce"):
        filters.append("afftdn=nf=-25")
    if cfg["video"].get("normalize_audio"):
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    if filters:
        filt = ",".join(filters)
        tmp = dst_audio + ".tmp.wav"
        cmd = ["ffmpeg","-y","-i",dst_audio,"-af",filt,tmp]
        run(cmd)
        os.replace(tmp, dst_audio)
    return dst_audio

def mux(src_video, audio_path, dst):
    cmd = ["ffmpeg","-y","-i",src_video,"-i",audio_path,
           "-c:v","copy","-c:a","aac","-b:a","128k","-shortest",dst]
    run(cmd)
    return dst

def edit_clip(src_path, work_dir, cfg, segments=None, ass_path=None, zooms=None):
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    base = Path(src_path).stem
    info = probe(src_path)
    crop = cfg["video"].get("crop", "face")
    visual = os.path.join(work_dir, base + "_visual.mp4")
    if crop == "face":
        try:
            face_crop_pass(src_path, visual, cfg, segments=segments, zooms=zooms)
        except Exception as e:
            print("face crop failed, fallback center:", e)
            center_crop_pass(src_path, visual, cfg, segments=segments, zooms=zooms)
    else:
        center_crop_pass(src_path, visual, cfg, segments=segments, zooms=zooms)
    audio = os.path.join(work_dir, base + "_audio.wav")
    process_audio(src_path, audio, cfg)
    av = os.path.join(work_dir, base + "_av.mp4")
    mux(visual, audio, av)
    return av
