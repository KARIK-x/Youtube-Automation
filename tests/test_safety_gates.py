import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import db, rights, duplicates, scoring, opportunity

def test_rights_gate_blocks_unknown():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    rr = rights.RightsRegistry(d)
    rid = rr.register(source_url="https://x", review_status="UNKNOWN")
    assert rr.gate(rid)[0] is False
    # rejected also blocked
    rid2 = rr.register(source_url="https://y", review_status="REJECTED")
    assert rr.gate(rid2)[0] is False
    # authorized passes
    rid3 = rr.register(source_url="https://z", review_status="AUTHORIZED")
    assert rr.gate(rid3)[0] is True
    d.close(); os.remove(p)
    print("rights gate OK")

def test_scoring_rights_hard_gate():
    opp = opportunity.make_opportunity("t", rights_status="UNKNOWN")
    res = scoring.score_candidate(opp, moment={"score":0.9,"reasons":["hook"]})
    assert res["rights_eligible"] is False
    assert res["final_score"] == 0.0
    # high score can't override
    opp2 = opportunity.make_opportunity("t2", rights_status="REJECTED")
    res2 = scoring.score_candidate(opp2, moment={"score":1.0,"reasons":["hook"]})
    assert res2["final_score"] == 0.0
    print("scoring hard gate OK")

def test_duplicate_exact_blocks():
    c = {"topic":"same topic","source_url":"https://a.com/v","file_hash":"h1"}
    e = [{"topic":"same topic","source_url":"https://a.com/v","file_hash":"h1"}]
    isdup, reason, kind = duplicates.check_duplicate(c, e)
    assert isdup and kind == "exact"
    print("duplicate exact OK")

def test_job_blocked_status():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    jid = d.add_job("/tmp/x.mp4", status="BLOCKED")
    j = d.get_job(jid)
    assert j["status"] == "BLOCKED"
    d.close()
    os.remove(p)
    print("blocked job status OK")

if __name__ == "__main__":
    test_rights_gate_blocks_unknown()
    test_scoring_rights_hard_gate()
    test_duplicate_exact_blocks()
    test_job_blocked_status()
    print("SAFETY GATE TESTS PASS")