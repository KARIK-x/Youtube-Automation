import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.editing import beat_sync, profiles

def test_snap_to_beat():
    beats = [1.0, 2.0, 3.0]
    assert beat_sync.snap_to_beat(1.1, beats, 0.25) == 1.0
    assert beat_sync.snap_to_beat(5.0, beats, 0.25) == 5.0  # no nearby
    assert beat_sync.snap_to_beat(2.0, [], 0.25) == 2.0
    print("snap OK")

def test_sync_zooms():
    beats = [0.5, 1.5, 2.5]
    zooms = [{"start": 0.0, "end": 3.0, "factor": 1.2}]
    out = beat_sync.sync_zooms(zooms, beats)
    print("synced zooms:", out)
    assert out[0]["end"] >= out[0]["start"]

def test_profiles_distinct():
    names = ["chaos","wholesome","aura","dramatic","gaming"]
    ps = [profiles.get_profile(n) for n in names]
    # zoom factors differ
    zooms = [p["zoom_factor"] for p in ps]
    assert len(set(zooms)) >= 3, zooms
    # contrasts differ
    cons = [p["contrast"] for p in ps]
    assert len(set(cons)) >= 3, cons
    print("profiles distinct OK")

def test_emphasis_keywords():
    for prof in ["chaos","wholesome","aura"]:
        kws = profiles.EMPHASIS_KEYWORDS[prof]
        assert len(kws) > 0
    print("emphasis OK")

if __name__ == "__main__":
    test_snap_to_beat()
    test_sync_zooms()
    test_profiles_distinct()
    test_emphasis_keywords()
    print("BEAT/PROFILE TESTS PASS")
