import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.editing import moment_selector

def test_short_dialogue():
    class S:
        def __init__(self,s,e,t): self.start=s;self.end=e;self.text=t
    segs = [S(0,1,"hi")]
    audio = {"duration":12.0,"beats":[],"energy_mean":0.02,"clipping":{"clipping":False},"silence":[]}
    cands = moment_selector.select_candidates(12.0, segs, audio, [], {"video":{"short_min":10,"short_max":60}})
    print("short dialogue candidates:", len(cands))
    for c in cands:
        assert 10 <= (c["end"]-c["start"]) <= 60

def test_repeated_segments():
    class S:
        def __init__(self,s,e,t): self.start=s;self.end=e;self.text=t
    segs = [S(0,2,"same"), S(2,4,"same"), S(4,6,"same")]
    audio = {"duration":20.0,"beats":[1,2,3],"energy_mean":0.05,"clipping":{"clipping":False},"silence":[]}
    cands = moment_selector.select_candidates(20.0, segs, audio, [], {"video":{"short_min":10,"short_max":60}})
    print("repeated candidates:", len(cands))
    # dedup by (start,end)
    keys = [(c["start"],c["end"]) for c in cands]
    assert len(keys) == len(set(keys))

def test_invalid_timestamps_rejected_by_edl():
    # moment selector should not crash on empty/zero duration
    cands = moment_selector.select_candidates(0.0, [], None, [], {"video":{"short_min":10,"short_max":60}})
    print("zero-duration candidates:", len(cands))
    assert isinstance(cands, list)

def test_reasons_present():
    class S:
        def __init__(self,s,e,t): self.start=s;self.end=e;self.text=t
    segs = [S(0,3,"hello bro")]
    audio = {"duration":20.0,"beats":[1,2,3,4,5],"energy_mean":0.05,"clipping":{"clipping":False},"silence":[]}
    cands = moment_selector.select_candidates(20.0, segs, audio, [{"time":1.0,"score":30}], {"video":{"short_min":10,"short_max":60}})
    assert len(cands) > 0
    for c in cands:
        assert isinstance(c["reasons"], list) and len(c["reasons"])>0
        assert "score" in c and "confidence" in c
    print("reasons present OK")

if __name__ == "__main__":
    test_short_dialogue()
    test_repeated_segments()
    test_invalid_timestamps_rejected_by_edl()
    test_reasons_present()
    print("MOMENT VALIDATION TESTS PASS")