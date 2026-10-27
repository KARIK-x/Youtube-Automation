"""Regression tests for the analytics learning loop (read-only, no fabrication)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.core import config, db as dbmod
from shorts_studio.analytics import learning


def test_learning_loop_no_data():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    db = dbmod.DB(str(ROOT / "data" / "work" / "test_analytics.db"))
    res = learning.run_learning_loop(cfg, db)
    assert res.get("error") is None
    assert res["analysis"]["sample_size"] == 0
    assert len(res["analysis"]["recommendations"]) >= 1
    # must not fabricate
    assert res["analysis"]["recommendations"][0]["sample_size"] == 0


def test_learning_loop_handles_missing_metrics():
    # inject a fake published job with missing metrics
    import sqlite3
    cfg = config.load_config(str(ROOT / "config.yaml"))
    db_path = str(ROOT / "data" / "work" / "test_analytics2.db")
    db = dbmod.DB(db_path)
    # add a job with youtube_id but no analytics
    jid = db.add_job("/tmp/test.mp4", profile="chaos", status="READY_FOR_REVIEW")
    db.update_job(jid, youtube_id="FAKE_VIDEO_ID", duration=15.0, human_approved=1)
    res = learning.run_learning_loop(cfg, db)
    assert res.get("error") is None
    # should handle gracefully (analytics adapter returns error for fake id)
    assert res["analysis"] is not None


def test_analyze_performance_empty():
    res = learning.analyze_performance([])
    assert res["sample_size"] == 0
    assert len(res["recommendations"]) >= 1


def test_edit_metadata_no_fabrication():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    db = dbmod.DB(str(ROOT / "data" / "work" / "test_analytics3.db"))
    jid = db.add_job("/tmp/test.mp4", profile="chaos", status="READY_FOR_REVIEW")
    db.update_job(jid, output_path="/tmp/test.mp4", duration=15.0)
    job = db.get_job(jid)
    meta = learning._load_edit_metadata(job, cfg)
    assert meta["job_id"] == jid
    assert meta["profile"] == "chaos"
    assert meta["duration"] == 15.0
    # no fabricated fields
    assert "views" not in meta
    assert "engagement" not in meta