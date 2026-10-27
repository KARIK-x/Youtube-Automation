"""Niche profiles: YAML-driven editing style (inspired by Verticals v3)."""
import os, yaml
from pathlib import Path

NICHES_DIR = Path(__file__).resolve().parents[3] / "niches"

def load_niche(name):
    """Load a niche profile by name. Returns dict or None."""
    path = NICHES_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)

def list_niches():
    if not NICHES_DIR.exists():
        return []
    return sorted(p.stem for p in NICHES_DIR.glob("*.yaml"))

def apply_niche_to_config(cfg, niche_name):
    """Apply niche editing params to config. Returns updated cfg."""
    niche = load_niche(niche_name)
    if not niche:
        return cfg
    ed = niche.get("editing", {})
    if "editing" not in cfg:
        cfg["editing"] = {}
    for k in ("zoom_factor", "contrast", "sharpen", "speed_ramp", "caption_size",
              "caption_emphasis", "emphasis_color", "sfx_density", "cut_density"):
        if k in ed:
            cfg["editing"][k] = ed[k]
    # music mood
    music_mood = niche.get("music", {}).get("mood")
    if music_mood:
        cfg.setdefault("audio", {})["music_mood"] = music_mood
    # captions
    caps = niche.get("captions", {})
    if "caption_font_size" not in cfg and caps.get("font_weight"):
        cfg["video"]["caption_font_size"] = ed.get("caption_size", cfg["video"].get("caption_font_size", 72))
    return cfg

def get_niche_profile_name(cfg):
    return cfg.get("niche", {}).get("name") or cfg.get("profiles", {}).get("default", "chaos")