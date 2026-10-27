"""Single source-processing pipeline, shared by `run` and `run-daily`.

Before this module existed, `cmd_run` and `cmd_run_daily` each had their own copy of
the pipeline, and the copies drifted (run-daily skipped thumbnails, scoring and the
duplicate gate). Everything now goes through `process_source`.

Ordering is deliberate and non-negotiable:
    rights gate -> transcribe -> analyse -> pick moment -> duplicate gate
    -> candidate score gate -> plan -> validate -> render -> QC -> publish artefacts
"""
from pathlib import Path

from shorts_studio.core import duplicates, output_safety, opportunity, scoring
from shorts_studio.core import rights as rights_mod
from shorts_studio.editing import edl, moment_selector, planner, qc, renderer
from shorts_studio.media import audio_analysis, scene_detect, thumbnail, transcribe

CLEARED_RIGHTS = ("AUTHORIZED", "LICENSED", "PUBLIC_DOMAIN_VERIFIED")


def _noop(*_a, **_kw):
    pass


def process_source(cfg, db, root, src, profile=None, *, allow_unverified=False,
                   min_score=None, job_id=None, move_source=False, beat_cuts=None,
                   narration_path=None, niche=None, log=print):
    """Run the full Shorts pipeline for one source file.

    Returns a dict: {status, job_id, output, thumbnail, qc, reason, timings}.
    `status` is one of OK / BLOCKED / FAILED.

    Raises only for unexpected programming errors; expected production failures are
    reported through the return value so the caller (runner) can apply its own policy.
    """
    root = Path(root)
    src = str(src)
    name = Path(src).stem
    profile = profile or cfg["profiles"]["default"]

    # apply niche profile if specified
    if niche:
        from shorts_studio.editing import niche as niche_mod
        cfg = niche_mod.apply_niche_to_config(cfg, niche)
        log(f"  niche: {niche} (zoom={cfg['editing'].get('zoom_factor')}, music={cfg['audio'].get('music_mood')})")
    moments_log = log if log else _noop

    def _mark(status, **kw):
        if job_id is not None:
            db.update_job(job_id, status=status, **kw)
            return job_id
        jid = db.add_job(src, profile=profile, status="RENDERING")
        db.update_job(jid, status=status, **kw)
        return jid

    # ---- 1. rights gate (hard) -------------------------------------------------
    rr = rights_mod.RightsRegistry(db)
    allowed, reason = rr.gate_by_source(src)
    if not allowed and not allow_unverified:
        jid = _mark("BLOCKED", error=reason)
        moments_log(f"  BLOCKED: {reason} (use --allow-unverified for local testing)")
        return {"status": "BLOCKED", "job_id": jid, "reason": reason,
                "output": None, "thumbnail": None, "qc": None}
    if not allowed:
        moments_log(f"  rights not cleared ({reason}) — allowed for local testing only; "
                    f"this job is NOT publishable")

    # ---- 2. transcribe + analyse ----------------------------------------------
    work = root / cfg["content"]["work_dir"] / name
    srt, ass, segs = transcribe.transcribe(src, str(work), "base")
    audio = audio_analysis.analyze(src)
    scenes = scene_detect.detect_scene_changes(src)

    # ---- 3. choose the moment --------------------------------------------------
    cands = moment_selector.select_candidates(audio["duration"], segs, audio, scenes, cfg)
    best = cands[0] if cands else None
    moment = {"start": best["start"], "end": best["end"]} if best else None

    # ---- 4. duplicate gate + candidate scoring ---------------------------------
    # The rights status must come from the registry, not be hardcoded to UNKNOWN,
    # otherwise a legitimately cleared source can never pass the score gate.
    rights_status = "AUTHORIZED" if allowed else "UNKNOWN"
    opp = opportunity.make_opportunity(name, source_url=None, source_adapter="local",
                                       rights_status=rights_status)
    is_dup, dup_reason, dup_kind = duplicates.check_duplicate(opp, db.list_opportunities())
    opp["duplicate_status"] = dup_kind if is_dup else "none"
    if is_dup and dup_kind == "exact":
        jid = _mark("BLOCKED", error=f"exact duplicate: {dup_reason}")
        moments_log(f"  BLOCKED: exact duplicate ({dup_reason})")
        return {"status": "BLOCKED", "job_id": jid, "reason": dup_reason,
                "output": None, "thumbnail": None, "qc": None}

    score_res = scoring.score_candidate(opp, moment=best, audio=audio)
    threshold = min_score if min_score is not None else cfg.get("candidate", {}).get("min_score", 0.1)
    if allow_unverified:
        threshold = 0.0
    moments_log(f"  score={score_res['final_score']} rights_eligible={score_res['rights_eligible']} "
                f"conf={score_res['confidence']} dup={opp['duplicate_status']} min={threshold}")
    moments_log(f"  reasons={score_res['reasons']}")
    if score_res["final_score"] < threshold and threshold > 0:
        jid = _mark("BLOCKED", error=f"score {score_res['final_score']} < min_score {threshold}")
        moments_log(f"  BLOCKED: score {score_res['final_score']} < min_score {threshold}")
        return {"status": "BLOCKED", "job_id": jid,
                "reason": f"below min_score {threshold}", "output": None,
                "thumbnail": None, "qc": None, "score": score_res["final_score"]}

    # ---- 5. plan -> validate -> render -----------------------------------------
    if beat_cuts is None:
        beat_cuts = bool(cfg.get("editing", {}).get("beat_synced_cuts", False))
    e = planner.plan(src, segs, profile=profile, target_duration=30,
                     moment=moment, audio=audio, scene_changes=scenes, beat_cuts=beat_cuts)
    if narration_path and os.path.exists(narration_path):
        e["narration"] = str(narration_path)
        log(f"  using narration audio: {narration_path}")
    edl.validate_or_raise(e, cfg)
    moments_log(f"  candidates: {len(cands)}; selected {moment}")

    final = renderer.render(e, str(work), cfg)
    quality = qc.qc(final, cfg)

    # ---- 6. publish artefacts (never overwrite) --------------------------------
    out_dir = root / cfg["content"]["output_dir"]
    out = output_safety.unique_path(out_dir, f"{name}_final.mp4")
    output_safety.atomic_copy(final, out)

    title = name.replace("_", " ").title()[:40]
    thumb = output_safety.unique_path(out_dir, f"{name}_thumb.jpg")
    try:
        thumbnail.make_thumbnail(final, title, str(thumb), cfg)
    except Exception as e_thumb:  # a thumbnail must not lose a finished video
        moments_log(f"  thumbnail failed: {e_thumb}")
        thumb = None

    status = "READY_FOR_REVIEW" if quality["passed"] else "FAILED"
    jid = _mark(status,
                output_path=str(out),
                duration=quality["checks"].get("duration"),
                thumbnail_path=str(thumb) if thumb else None,
                error=None if quality["passed"] else "; ".join(quality["errors"]))
    moments_log(f"[{jid}] {Path(src).name}: QC={'PASS' if quality['passed'] else 'FAIL'} -> {out.name}")

    if move_source and quality["passed"]:
        done = root / cfg["content"]["sources_dir"] / "_done"
        done.mkdir(parents=True, exist_ok=True)
        try:
            Path(src).rename(done / Path(src).name)
        except OSError as e_move:
            moments_log(f"  could not archive source: {e_move}")

    return {"status": "OK" if quality["passed"] else "FAILED", "job_id": jid,
            "output": str(out), "thumbnail": str(thumb) if thumb else None,
            "qc": quality, "reason": None if quality["passed"] else "; ".join(quality["errors"]),
            "score": score_res["final_score"], "rights_status": rights_status}
