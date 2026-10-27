import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import opportunity, rights, duplicates, scoring
from shorts_studio.media import discovery

def test_opportunity_validation():
    opp = opportunity.make_opportunity("test topic", source_url="https://example.com/v", rights_status="UNKNOWN")
    assert opportunity.validate_opp(opp) == []
    bad = dict(opp); bad["topic"] = ""
    assert opportunity.validate_opp(bad)
    print("opp validation OK")

def test_rights_gate():
    import tempfile, os
    from shorts_studio.core import db
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    d = db.DB(p)
    rr = rights.RightsRegistry(d)
    rid = rr.register(source_url="https://x", review_status="UNKNOWN")
    assert rr.gate(rid)[0] is False
    rr.update_status(rid, "AUTHORIZED")
    assert rr.gate(rid)[0] is True
    # invalid state raises
    try:
        rr.update_status(rid, "BOGUS"); print("FAIL no raise")
    except ValueError:
        print("invalid state rejected OK")
    try: d.close()
    except Exception: pass
    try: os.remove(p)
    except OSError: pass

def test_duplicates():
    c = {"topic": "hello world", "source_url": "https://a.com/v?utm_source=x", "file_hash": "abc"}
    e = [{"topic": "hello world", "source_url": "https://a.com/v", "file_hash": "abc"}]
    isdup, reason, kind = duplicates.check_duplicate(c, e)
    assert isdup and kind == "exact"
    # near duplicate
    c2 = {"topic": "hello world foo bar", "source_url": "https://b.com/v", "file_hash": "zzz"}
    e2 = [{"topic": "hello world foo bar baz", "source_url": "https://a.com/v", "file_hash": "abc"}]
    isdup2, _, kind2 = duplicates.check_duplicate(c2, e2)
    assert kind2 == "near"
    # unrelated
    c3 = {"topic": "completely different topic", "source_url": "https://c.com/v", "file_hash": "yyy"}
    isdup3, _, kind3 = duplicates.check_duplicate(c3, e)
    assert not isdup3 and kind3 == "none"
    # url canonicalization
    assert duplicates.canonicalize_url("https://a.com/v?utm_source=x") == "https://a.com/v"
    print("duplicates OK")

def test_scoring_rights_gate():
    opp = opportunity.make_opportunity("t", rights_status="UNKNOWN")
    moment = {"score": 0.8, "reasons": ["hook"]}
    res = scoring.score_candidate(opp, moment=moment)
    assert res["rights_eligible"] is False
    assert res["final_score"] == 0.0
    # authorized
    opp2 = opportunity.make_opportunity("t2", rights_status="AUTHORIZED")
    res2 = scoring.score_candidate(opp2, moment=moment)
    assert res2["rights_eligible"] is True
    assert res2["final_score"] > 0
    assert "final_score" in res2 and "components" in res2 and "confidence" in res2
    print("scoring OK")

def test_discovery_local():
    ad = discovery.get_adapter("local")
    res = ad.discover(sources_dir=str(ROOT / "data" / "sources"))
    print("local discover:", len(res))
    assert isinstance(res, list)

def test_discovery_tiktok():
    ad = discovery.get_adapter("tiktok")
    res = ad.discover()
    assert any("error" in r for r in res)
    print("tiktok adapter reports limitation OK")

if __name__ == "__main__":
    test_opportunity_validation()
    test_rights_gate()
    test_duplicates()
    test_scoring_rights_gate()
    test_discovery_local()
    test_discovery_tiktok()
    print("PHASE 3 TESTS PASS")