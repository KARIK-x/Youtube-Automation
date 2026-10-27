"""Regression tests for niche profiles."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.core import config
from shorts_studio.editing import niche as niche_mod


def test_list_niches():
    niches = niche_mod.list_niches()
    assert len(niches) >= 4
    assert "gaming" in niches
    assert "comedy" in niches


def test_load_niche():
    n = niche_mod.load_niche("gaming")
    assert n is not None
    assert n["name"] == "gaming"
    assert n["editing"]["zoom_factor"] == 1.3


def test_load_missing_niche():
    n = niche_mod.load_niche("nonexistent")
    assert n is None


def test_apply_niche_changes_config():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    original_zoom = cfg.get("editing", {}).get("zoom_factor", 1.0)
    cfg = niche_mod.apply_niche_to_config(cfg, "dramatic")
    assert cfg["editing"]["zoom_factor"] == 1.15
    assert cfg["editing"]["speed_ramp"] == "slowmo"
    assert cfg["audio"]["music_mood"] == "tense"
    assert cfg["editing"]["zoom_factor"] != original_zoom


def test_niches_produce_different_edits():
    cfgs = {}
    for name in ["gaming", "comedy", "tech", "dramatic"]:
        cfg = config.load_config(str(ROOT / "config.yaml"))
        cfg = niche_mod.apply_niche_to_config(cfg, name)
        cfgs[name] = cfg["editing"].get("zoom_factor")
    # at least 2 different zoom values
    assert len(set(cfgs.values())) >= 2, f"all niches same zoom: {cfgs}"