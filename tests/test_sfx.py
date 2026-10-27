import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.editing import sfx

def test_place_sfx_chaos():
    beats = [0.5, 1.5, 2.5, 5.0]
    caps = [{"start": 2.0, "end": 3.0, "text": "hi"}]
    lib = [{"path": "/tmp/s.wav", "title": "s"}]
    # create dummy sfx file
    Path("/tmp/s.wav").write_bytes(b"")
    placements = sfx.place_sfx("chaos", beats, caps, 10.0, lib)
    print("chaos placements:", len(placements))
    assert len(placements) >= 3
    for pl in placements:
        assert "time" in pl and "reason" in pl and "volume" in pl
    Path("/tmp/s.wav").unlink(missing_ok=True)

def test_place_sfx_wholesome_low_density():
    beats = [1.0, 2.0]
    caps = [{"start": 1.0, "end": 2.0, "text": "hi"}]
    lib = [{"path": "/tmp/s.wav", "title": "s"}]
    Path("/tmp/s.wav").write_bytes(b"")
    placements = sfx.place_sfx("wholesome", beats, caps, 10.0, lib)
    print("wholesome placements:", len(placements))
    assert len(placements) <= 2
    Path("/tmp/s.wav").unlink(missing_ok=True)

def test_place_sfx_empty_lib():
    placements = sfx.place_sfx("chaos", [1.0], [], 10.0, [])
    assert placements == []
    print("empty lib OK")

if __name__ == "__main__":
    test_place_sfx_chaos()
    test_place_sfx_wholesome_low_density()
    test_place_sfx_empty_lib()
    print("SFX TESTS PASS")
