import sys, tempfile, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import db

def test_db_job_lifecycle():
    fd, p = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(p)
    d = db.DB(p)
    jid = d.add_job("/tmp/x.mp4", profile="chaos", status="DISCOVERED")
    assert jid > 0
    d.update_job(jid, status="ANALYZED")
    j = d.get_job(jid)
    assert j["status"] == "ANALYZED"
    assert "READY_FOR_REVIEW" in db.VALID_STATUSES
    # invalid status raises
    try:
        d.update_job(jid, status="NOPE")
        print("FAIL: no exception")
    except ValueError:
        print("invalid status rejected OK")
    d.close()
    os.remove(p)
    print("DB OK")

def test_db_counts():
    fd, p = tempfile.mkstemp(suffix=".db")
    os.close(fd); os.remove(p)
    d = db.DB(p)
    for s in ["DISCOVERED","FAILED"]:
        d.add_job("/tmp/x.mp4", status=s)
    assert d.count_by_status()["DISCOVERED"] == 1
    d.close(); os.remove(p)
    print("counts OK")

if __name__ == "__main__":
    test_db_job_lifecycle(); test_db_counts()
    print("ALL DB TESTS PASS")
