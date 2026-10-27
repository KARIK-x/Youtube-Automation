"""Publish-readiness gate: all safety checks must pass."""
def publish_ready(job, rights_registry=None, cfg=None):
    """Return (ready: bool, reasons: list)."""
    reasons = []
    ready = True
    if job is None:
        return False, ["job missing"]
    if not job.get("output_path") or not __import__("os").path.exists(job["output_path"]):
        ready = False; reasons.append("output missing")
    if not job.get("thumbnail_path") or not __import__("os").path.exists(job.get("thumbnail_path","")):
        ready = False; reasons.append("thumbnail missing")
    dur = job.get("duration")
    if dur is None or not (10 <= dur <= 60):
        ready = False; reasons.append(f"duration invalid: {dur}")
    if job.get("status") not in ("READY_FOR_REVIEW","APPROVED"):
        ready = False; reasons.append(f"status not review-ready: {job.get('status')}")
    if not job.get("human_approved"):
        ready = False; reasons.append("human approval required")
    # rights check via rights_registry if provided
    if rights_registry is not None:
        # look up by source path
        rr = rights_registry
        try:
            ok, reason = rr.gate_by_source(job.get("source_path"))
            if not ok:
                ready = False; reasons.append(f"rights: {reason}")
        except Exception as e:
            ready = False; reasons.append(f"rights check error: {e}")
    if not reasons:
        reasons = ["all checks passed"]
    return ready, reasons
