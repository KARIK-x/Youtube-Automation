import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.editing import qc

def test_qc_pass_on_rendered():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    p = ROOT / "data" / "output" / "dolma_final.mp4"
    if not p.exists():
        print("SKIP: no rendered file"); return
    q = qc.qc(str(p), cfg)
    print("QC passed:", q["passed"], q["errors"])
    assert q["passed"], q["errors"]
    assert q["checks"]["dimensions"] == "1080x1920"

def test_qc_fail_on_missing():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    q = qc.qc(str(ROOT / "data" / "nope.mp4"), cfg)
    assert not q["passed"]
    print("missing-file QC correctly fails")

if __name__ == "__main__":
    test_qc_fail_on_missing()
    test_qc_pass_on_rendered()
    print("QC TESTS DONE")
