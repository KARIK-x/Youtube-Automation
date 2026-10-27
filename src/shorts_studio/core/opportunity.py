"""Normalized content opportunity record."""
import json, time, hashlib

OPPORTUNITY_FIELDS = ["opportunity_id","topic","niche","source_url","discovery_ts","publication_ts",
    "engagement_metrics","metrics_ts","trend_growth_evidence","competition","audience_relevance",
    "content_angle","research_notes","source_adapter","confidence","rights_status",
    "duplicate_status","recommended_format"]

def make_opportunity(topic, source_url=None, source_adapter="manual", niche="streamer moments",
                    confidence=0.5, rights_status="UNKNOWN", recommended_format="short"):
    oid = hashlib.sha1(f"{topic}|{source_url}|{time.time()}".encode()).hexdigest()[:12]
    return {
        "opportunity_id": oid,
        "topic": topic,
        "niche": niche,
        "source_url": source_url,
        "discovery_ts": time.time(),
        "publication_ts": None,
        "engagement_metrics": None,
        "metrics_ts": None,
        "trend_growth_evidence": None,
        "competition": None,
        "audience_relevance": None,
        "content_angle": None,
        "research_notes": None,
        "source_adapter": source_adapter,
        "confidence": confidence,
        "rights_status": rights_status,
        "duplicate_status": "unchecked",
        "recommended_format": recommended_format,
    }

def validate_opp(opp):
    errs = []
    if not opp.get("topic"):
        errs.append("topic required")
    if opp.get("confidence", 0) < 0 or opp.get("confidence", 0) > 1:
        errs.append("confidence 0-1")
    if opp.get("recommended_format") not in ("short","long","both"):
        errs.append("recommended_format must be short/long/both")
    return errs
