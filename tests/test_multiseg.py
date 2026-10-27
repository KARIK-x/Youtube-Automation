import sys, os, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.editing import edl, renderer, qc
from shorts_studio.media import transcribe

def test_multi_segment_render():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    src = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if not src.exists():
        print("SKIP no source"); return
    # build EDL with 2 segments
    e = edl.make_empty_edl(str(src), "chaos", 10)
    e["segments"] = [
        {"start": 0.0, "end": 5.0, "source_start": 0.0, "source_end": 5.0},
        {"start": 5.0, "end": 10.0, "source_start": 5.0, "source_end": 10.0},
    ]
    e["output"]["duration"] = 10.0
    errs = edl.validate(e, cfg)
    # validation may complain about segment total vs duration; check
    print("validation errs:", errs)
    work = ROOT / "data" / "work" / "test_multiseg"
    if work.exists():
        import shutil; shutil.rmtree(work)
    work.mkdir(parents=True)
    final = renderer.render(e, str(work), cfg, final_name="multiseg_test.mp4")
    q = qc.qc(final, cfg)
    print("QC:", q["passed"], q["errors"], q["checks"]["duration"])
    assert os.path.exists(final)

if __name__ == "__main__":
    test_multi_segment_render()
    print("MULTI-SEGMENT RENDER TEST DONE")