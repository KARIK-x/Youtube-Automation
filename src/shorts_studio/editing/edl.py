"""Edit Decision List schema + validation."""
import json, os
from pathlib import Path

EDL_VERSION = "1.0"

REQUIRED_TOP = ["version","source","profile","output","segments"]
VALID_PROFILES = {"wholesome","chaos","aura","dramatic","gaming"}

def make_empty_edl(source_path, profile="chaos", duration_target=30):
    return {
        "version": EDL_VERSION,
        "source": source_path,
        "profile": profile,
        "output": {"width": 1080, "height": 1920, "fps": 30, "duration": duration_target},
        "segments": [],
        "music": None,
        "narration": None,
        "sfx": [],
        "captions": [],
        "zooms": [],
        "beats": [],
        "speed_changes": [],
        "transitions": [],
        "color": {"contrast": 1.05, "sharpen": True},
        "audio": {"normalize": True, "noise_reduce": True, "ducking": True},
    }

def validate(edl, cfg):
    errors = []
    if not isinstance(edl, dict):
        return ["edl must be dict"]
    if edl.get("version") != EDL_VERSION:
        errors.append(f"bad version {edl.get('version')}")
    if edl.get("profile") not in VALID_PROFILES:
        errors.append(f"unknown profile {edl.get('profile')}")
    src = edl.get("source")
    if not src or not os.path.exists(src):
        errors.append(f"source missing: {src}")
    out = edl.get("output", {})
    dur = out.get("duration")
    if dur is None or not (10 <= dur <= 60):
        errors.append(f"duration must be 10-60, got {dur}")
    w, h = out.get("width"), out.get("height")
    if (w, h) != (1080, 1920):
        errors.append(f"output must be 1080x1920, got {w}x{h}")
    segs = edl.get("segments")
    if not isinstance(segs, list) or not segs:
        errors.append("segments must be non-empty list")
    else:
        for i, s in enumerate(segs):
            if not all(k in s for k in ("start", "end")):
                errors.append(f"segment {i} missing start/end")
                continue
            if s["start"] < 0 or s["end"] <= s["start"]:
                errors.append(f"segment {i} invalid range {s['start']}-{s['end']}")
            if s["end"] > 10000:
                errors.append(f"segment {i} end too large")
    # captions timing
    for c in edl.get("captions", []) or []:
        if not all(k in c for k in ("start","end","text")):
            errors.append("caption missing fields")
        elif c["end"] <= c["start"]:
            errors.append("caption bad timing")
    # zooms
    for z in edl.get("zooms", []) or []:
        if not all(k in z for k in ("start","end","factor")):
            errors.append("zoom missing fields")
    # sfx
    for s in edl.get("sfx", []) or []:
        if not all(k in s for k in ("time",)):
            errors.append("sfx missing time")
    # total duration sanity: segments span <= duration
    if segs and dur:
        total = sum(s["end"]-s["start"] for s in segs)
        if total > dur + 1:
            errors.append(f"segments total {total:.1f}s exceeds duration {dur}s")
    return errors

def validate_or_raise(edl, cfg):
    errs = validate(edl, cfg)
    if errs:
        raise ValueError("EDL invalid: " + "; ".join(errs))
    return True
