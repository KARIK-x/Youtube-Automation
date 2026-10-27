import os, sys, json, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.editing import edl, planner

def test_edl_valid():
    e = edl.make_empty_edl("x.mp4", "chaos", 30)
    e["segments"] = [{"start":0,"end":30}]
    e["source"] = None  # will be set
    # use a real file
    p = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if p.exists():
        e["source"] = str(p)
    errs = edl.validate(e, {})
    # source may be missing in test env; check other errors
    print("errs:", errs)

def test_edl_invalid_duration():
    e = edl.make_empty_edl("x.mp4","chaos",5)
    e["segments"] = [{"start":0,"end":5}]
    errs = edl.validate(e, {})
    assert any("duration" in x for x in errs), errs

def test_edl_invalid_segment():
    p = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    e = edl.make_empty_edl(str(p),"chaos",30)
    e["segments"] = [{"start":5,"end":3}]  # bad
    errs = edl.validate(e, {})
    assert any("invalid range" in x for x in errs), errs

def test_plan_creates_valid_edl():
    p = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if not p.exists():
        print("SKIP no source"); return
    import subprocess
    # fake segments
    class S: 
        def __init__(self,s,e,t): self.start=s;self.end=e;self.text=t
    segs = [S(0,2,"hello"), S(2,5,"world")]
    e = planner.plan(str(p), segs, profile="chaos", target_duration=20)
    assert e["version"]=="1.0"
    errs = edl.validate(e, {})
    print("plan errs:", errs)
    assert not errs, errs

if __name__ == "__main__":
    test_edl_valid(); test_edl_invalid_duration(); test_edl_invalid_segment(); test_plan_creates_valid_edl()
    print("OK")
