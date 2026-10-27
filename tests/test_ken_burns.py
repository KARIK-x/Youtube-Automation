"""Regression tests for Ken Burns effect."""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.media import ken_burns as kb
from PIL import Image


def test_ken_burns_zoom_in():
    img = Image.new("RGB", (1080, 1920), (30, 30, 50))
    img.save("/tmp/kb_test2.png")
    cfg = {"video": {"width": 1080, "height": 1920, "fps": 30},
           "editing": {"ken_burns": {"enabled": True, "start_scale": 1.0, "end_scale": 1.15, "easing": "ease_in_out"}}}
    out = kb.apply_ken_burns_to_scene("/tmp/kb_test2.png", "/tmp/kb_out2.mp4", cfg, 3.0, zoom_type="zoom_in")
    assert os.path.exists(out)
    # verify with ffprobe
    import subprocess, json
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,duration",
                        "-of", "json", out], capture_output=True, text=True)
    info = json.loads(r.stdout)
    vs = info["streams"]
    assert vs and vs[0]["width"] == 1080 and vs[0]["height"] == 1920
    assert float(vs[0]["duration"]) >= 2.5


def test_ken_burns_disabled_fallback():
    img = Image.new("RGB", (1080, 1920), (30, 30, 50))
    img.save("/tmp/kb_test3.png")
    cfg = {"video": {"width": 1080, "height": 1920, "fps": 30},
           "editing": {"ken_burns": {"enabled": False}}}
    out = kb.apply_ken_burns_to_scene("/tmp/kb_test3.png", "/tmp/kb_out3.mp4", cfg, 2.0)
    assert os.path.exists(out)


def test_ken_burns_all_types():
    img = Image.new("RGB", (1080, 1920), (30, 30, 50))
    img.save("/tmp/kb_test4.png")
    cfg = {"video": {"width": 1080, "height": 1920, "fps": 30},
           "editing": {"ken_burns": {"enabled": True, "start_scale": 1.0, "end_scale": 1.1, "easing": "linear"}}}
    for zt in ["zoom_in", "zoom_out", "pan_left", "pan_right", "zoom_pan"]:
        out = f"/tmp/kb_{zt}.mp4"
        kb.ken_burns("/tmp/kb_test4.png", out, duration=2.0, fps=30, w=1080, h=1920, zoom_type=zt)
        assert os.path.exists(out), f"failed: {zt}"