"""Music library with provenance/licensing metadata."""
import os, json
from pathlib import Path

def load_library(lib_dir):
    lib_dir = Path(lib_dir)
    meta_path = lib_dir / "music_library.json"
    assets = []
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            assets = data.get("tracks", [])
        except Exception:
            assets = []
def load_library(lib_dir):
    lib_dir = Path(lib_dir)
    meta_path = lib_dir / "music_library.json"
    assets = []
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            assets = data.get("tracks", [])
        except Exception:
            assets = []
    # normalize registered paths for comparison
    # project root is two levels above the audio library dir
    project_root = lib_dir.parent.parent if lib_dir.name == "audio_library" else lib_dir.parent
    registered = set()
    for a in assets:
        pth = a.get("path", "")
        if not pth:
            continue
        pp = Path(pth)
        if not pp.is_absolute():
            # try project root first, then lib_dir
            for base in (project_root, lib_dir, Path.cwd()):
                cand = (base / pp).resolve()
                if cand.exists():
                    registered.add(str(cand))
                    break
            else:
                registered.add(str((project_root / pp).resolve()))
        else:
            registered.add(str(pp.resolve()))
    # scan for audio files without metadata -> mark unknown license (blocked for publish)
    for p in lib_dir.rglob("*"):
        if "sfx" in p.parts:
            continue
        if p.suffix.lower() in {".mp3",".wav",".m4a",".aif",".aiff",".ogg",".flac"}:
            if str(p.resolve()) not in registered:
                assets.append({"path": str(p), "title": p.stem, "mood": "unknown",
                               "license": "unknown", "source": str(p), "permitted_use": "none"})
    return assets
    return assets

def select_music(assets, profile, mood=None):
    """Return best asset path or None. Prefer cleared licenses."""
    mood = mood or profile
    # profile -> mood mapping
    mood_map = {"chaos":"hype","wholesome":"soft","aura":"epic","dramatic":"tense","gaming":"energetic"}
    target_mood = mood_map.get(profile, "hype")
def select_music(assets, profile, mood=None):
    """Return best asset dict or None. Prefer cleared/publish licenses over test."""
    mood = mood or profile
    mood_map = {"chaos":"hype","wholesome":"soft","aura":"epic","dramatic":"tense","gaming":"energetic"}
    target_mood = mood_map.get(profile, "hype")
    eligible = [a for a in assets if a.get("permitted_use") in ("publish","test","internal")
                and a.get("license") not in ("unknown", None, "")]
    # prefer cleared (publish/internal) over test assets
    cleared = [a for a in eligible if a.get("permitted_use") in ("publish", "internal")]
    pool = cleared if cleared else eligible
    import random
    mood_match = [a for a in pool if a.get("mood") == target_mood]
    if mood_match:
        return random.choice(mood_match)
    if pool:
        return random.choice(pool)
    return None

def library_template(lib_dir):
    """Create an empty library metadata file if missing."""
    lib_dir = Path(lib_dir)
    lib_dir.mkdir(parents=True, exist_ok=True)
    meta = lib_dir / "music_library.json"
    if not meta.exists():
        meta.write_text(json.dumps({"tracks": [], "note": "Add tracks with path,title,mood,license,source,permitted_use"}, indent=2))
    return meta
