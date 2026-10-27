import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import db, rights, publish_gate

def test_gate_blocks_missing_output():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    jid = d.add_job("/tmp/x.mp4", status="READY_FOR_REVIEW")
    job = d.get_job(jid)
    ready, reasons = publish_gate.publish_ready(job, rights.RightsRegistry(d), None)
    assert not ready
    assert any("output missing" in r or "thumbnail missing" in r for r in reasons)
    d.close(); os.remove(p)
    print("missing output blocked OK")

def test_gate_requires_human_approval():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    # create fake output + thumbnail
    out = Path(tempfile.mkdtemp()) / "v.mp4"; out.write_text("x")
    th = Path(tempfile.mkdtemp()) / "t.jpg"; th.write_text("y")
    jid = d.add_job("/tmp/x.mp4", status="READY_FOR_REVIEW")
    d.update_job(jid, output_path=str(out), thumbnail_path=str(th), duration=20.0)
    job = d.get_job(jid)
    ready, reasons = publish_gate.publish_ready(job, rights.RightsRegistry(d), None)
    assert not ready
    assert "human approval required" in reasons
    # approve
    d.update_job(jid, human_approved=1, status="APPROVED")
    job = d.get_job(jid)
    # rights still unknown -> blocked
    ready2, reasons2 = publish_gate.publish_ready(job, rights.RightsRegistry(d), None)
    assert not ready2
    assert any("rights" in r for r in reasons2)
    d.close(); os.remove(p)
    print("human approval + rights gate OK")

def test_gate_all_pass():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    rr = rights.RightsRegistry(d)
    rid = rr.register(source_url="/tmp/x.mp4", review_status="AUTHORIZED")
    out = Path(tempfile.mkdtemp()) / "v.mp4"; out.write_text("x")
    th = Path(tempfile.mkdtemp()) / "t.jpg"; th.write_text("y")
    jid = d.add_job("/tmp/x.mp4", status="APPROVED")
    d.update_job(jid, output_path=str(out), thumbnail_path=str(th), duration=20.0, human_approved=1)
    job = d.get_job(jid)
    ready, reasons = publish_gate.publish_ready(job, rr, None)
    assert ready, reasons
    d.close(); os.remove(p)
    print("all-pass gate OK")

if __name__ == "__main__":
    test_gate_blocks_missing_output()
    test_gate_requires_human_approval()
    test_gate_all_pass()
    print("PUBLISH GATE TESTS PASS")