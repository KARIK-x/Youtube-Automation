"""Regression tests for the shared pipeline's hard gates (no render)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.core import config, db as dbmod
from shorts_studio.queue import pipeline


def test_process_source_blocks_unregistered_source(tmp_path):
    cfg = config.load_config(str(ROOT / "config.yaml"))
    db = dbmod.DB(str(tmp_path / "t.db"))
    # a source with no rights record must be BLOCKED before any render
    res = pipeline.process_source(cfg, db, ROOT, "/tmp/definitely-not-a-real-source.mp4",
                                 "chaos", allow_unverified=False, move_source=False)
    assert res["status"] == "BLOCKED"
    assert "rights" in (res.get("reason") or "").lower()
    assert res["output"] is None
    jobs = db.count_by_status()
    assert jobs.get("BLOCKED", 0) >= 1


def test_process_source_allow_unverified_does_not_authorize_publishing(tmp_path):
    src = "/tmp/s3.mp4"
    if not Path(src).exists():
        return
    cfg = config.load_config(str(ROOT / "config.yaml"))
    db = dbmod.DB(str(tmp_path / "t.db"))
    # rights still UNKNOWN even when allowed for local testing
    res = pipeline.process_source(cfg, db, ROOT, src, "chaos",
                                 allow_unverified=True, move_source=False)
    assert res.get("rights_status") == "UNKNOWN"
    assert res.get("rights_status") != "AUTHORIZED"
