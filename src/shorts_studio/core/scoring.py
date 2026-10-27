"""Candidate scoring (heuristic, transparent)."""
def score_candidate(opp, moment=None, audio=None):
    """Return dict with component scores, final score, reasons, confidence, missing data."""
    components = {}
    reasons = []
    missing = []
    # content quality (from moment)
    cq = 0.5
    if moment:
        ms = moment.get("score")
        if ms is not None:
            try:
                cq = float(ms)
                import math
                if not math.isfinite(cq):
                    cq = 0.5
            except (TypeError, ValueError):
                cq = 0.5
        reasons += moment.get("reasons", [])
    components["content_quality"] = round(cq, 3)
    # trend opportunity (from opp engagement if available)
    to = 0.5
    metrics = opp.get("engagement_metrics")
    if metrics:
        # naive: more views -> higher, normalized log-ish
        views = metrics.get("views", 0)
        to = min(1.0, (views or 0) / 100000.0)
        reasons.append("engagement_signal")
    else:
        missing.append("engagement_metrics")
    components["trend_opportunity"] = round(to, 3)
    # rights eligibility (hard gate, separate dimension)
    rights = opp.get("rights_status", "UNKNOWN")
    rights_ok = rights in ("AUTHORIZED","LICENSED","PUBLIC_DOMAIN_VERIFIED")
    components["rights_eligible"] = 1.0 if rights_ok else 0.0
    if not rights_ok:
        reasons.append(f"rights_not_cleared:{rights}")
    # production feasibility
    pf = 0.8
    if audio and audio.get("clipping", {}).get("clipping"):
        pf -= 0.2; reasons.append("audio_clipping")
    if audio and (audio.get("silence") and sum(s["duration"] for s in audio["silence"]) > 5):
        pf -= 0.1; reasons.append("excess_silence")
    components["production_feasibility"] = round(pf, 3)
    # duplicate risk
    dup = 0.0 if opp.get("duplicate_status") == "none" else 0.5
    if opp.get("duplicate_status") in ("exact",):
        dup = 1.0
    components["duplicate_risk"] = round(dup, 3)
    # final (rights is hard gate: if not eligible, final 0)
    if not rights_ok:
        final = 0.0
    else:
        final = (0.4*components["content_quality"] + 0.25*components["trend_opportunity"]
                 + 0.2*components["production_feasibility"] + 0.15*(1-components["duplicate_risk"]))
        final = max(0.0, min(1.0, final))
    # confidence
    conf = 0.4
    if metrics: conf += 0.2
    if moment: conf += 0.2
    if audio: conf += 0.1
    conf = min(1.0, conf)
    return {
        "final_score": round(final, 3),
        "components": components,
        "reasons": reasons,
        "missing_data": missing,
        "confidence": round(conf, 3),
        "rights_eligible": rights_ok,
    }
