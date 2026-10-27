import sys, json, os, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.editing import edl, planner, renderer, qc
from shorts_studio.media import transcribe

def test_render_integration():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    src = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if not src.exists():
        # fallback: any mp4
        cands = list((ROOT / "data").rglob("*.mp4"))
        if not cands:
            print("SKIP no source"); return
        src = cands[0]
    work = ROOT / "data" / "work" / "test_render"
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    srt, ass, segs = transcribe.transcribe(str(src), str(work), "base")
    e = planner.plan(str(src), segs, profile="chaos", target_duration=15)
    edl.validate_or_raise(e, cfg)
    final = renderer.render(e, str(work), cfg)
    q = qc.qc(final, cfg)
    print("rendered:", final)
    print("QC:", q["passed"], q["errors"], q["checks"])
    assert q["passed"], q["errors"]
    assert q["checks"]["dimensions"] == "1080x1920"
    assert 10 <= q["checks"]["duration"] <= 60

if __name__ == "__main__":
    test_render_integration()
    print("RENDER INTEGRATION PASS")
