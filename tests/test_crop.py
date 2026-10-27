import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.media import editor

def test_center_crop():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    cfg["video"]["crop"] = "center"
    src = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if not src.exists():
        print("SKIP no source"); return
    out = ROOT / "data" / "work" / "test_center.mp4"
    editor.center_crop_pass(str(src), str(out), cfg)
    info = editor.probe(str(out))
    assert info["w"] == 1080 and info["h"] == 1920, info
    print("center crop OK", info["w"], info["h"])

def test_face_crop_sparse():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    cfg["video"]["crop"] = "face"
    cfg["video"]["face_detect_interval"] = 15
    src = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if not src.exists():
        print("SKIP no source"); return
    out = ROOT / "data" / "work" / "test_face.mp4"
    editor.face_crop_pass(str(src), str(out), cfg)
    info = editor.probe(str(out))
    assert info["w"] == 1080 and info["h"] == 1920, info
    print("face crop (sparse) OK", info["w"], info["h"])

if __name__ == "__main__":
    test_center_crop()
    test_face_crop_sparse()
    print("CROP TESTS PASS")
