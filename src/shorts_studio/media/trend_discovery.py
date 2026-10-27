"""Automated trend discovery from permitted sources."""
import time, hashlib, json
from shorts_studio.media import discovery
from shorts_studio.core import opportunity, duplicates, scoring

def discover_and_rank(adapters, cfg, db):
    """Run discovery adapters, normalize, dedup, score, store. Returns ranked list."""
    raw_all = []
    for adapter_name, kw in adapters:
        ad = discovery.get_adapter(adapter_name)
        if ad is None:
            continue
        try:
            res = ad.discover(**kw)
        except Exception as e:
            res = [{"error": str(e), "source_adapter": adapter_name}]
        for r in res:
            if "error" in r:
                continue
            raw_all.append(r)
    # normalize to opportunities
    existing = db.list_opportunities()
    opps = []
    for r in raw_all:
        opp = opportunity.make_opportunity(
            r.get("topic", "unknown"),
            source_url=r.get("source_url"),
            source_adapter=r.get("source_adapter", "unknown"),
            rights_status=r.get("rights_status", "UNKNOWN"),
            confidence=0.5,
        )
        # duplicate check
        is_dup, reason, kind = duplicates.check_duplicate(opp, existing + opps)
        opp["duplicate_status"] = kind if is_dup else "none"
        # rights gate already in scoring
        sc = scoring.score_candidate(opp, audio=None)
        opp["_score"] = sc
        opps.append(opp)
    # sort by score desc, then discovery_ts
    opps.sort(key=lambda o: (o["_score"]["final_score"], o["discovery_ts"]), reverse=True)
    # store
    for opp in opps:
        try:
            db.add_opportunity(opp)
        except Exception:
            pass
    return opps