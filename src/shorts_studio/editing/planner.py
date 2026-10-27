"""Creative editing planner: source + transcript -> validated EDL."""
import os, subprocess, json
from .edl import make_empty_edl
from .profiles import PROFILES

def plan(source_path, segments, profile="chaos", target_duration=30, moment=None, audio=None, scene_changes=None):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",source_path],
                       capture_output=True, text=True)
    try:
        info_duration = float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        info_duration = target_duration
    if moment is not None:
        start = float(moment["start"]); end = float(moment["end"])
    else:
        try:
            from .moment_selector import select_candidates
            cands = select_candidates(info_duration, segments, audio, scene_changes, {"video":{"short_min":10,"short_max":60}})
            if cands:
                c = cands[0]
                start, end = c["start"], c["end"]
            else:
                start, end = 0.0, min(target_duration, info_duration)
        except Exception:
            start, end = 0.0, min(target_duration, info_duration)
    if end - start < 10:
        end = min(info_duration, start + 10.0)
    if end - start > 60:
        end = start + 60.0
    if end > info_duration:
        end = info_duration
    dur = end - start
    if dur < 10:
        dur = min(10.0, info_duration); end = start + dur
def plan(source_path, segments, profile="chaos", target_duration=30, moment=None, audio=None, scene_changes=None, beat_cuts=False):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",source_path],
                       capture_output=True, text=True)
    try:
        info_duration = float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        info_duration = target_duration
    if moment is not None:
        start = float(moment["start"]); end = float(moment["end"])
    else:
        try:
            from .moment_selector import select_candidates
            cands = select_candidates(info_duration, segments, audio, scene_changes, {"video":{"short_min":10,"short_max":60}})
            if cands:
                c = cands[0]
                start, end = c["start"], c["end"]
            else:
                start, end = 0.0, min(target_duration, info_duration)
        except Exception:
            start, end = 0.0, min(target_duration, info_duration)
    if end - start < 10:
        end = min(info_duration, start + 10.0)
    if end - start > 60:
        end = start + 60.0
    if end > info_duration:
        end = info_duration
    dur = end - start
    if dur < 10:
        dur = min(10.0, info_duration); end = start + dur
    edl = make_empty_edl(source_path, profile, dur)
    # default: one segment covering the whole moment
    seg_list = [{"start": start, "end": end, "source_start": start, "source_end": end}]
    beats = []
    if audio and audio.get("beats"):
        beats = [b for b in audio["beats"] if start <= b <= end]
    # optional beat-synced internal cuts: only split where a beat coincides with a
    # silence gap (so we never cut mid-speech). Off by default — cutting inside
    # dialogue ruins continuity.
    if beat_cuts and beats:
        silences = (audio.get("silence") or []) if audio else []
        cuts = [start]
        for b in beats:
            if b <= start + 0.5 or b >= end - 0.5:
                continue
            near_silence = any(
                (s.get("start", 0) - 0.5 <= b <= s.get("end", 0) + 0.5) for s in silences)
            mid_word = False
            for seg in (segments or []):
                words = getattr(seg, "words", None)
                if words:
                    for w in words:
                        ws = getattr(w, "start", None); we = getattr(w, "end", None)
                        if ws is None or we is None:
                            continue
                        if ws + 0.05 < b < we - 0.05:
                            mid_word = True
                            break
                if mid_word:
                    break
            # if no word timings are available, rely on the silence check alone
            if near_silence and not mid_word:
                cuts.append(b)
        cuts.append(end)
        cuts = sorted(set(round(c, 3) for c in cuts))
        new_segs = []
        for i in range(len(cuts) - 1):
            if cuts[i + 1] - cuts[i] >= 1.0:
                new_segs.append({"start": cuts[i], "end": cuts[i + 1],
                                 "source_start": cuts[i], "source_end": cuts[i + 1]})
        if len(new_segs) > 1:
            seg_list = new_segs
    edl["segments"] = seg_list
    caps = []
    for seg in (segments or []):
        s = max(seg.start, start); e = min(seg.end, end)
        if e - s >= 0.3:
            caps.append({"start": round(s-start,3), "end": round(e-start,3), "text": seg.text.strip()})
    edl["captions"] = caps
    edl["hook_title"] = " ".join(caps[0]["text"].split()[:6]) if caps else None
    p = PROFILES.get(profile, PROFILES["chaos"])
    edl["color"]["contrast"] = p["contrast"]
    zooms = [{"start": 0.0, "end": min(3.0, dur), "factor": p["zoom_factor"]}]
    if audio and audio.get("beats"):
        from .beat_sync import sync_zooms
        zooms = sync_zooms(zooms, beats)
    edl["zooms"] = zooms
    edl["beats"] = beats
    edl["audio"]["ducking"] = True
    edl["music"] = None
    return edl
