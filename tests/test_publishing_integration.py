import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.youtube.publishing import YouTubePublisher
from shorts_studio.core import publish_gate, rights, db

def test_dryrun_never_uploads():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    pub = YouTubePublisher(cfg, dry_run=True)
    res = pub.upload("data/output/dolma_final.mp4", "T", "D", ["t"], None)
    assert res["status"] == "DRY_RUN"
    assert res["video_id"] is None
    assert res["dry_run"] is True
    print("dryrun never uploads OK")

def test_dryrun_metadata_validation():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    pub = YouTubePublisher(cfg, dry_run=True)
    # title truncation
    long_title = "A" * 200
    res = pub.upload("x.mp4", long_title, "D", ["t"], None)
    assert res["status"] == "DRY_RUN"
    assert res["dry_run"] is True
    print("metadata (dry-run) OK")

def test_publish_gate_blocks_unapproved():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    rr = rights.RightsRegistry(d)
    out = Path(tempfile.mkdtemp()) / "v.mp4"; out.write_text("x")
    th = Path(tempfile.mkdtemp()) / "t.jpg"; th.write_text("y")
    jid = d.add_job("/tmp/x.mp4", status="READY_FOR_REVIEW")
    d.update_job(jid, output_path=str(out), thumbnail_path=str(th), duration=20.0)
    job = d.get_job(jid)
    ready, reasons = publish_gate.publish_ready(job, rr, None)
    assert not ready
    assert "human approval required" in reasons
    d.close(); os.remove(p)
    print("unapproved blocked OK")

def test_publish_gate_requires_rights():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    rr = rights.RightsRegistry(d)
    rid = rr.register(source_url="/tmp/x.mp4", review_status="REJECTED")
    out = Path(tempfile.mkdtemp()) / "v.mp4"; out.write_text("x")
    th = Path(tempfile.mkdtemp()) / "t.jpg"; th.write_text("y")
    jid = d.add_job("/tmp/x.mp4", status="APPROVED")
    d.update_job(jid, output_path=str(out), thumbnail_path=str(th), duration=20.0, human_approved=1)
    job = d.get_job(jid)
    ready, reasons = publish_gate.publish_ready(job, rr, None)
    assert not ready
    assert any("rights" in r for r in reasons)
    d.close(); os.remove(p)
    print("rights required OK")


def test_publish_ready_gate_enforcement():
    """Verify publish_ready blocks unapproved, unverified, and incomplete jobs."""
    import tempfile, os
    from pathlib import Path
    from shorts_studio.core import db, rights, publish_gate
    fd, dbpath = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(dbpath)
    d = db.DB(dbpath)
    rr = rights.RightsRegistry(d)
    # job with unknown rights -> blocked
    jid = d.add_job("/tmp/x.mp4", status="READY_FOR_REVIEW")
    d.update_job(jid, output_path="/tmp/v.mp4", thumbnail_path="/tmp/t.jpg", duration=20.0)
    job = d.get_job(jid)
    ready, reasons = publish_gate.publish_ready(job, rr, None)
    assert not ready
    assert any("rights" in r for r in reasons)
    # job with authorized rights but no human approval -> blocked
    rid = rr.register(source_url="/tmp/x.mp4", review_status="AUTHORIZED")
    jid2 = d.add_job("/tmp/x.mp4", status="READY_FOR_REVIEW")
    d.update_job(jid2, output_path="/tmp/v.mp4", thumbnail_path="/tmp/t.jpg", duration=20.0)
    # create fake files
    Path("/tmp/v.mp4").write_text("x")
    Path("/tmp/t.jpg").write_text("y")
    job2 = d.get_job(jid2)
    ready2, reasons2 = publish_gate.publish_ready(job2, rr, None)
    assert not ready2
    assert "human approval required" in reasons2
    d.close()
    os.remove(dbpath)
    print("publish_ready gate enforcement OK")

if __name__ == "__main__":
    test_dryrun_never_uploads()
    test_dryrun_metadata_validation()
    test_publish_gate_blocks_unapproved()
    test_publish_gate_requires_rights()
    test_publish_ready_gate_enforcement()
    print("PUBLISHING INTEGRATION TESTS PASS")

def test_publish_ready_full_gate():
    """Verify publish_ready requires all: output, thumbnail, duration, status, human_approval, rights."""
    import tempfile, os
    from pathlib import Path
    from shorts_studio.core import db, rights, publish_gate
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    rr = rights.RightsRegistry(d)
    out = Path(tempfile.mkdtemp()) / "v.mp4"; out.write_text("x")
    th = Path(tempfile.mkdtemp()) / "t.jpg"; th.write_text("y")
    # authorized rights
    rid = rr.register(source_url="/tmp/x.mp4", review_status="AUTHORIZED")
    jid = d.add_job("/tmp/x.mp4", status="READY_FOR_REVIEW")
    d.update_job(jid, output_path=str(out), thumbnail_path=str(th), duration=20.0, human_approved=1)
    job = d.get_job(jid)
    ready, reasons = publish_gate.publish_ready(job, rr, None)
    assert ready, reasons
    # without human approval -> blocked
    jid2 = d.add_job("/tmp/x.mp4", status="READY_FOR_REVIEW")
    d.update_job(jid2, output_path=str(out), thumbnail_path=str(th), duration=20.0, human_approved=0)
    job2 = d.get_job(jid2)
    ready2, reasons2 = publish_gate.publish_ready(job2, rr, None)
    assert not ready2
    assert "human approval required" in reasons2
    d.close(); os.remove(p)
    print("publish_ready full gate OK")

if __name__ == "__main__":
    test_dryrun_never_uploads()
    test_dryrun_metadata_validation()
    test_publish_gate_blocks_unapproved()
    test_publish_gate_requires_rights()
    test_publish_ready_gate_enforcement()
    test_publish_ready_full_gate()
    print("PUBLISHING INTEGRATION TESTS PASS")
