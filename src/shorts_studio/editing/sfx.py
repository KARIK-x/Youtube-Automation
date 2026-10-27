"""Profile-aware SFX placement."""
import json, os
from pathlib import Path
def load_sfx_library(lib_dir):
    lib_dir = Path(lib_dir)
    meta = lib_dir / "sfx_library.json"
    assets = []
    if meta.exists():
        try:
            assets = json.loads(meta.read_text()).get("tracks", [])
        except Exception:
            assets = []
    project_root = lib_dir.parent.parent if lib_dir.name == "audio_library" else lib_dir.parent
    registered = set()
    for a in assets:
        pth = a.get("path", "")
        if not pth:
            continue
        pp = Path(pth)
        if not pp.is_absolute():
            for base in (project_root, lib_dir, Path.cwd()):
                cand = (base / pp).resolve()
                if cand.exists():
                    registered.add(str(cand))
                    break
            else:
                registered.add(str((project_root / pp).resolve()))
        else:
            registered.add(str(pp.resolve()))
    sfx_dir = lib_dir / "sfx"
    scan_dir = sfx_dir if sfx_dir.exists() else lib_dir
    for p in scan_dir.rglob("*.wav"):
        if str(p.resolve()) not in registered:
            assets.append({"path": str(p), "title": p.stem, "license": "unknown", "permitted_use": "none"})
    return [a for a in assets if a.get("permitted_use") in ("publish","test","internal")]

# SFX library metadata template
SFX_PROFILES = {
    "chaos": {"events": ["hook", "punchline", "transition"], "density": "high"},
    "wholesome": {"events": ["reveal", "payoff"], "density": "low"},
    "aura": {"events": ["hook", "payoff"], "density": "medium"},
    "dramatic": {"events": ["reveal", "transition"], "density": "medium"},
    "gaming": {"events": ["hook", "punchline", "payoff"], "density": "high"},
}

def place_sfx(profile, beats, captions, duration, sfx_library):
    """Return list of {time, path, volume, reason}. Only uses available assets."""
    if not sfx_library:
        return []
    events = SFX_PROFILES.get(profile, SFX_PROFILES["chaos"])["events"]
    density = SFX_PROFILES.get(profile, SFX_PROFILES["chaos"])["density"]
    placements = []
    # hook: first beat or 0
    if "hook" in events and beats:
        placements.append({"time": beats[0], "path": sfx_library[0]["path"],
                           "volume": 0.5, "reason": "hook_beat"})
    # punchline: caption with emphasis / last caption
    if "punchline" in events and captions:
        last = captions[-1]
        placements.append({"time": max(0, last["start"]), "path": sfx_library[0]["path"],
                           "volume": 0.4, "reason": "punchline_caption"})
    # payoff: near end
    if "payoff" in events:
        placements.append({"time": max(0, duration - 2.0), "path": sfx_library[0]["path"],
                           "volume": 0.5, "reason": "payoff"})
    # transition: mid-point
    if "transition" in events:
        placements.append({"time": duration / 2, "path": sfx_library[0]["path"],
                           "volume": 0.3, "reason": "mid_transition"})
    if density == "low":
        placements = placements[:2]
    elif density == "medium":
        placements = placements[:3]
    return placements
