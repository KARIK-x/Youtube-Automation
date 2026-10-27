import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import opportunity, scoring, duplicates, rights, db

def test_rejected_candidate_blocked():
    # low score candidate (rights unknown -> score 0)
    opp = opportunity.make_opportunity("weak", rights_status="UNKNOWN")
    res = scoring.score_candidate(opp, moment={"score": 0.1, "reasons": []})
    assert res["final_score"] == 0.0
    assert res["rights_eligible"] is False
    # min_score gate
    min_score = 0.1
    assert res["final_score"] < min_score
    print("weak candidate blocked by score OK")

def test_duplicate_candidate_blocked():
    opp1 = opportunity.make_opportunity("same topic", source_url="https://a.com/v", rights_status="AUTHORIZED")
    opp2 = opportunity.make_opportunity("same topic", source_url="https://a.com/v", rights_status="AUTHORIZED")
    isdup, reason, kind = duplicates.check_duplicate(opp2, [opp1])
    assert isdup and kind == "exact"
    print("duplicate candidate blocked OK")

def test_high_score_cannot_override_rights():
    opp = opportunity.make_opportunity("t", rights_status="REJECTED")
    res = scoring.score_candidate(opp, moment={"score": 1.0, "reasons": ["hook"]})
    assert res["final_score"] == 0.0
    assert res["rights_eligible"] is False
    print("rights hard gate (high score) OK")

def test_missing_data_recorded():
    opp = opportunity.make_opportunity("t", rights_status="AUTHORIZED")
    res = scoring.score_candidate(opp)  # no moment, no audio
    assert "missing_data" in res
    assert len(res["missing_data"]) > 0
    print("missing data recorded:", res["missing_data"])

def test_candidate_reasons_present():
    opp = opportunity.make_opportunity("t", rights_status="AUTHORIZED")
    res = scoring.score_candidate(opp, moment={"score": 0.5, "reasons": ["hook"]})
    assert len(res["reasons"]) > 0
    assert "final_score" in res and "components" in res and "confidence" in res
    print("candidate reasons OK")

if __name__ == "__main__":
    test_rejected_candidate_blocked()
    test_duplicate_candidate_blocked()
    test_high_score_cannot_override_rights()
    test_missing_data_recorded()
    test_candidate_reasons_present()
    print("CANDIDATE QUALITY GATE TESTS PASS")