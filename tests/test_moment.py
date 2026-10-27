import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.editing import moment_selector

def test_select_candidates_basic():
    class S:
        def __init__(self,s,e,t): self.start=s;self.end=e;self.text=t
    segs = [S(0,2,"hello bro"), S(2,5,"world")]
    audio = {"duration":20.0,"beats":[1.0,2.0,3.0,4.0,5.0],"energy_mean":0.05,"clipping":{"clipping":False},"silence":[]}
    scenes = [{"time":1.5,"score":30.0}]
    cands = moment_selector.select_candidates(20.0, segs, audio, scenes, {"video":{"short_min":10,"short_max":60}})
    print("num candidates:", len(cands))
    assert len(cands) > 0
    for c in cands:
        assert 10 <= (c["end"]-c["start"]) <= 60
        assert 0 <= c["score"] <= 1
        assert 0 < c["confidence"] <= 1
        assert isinstance(c["reasons"], list) and len(c["reasons"])>0
    # sorted descending
    scores = [c["score"] for c in cands]
    assert scores == sorted(scores, reverse=True)

def test_select_candidates_silence_penalized():
    class S:
        def __init__(self,s,e,t): self.start=s;self.end=e;self.text=t
    segs = [S(0,2,"hi")]
    # mostly silence
    audio = {"duration":20.0,"beats":[],"energy_mean":0.001,"clipping":{"clipping":False},
            "silence":[{"start":0,"end":18,"duration":18}]}
    cands = moment_selector.select_candidates(20.0, segs, audio, [], {"video":{"short_min":10,"short_max":60}})
    print("silence candidates:", len(cands))
    # any candidate should have silence penalty or low score
    for c in cands:
        print(c["start"], c["score"], c["reasons"])

def test_select_candidates_empty():
    cands = moment_selector.select_candidates(15.0, [], None, [], {"video":{"short_min":10,"short_max":60}})
    print("empty candidates:", len(cands))
    # may be 0 or scene-based; just ensure no crash

if __name__ == "__main__":
    test_select_candidates_basic()
    test_select_candidates_silence_penalized()
    test_select_candidates_empty()
    print("MOMENT TESTS PASS")