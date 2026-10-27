"""Deterministic renderer from a validated EDL."""
import os, subprocess, json
from pathlib import Path
from ..media import editor, audio_analysis, music_library, audio_mixer
from ..editing import sfx as sfx_mod
from ..editing import profiles as prof_mod

def probe(path):
    return editor.probe(path)

def render(edl, work_dir, cfg, final_name="final.mp4"):
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    source = edl["source"]
    dur = edl["output"]["duration"]
    fps = edl["output"]["fps"]
    w, h = edl["output"]["width"], edl["output"]["height"]
    profile = edl.get("profile", "chaos")
    contrast = edl.get("color", {}).get("contrast", 1.05)
    sharpen = edl.get("color", {}).get("sharpen", True)
    captions_on = cfg["video"].get("captions", True)
    crop_mode = cfg["video"].get("crop", "face")

    print(f"[renderer] profile={profile} duration={dur:.2f}s crop={crop_mode} captions={captions_on} segments={len(edl.get('segments',[]))}", flush=True)

    cfg2 = dict(cfg)
    cfg2["video"] = dict(cfg["video"]); cfg2["video"]["width"]=w; cfg2["video"]["height"]=h; cfg2["video"]["fps"]=fps
    cfg2["editing"] = dict(cfg["editing"]); cfg2["editing"]["contrast"]=contrast; cfg2["editing"]["sharpen"]=sharpen
    p = prof_mod.get_profile(profile)
    cfg2["editing"]["emphasis_keywords"] = prof_mod.EMPHASIS_KEYWORDS.get(profile, [])
    cfg2["editing"]["zoom_factor"] = p["zoom_factor"]

    beats = edl.get("beats") or []
    zooms = edl.get("zooms", []) or []
    if beats:
        from ..editing import beat_sync
        zooms = beat_sync.sync_zooms(zooms, beats)
        print(f"[renderer] beat-synced zooms: {zooms}", flush=True)

    segments = edl.get("segments") or []
    if not segments:
        segments = [{"start": 0.0, "end": dur, "source_start": 0.0, "source_end": dur}]

    # Process each segment: trim -> visual (with captions) -> audio
    visual_parts = []
    audio_parts = []
    for i, seg in enumerate(segments):
        s0 = seg.get("source_start", seg["start"])
        s1 = seg.get("source_end", seg["end"])
        # beat-synced trim: snap boundaries to nearest beat
        if beats:
            from ..editing import beat_sync
            s0 = beat_sync.snap_to_beat(s0, beats, max_snap=0.5)
            s1 = beat_sync.snap_to_beat(s1, beats, max_snap=0.5)
            if s1 <= s0:
                s1 = s0 + max(0.5, seg["end"] - seg["start"])
        print(f"[renderer] segment {i}: source {s0:.3f}-{s1:.3f}", flush=True)

        trimmed = os.path.join(work_dir, f"trimmed_{i}.mp4")
        subprocess.run(["ffmpeg","-y","-ss",str(s0),"-t",str(s1-s0),"-i",source,
                       "-c:v","libx264","-preset","fast","-crf","18","-c:a","aac","-b:a","128k",trimmed],
                       capture_output=True, check=True, timeout=300)

        class Seg:
            def __init__(self, start, end, text):
                self.start=start; self.end=end; self.text=text
        caps = [c for c in (edl.get("captions") or []) if seg["start"] <= c["start"]+seg["start"] <= seg["end"]+seg["start"]]
        # captions relative to segment
        fake_segs = []
        for c in (edl.get("captions") or []):
            cs = c["start"] + seg["start"]; ce = c["end"] + seg["start"]
            if cs >= s0 and ce <= s1:
                fake_segs.append(Seg(c["start"] + (s0 - seg["start"]) if False else (cs - s0), (ce - s0), c["text"]))
        # simpler: relative to trimmed (trimmed starts at s0)
        fake_segs = []
        for c in (edl.get("captions") or []):
            cs = c["start"] + seg["start"]; ce = c["end"] + seg["start"]
            if s0 <= cs < s1:
                fake_segs.append(Seg(cs - s0, min(ce, s1) - s0, c["text"]))

        visual = os.path.join(work_dir, f"visual_{i}.mp4")
        editor.render_visual(trimmed, visual, cfg2, segments=fake_segs, crop_mode=crop_mode, zooms=zooms, hook_title=edl.get("hook_title"))

        audio = os.path.join(work_dir, f"audio_{i}.wav")
        narration_path = edl.get("narration")
        if narration_path and os.path.exists(narration_path):
            print(f"[renderer] using narration audio: {narration_path}", flush=True)
            editor.process_audio(narration_path, audio, cfg2)
        else:
            editor.process_audio(trimmed, audio, cfg2)

        visual_parts.append(visual)
        audio_parts.append(audio)

    # Concatenate visuals (hard cuts on beat boundaries)
    if len(visual_parts) == 1:
        visual_final = visual_parts[0]
    else:
        listfile = os.path.join(work_dir, "visual_concat.txt")
        with open(listfile, "w") as f:
            for v in visual_parts:
                f.write(f"file '{os.path.abspath(v)}'\n")
        visual_final = os.path.join(work_dir, "visual_all.mp4")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",listfile,"-c","copy",visual_final],
                       capture_output=True, check=True, timeout=300)

    # Concatenate audio
    if len(audio_parts) == 1:
        audio_final = audio_parts[0]
    else:
        listfile = os.path.join(work_dir, "audio_concat.txt")
        with open(listfile, "w") as f:
            for a in audio_parts:
                f.write(f"file '{os.path.abspath(a)}'\n")
        audio_final = os.path.join(work_dir, "audio_all.wav")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",listfile,"-c","copy",audio_final],
                       capture_output=True, check=True, timeout=300)

    # music + sfx
    music_dir = cfg.get("audio", {}).get("music_library_dir", "data/audio_library")
    sfx_dir = cfg.get("audio", {}).get("sfx_library_dir", "data/audio_library")
    music_assets = music_library.load_library(music_dir)
    sfx_assets = sfx_mod.load_sfx_library(sfx_dir)
    music_track = music_library.select_music(music_assets, profile)
    sfx_placements = sfx_mod.place_sfx(profile, beats, edl.get("captions",[]), dur, sfx_assets)
    print(f"[renderer] music: {music_track['title'] if music_track else None} | sfx: {len(sfx_placements)}", flush=True)

    final_audio = audio_final
    if music_track or sfx_placements:
        mixed = os.path.join(work_dir, "mixed.wav")
        try:
            audio_mixer.mix_audio(audio_final, music_track["path"] if music_track else None,
                                 sfx_placements, mixed, cfg)
            cc = audio_mixer.clipping_check(mixed)
            print(f"[renderer] mixed audio: max_volume={cc['max_volume_db']}dB clipping={cc['clipping']}", flush=True)
            if cc["clipping"]:
                print("[renderer] WARNING: mixed audio clipping; falling back to dialogue-only", flush=True)
            else:
                final_audio = mixed
        except Exception as e:
            print(f"[renderer] mixing failed, fallback dialogue-only: {e}", flush=True)
    else:
        print("[renderer] no music/sfx available; using dialogue-only (fallback)", flush=True)

    final = os.path.join(work_dir, final_name)
    print("[renderer] muxing...", flush=True)
    editor.mux(visual_final, final_audio, final)
    print(f"[renderer] done: {final}", flush=True)
    return final