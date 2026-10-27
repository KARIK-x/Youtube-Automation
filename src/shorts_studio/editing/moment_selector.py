"""Deterministic candidate-moment selection for Shorts."""
import json

def select_candidates(duration, transcript_segments, audio, scene_changes, cfg):
    """Return list of candidate moments: {start,end,score,reasons,confidence,profile_hint}."""
    short_min = cfg["video"]["short_min"]
    short_max = cfg["video"]["short_max"]
    candidates = []
    # Build windows from transcript segments (speech-heavy = hook potential)
    segs = transcript_segments or []
    # Candidate 1: speech segments grouped into windows
    # Use each transcript segment start as a potential hook start
    for seg in segs:
        start = max(0.0, seg.start)
        # window length: prefer 15-30s
        for win in (15.0, 20.0, 30.0):
            end = start + win
            if end > duration:
                end = duration
            if end - start < short_min:
                continue
            if end - start > short_max:
                continue
            score, reasons, conf = _score_window(start, end, duration, segs, audio, scene_changes)
            candidates.append({
                "start": round(start,3), "end": round(end,3),
                "score": round(score,3), "reasons": reasons,
                "confidence": round(conf,3), "profile_hint": _profile_hint(seg.text),
            })
    # Candidate 2: scene-change anchored windows
    for sc in (scene_changes or []):
        start = max(0.0, sc["time"] - 2.0)
        end = min(duration, start + 20.0)
        if end - start < short_min:
            continue
        score, reasons, conf = _score_window(start, end, duration, segs, audio, scene_changes)
        reasons = ["scene_change"] + reasons
        candidates.append({
            "start": round(start,3), "end": round(end,3),
            "score": round(score,3), "reasons": reasons,
            "confidence": round(conf,3), "profile_hint": "chaos",
        })
    # Dedupe by (start,end) keeping max score
    seen = {}
    for c in candidates:
        key = (c["start"], c["end"])
        if key not in seen or c["score"] > seen[key]["score"]:
            seen[key] = c
    out = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    # cap to top 10
    return out[:10]

def _score_window(start, end, duration, segs, audio, scene_changes):
    reasons = []
    score = 0.0
    conf = 0.5
    # speech coverage
    speech_time = 0.0
    for s in (segs or []):
        s0 = max(s.start, start); s1 = min(s.end, end)
        if s1 > s0:
            speech_time += (s1 - s0)
    win = end - start
    cov = speech_time / max(1e-6, win)
    if cov > 0.3:
        score += 0.3; reasons.append("speech_coverage")
        conf += 0.1
    # early hook (first 5s of source)
    if start < 5.0:
        score += 0.15; reasons.append("early_hook")
        conf += 0.05
    # beat presence
    beats = (audio or {}).get("beats", [])
    beat_count = sum(1 for b in beats if start <= b <= end)
    if beat_count >= 3:
        score += 0.2; reasons.append("beat_rich")
        conf += 0.1
    elif beat_count >= 1:
        score += 0.1; reasons.append("has_beats")
    # scene changes
    sc_count = sum(1 for s in (scene_changes or []) if start <= s["time"] <= end)
    if sc_count >= 1:
        score += 0.1; reasons.append("scene_changes")
    # energy
    energy = (audio or {}).get("energy_mean", 0)
    if energy and energy > 0.01:
        score += 0.1; reasons.append("audio_energy")
    # clipping penalty
    if (audio or {}).get("clipping", {}).get("clipping"):
        score -= 0.2; reasons.append("clipping_penalty")
        conf -= 0.1
    # silence penalty
    sil = (audio or {}).get("silence", [])
    sil_time = sum(s["duration"] for s in sil if s["start"] >= start and s["end"] <= end)
    if sil_time / max(1e-6, win) > 0.4:
        score -= 0.15; reasons.append("too_much_silence")
    # bounds
    score = max(0.0, min(1.0, score))
    conf = max(0.1, min(1.0, conf))
    if not reasons:
        reasons = ["baseline"]
    return score, reasons, conf

def _profile_hint(text):
    t = (text or "").lower()
    if any(w in t for w in ["lol","funny","haha","bro"]):
        return "chaos"
    if any(w in t for w in ["love","respect","thank","wholesome"]):
        return "wholesome"
    if any(w in t for w in ["insane","crazy","w"]):
        return "aura"
    return "chaos"
