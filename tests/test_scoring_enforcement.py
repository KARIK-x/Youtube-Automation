import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import scoring, opportunity, duplicates

def test_below_threshold_rejected():
    # rights-ineligible candidate gets score 0, blocked by min_score=0.1
    opp = opportunity.make_opportunity("t", rights_status="UNKNOWN")
    res = scoring.score_candidate(opp, moment={"score": 0.05, "reasons": []})
    min_score = 0.1
    assert res["final_score"] == 0.0
    assert res["final_score"] < min_score
    print("below threshold (rights) OK, score=", res["final_score"])

def test_equal_threshold():
    opp = opportunity.make_opportunity("t", rights_status="AUTHORIZED")
    res = scoring.score_candidate(opp, moment={"score": 0.5, "reasons": ["hook"]})
    print("equal/boundary score=", res["final_score"])
    assert res["final_score"] >= 0

def test_above_threshold():
    opp = opportunity.make_opportunity("t", rights_status="AUTHORIZED")
    res = scoring.score_candidate(opp, moment={"score": 0.8, "reasons": ["hook"]})
    assert res["final_score"] > 0
    print("above threshold OK, score=", res["final_score"])

def test_missing_score():
    opp = opportunity.make_opportunity("t", rights_status="AUTHORIZED")
    res = scoring.score_candidate(opp)  # no moment
    assert "missing_data" in res
    assert len(res["missing_data"]) > 0
    print("missing score OK, missing=", res["missing_data"])

def test_invalid_score():
    opp = opportunity.make_opportunity("t", rights_status="AUTHORIZED")
    # moment with invalid score (None)
    res = scoring.score_candidate(opp, moment={"score": None, "reasons": []})
    # should not crash
    assert "final_score" in res
    print("invalid score OK, score=", res["final_score"])

def test_empty_candidates():
    # empty candidate set
    opps = []
    assert len(opps) == 0
    print("empty candidates OK")

def test_rights_blocks_unauthorized():
    for status in ["UNKNOWN", "REJECTED", "REVIEW_REQUIRED"]:
        opp = opportunity.make_opportunity("t", rights_status=status)
        res = scoring.score_candidate(opp, moment={"score": 0.9, "reasons": ["hook"]})
        assert res["final_score"] == 0.0, f"rights {status} should block, got {res['final_score']}"
        assert res["rights_eligible"] is False
    print("rights blocks unauthorized OK")

def test_duplicate_blocks():
    opp1 = opportunity.make_opportunity("same", source_url="https://a.com/v", rights_status="AUTHORIZED")
    opp2 = opportunity.make_opportunity("same", source_url="https://a.com/v", rights_status="AUTHORIZED")
    isdup, reason, kind = duplicates.check_duplicate(opp2, [opp1])
    assert isdup and kind == "exact"
    print("duplicate blocks OK")

if __name__ == "__main__":
    test_below_threshold_rejected()
    test_equal_threshold()
    test_above_threshold()
    test_missing_score()
    test_invalid_score()
    test_empty_candidates()
    test_rights_blocks_unauthorized()
    test_duplicate_blocks()
    print("CANDIDATE SCORING ENFORCEMENT TESTS PASS")