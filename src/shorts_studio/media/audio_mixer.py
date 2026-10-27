"""Audio mixing: dialogue + music + SFX with ducking."""
import os, subprocess, json

def mix_audio(dialogue_wav, music_path, sfx_list, out_wav, cfg):
    """Mix dialogue + optional music (ducked) + sfx. Returns out_wav path."""
    # Build ffmpeg filtergraph
    inputs = ["-i", dialogue_wav]
    idx = 1
    music_idx = None
    if music_path and os.path.exists(music_path):
        inputs += ["-i", music_path]
        music_idx = idx; idx += 1
    sfx_indices = []
    for s in (sfx_list or []):
        if os.path.exists(s["path"]):
            inputs += ["-i", s["path"]]
            sfx_indices.append((idx, s)); idx += 1

    # Build filter complex
    filters = []
    # dialogue normalize
    filters.append(f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,afftdn=nf=-25[dlg]")
    if music_idx is not None:
        # music ducked by dialogue
        filters.append(f"[{music_idx}:a]volume=0.35,afade=t=in:st=0:d=0.5[mus]")
        filters.append(f"[mus][dlg]sidechaincompress=threshold=0.02:ratio=8:attack=5:release=200[musducked]")
        # mix dlg + musducked
        mix = "[dlg][musducked]amix=inputs=2:duration=first:dropout_transition=2[mix]"
        filters.append(mix)
    else:
        filters.append("[dlg]anull[mix]")
    # add sfx
    cur = "mix"
    for i, (si, s) in enumerate(sfx_indices):
        t = s.get("time", 0)
        vol = s.get("volume", 0.6)
        delay_ms = int(t * 1000)
        filters.append(f"[{si}:a]volume={vol},adelay={delay_ms}|{delay_ms}[sfx{i}]")
        filters.append(f"[{cur}][sfx{i}]amix=inputs=2:duration=first:dropout_transition=0[{ 'mix'+str(i+1) }]")
        cur = f"mix{i+1}"
    final_label = cur
    filters.append(f"[{final_label}]loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    fc = ";".join(filters)
    cmd = ["ffmpeg","-y"] + inputs + ["-filter_complex", fc, "-map","[out]","-c:a","pcm_s16le", out_wav]
    subprocess.run(cmd, capture_output=True, check=True, timeout=300)
    return out_wav

def clipping_check(wav_path, threshold_db=-1.0):
    import subprocess, json
    r = subprocess.run(["ffmpeg","-i",wav_path,"-af","volumedetect","-f","null","-"],
                       capture_output=True, text=True)
    maxv = None
    for line in r.stderr.splitlines():
        if "max_volume" in line:
            try: maxv = float(line.split("max_volume:")[1].split("dB")[0].strip())
            except Exception: pass
    return {"max_volume_db": maxv, "clipping": maxv is not None and maxv > threshold_db}
