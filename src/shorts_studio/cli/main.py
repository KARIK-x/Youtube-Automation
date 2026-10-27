#!/usr/bin/env python3
"""Shorts Studio CLI."""
import argparse, os, sys, json, time, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

from shorts_studio.core import config, db as dbmod
from shorts_studio.media import source, transcribe, editor
from shorts_studio.editing import edl, planner, renderer, qc, moment_selector

def load():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    db = dbmod.DB(cfg["db"]["path"])
    return cfg, db

def cmd_check_deps(args):
    import shutil
    deps = {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe"),
            "python": sys.executable}
    for k,v in deps.items():
        print(f"{k}: {v or 'MISSING'}")
    try:
        import faster_whisper, cv2, PIL, yaml, edge_tts
        print("python modules: OK (faster_whisper, cv2, PIL, yaml, edge_tts)")
    except Exception as e:
        print("module import error:", e)
    # av version check
    try:
        import av
        print(f"av version: {av.__version__} (required 12.3.0)")
        if av.__version__ != "12.3.0":
            print("WARNING: av version mismatch; transcription may fail")
    except Exception as e:
        print("av import error:", e)
    # scipy/numpy
    try:
        import scipy, numpy
        print(f"scipy {scipy.__version__}, numpy {numpy.__version__}")
    except Exception as e:
        print("scipy/numpy error:", e)
    return 0

def cmd_inspect(args):
    info = editor.probe(args.path)
    print(json.dumps(info, indent=2))
    return 0

def cmd_analyze(args):
    cfg, db = load()
    segs = None
    srt, ass, segs = transcribe.transcribe(args.path, str(ROOT / "data" / "work" / "analyze"), "base")
    print(f"segments: {len(segs)}")
    for s in segs[:5]:
        print(f"  {s.start:.2f}-{s.end:.2f}: {s.text.strip()}")
    # audio analysis
    from shorts_studio.media import audio_analysis, scene_detect
    a = audio_analysis.analyze(args.path)
    print(f"audio: dur={a['duration']} bpm={a['bpm']} onsets={a['onset_count']} silence={len(a['silence'])} clipping={a['clipping']['clipping']}")
    sc = scene_detect.detect_scene_changes(args.path)
    print(f"scene changes: {len(sc)}")
    cands = moment_selector.select_candidates(a["duration"], segs, a, sc, cfg)
    print(f"candidates: {len(cands)}")
    for c in cands[:5]:
        print(f"  {c['start']:.2f}-{c['end']:.2f} score={c['score']} conf={c['confidence']} reasons={c['reasons']}")
    return 0

def cmd_plan(args):
    cfg, db = load()
    srt, ass, segs = transcribe.transcribe(args.path, str(ROOT / "data" / "work" / "plan"), "base")
    from shorts_studio.media import audio_analysis, scene_detect
    audio = audio_analysis.analyze(args.path)
    scenes = scene_detect.detect_scene_changes(args.path)
    cands = moment_selector.select_candidates(audio["duration"], segs, audio, scenes, cfg)
    moment = {"start": cands[0]["start"], "end": cands[0]["end"]} if cands else None
    prof = args.profile or cfg["profiles"]["default"]
    e = planner.plan(args.path, segs, profile=prof, target_duration=args.duration,
                    moment=moment, audio=audio, scene_changes=scenes)
    errs = edl.validate(e, cfg)
    print(json.dumps(e, indent=2))
    print("VALIDATION:", "OK" if not errs else errs)
    print("top candidate:", cands[0] if cands else None)
    if args.out:
        Path(args.out).write_text(json.dumps(e, indent=2))
    return 0 if not errs else 1

def cmd_validate(args):
    cfg, db = load()
    e = json.loads(Path(args.path).read_text())
    errs = edl.validate(e, cfg)
    print("VALID" if not errs else "INVALID: " + "; ".join(errs))
    return 0 if not errs else 1

def cmd_render(args):
    cfg, db = load()
    e = json.loads(Path(args.plan).read_text())
    edl.validate_or_raise(e, cfg)
    work = ROOT / "data" / "work" / "render"
    work.mkdir(parents=True, exist_ok=True)
    out_name = getattr(args, "output", None) or "final.mp4"
    target = ROOT / "data" / "output" / out_name
    if target.exists() and not getattr(args, "force", False):
        stem = Path(out_name).stem
        suf = Path(out_name).suffix
        i = 1
        while (ROOT / "data" / "output" / f"{stem}_{i}{suf}").exists():
            i += 1
        out_name = f"{stem}_{i}{suf}"
        target = ROOT / "data" / "output" / out_name
        print(f"[render] output exists; using {out_name}")
    final = renderer.render(e, str(work), cfg, final_name=out_name)
    print("rendered:", final)
    q = qc.qc(final, cfg)
    print("QC:", "PASS" if q["passed"] else "FAIL", q["errors"])
    print(json.dumps(q["checks"], indent=2))
    import shutil
    if Path(final).resolve() != target.resolve():
        from shorts_studio.core import output_safety
        output_safety.atomic_copy(final, target)
    print("output:", target)
    job_id = db.add_job(e["source"], profile=e["profile"], status="RENDERING")
    db.update_job(job_id, status="QUALITY_CHECK" if q["passed"] else "FAILED",
                  output_path=str(target), duration=q["checks"].get("duration"),
                  error=None if q["passed"] else "; ".join(q["errors"]))
    if q["passed"]:
        db.update_job(job_id, status="READY_FOR_REVIEW")
    return 0 if q["passed"] else 1

def cmd_qc(args):
    cfg, db = load()
    q = qc.qc(args.path, cfg)
    print(json.dumps(q, indent=2))
    return 0 if q["passed"] else 1

def cmd_jobs(args):
    cfg, db = load()
    for j in db.list_jobs(limit=args.limit):
        print(f"{j['id']:4} {j['status']:<20} {j['profile']:<10} {Path(j['source_path']).name}")
    print("counts:", db.count_by_status())
    return 0

def cmd_run(args):
    """Process every local source once, through the shared pipeline."""
    cfg, db = load()
    niche_name = getattr(args, "niche", None)
    if niche_name:
        from shorts_studio.editing import niche as niche_mod
        cfg = niche_mod.apply_niche_to_config(cfg, niche_name)
        print(f"niche: {niche_name}")
    srcs = source.collect_local(str(ROOT / cfg["content"]["sources_dir"]))
    srcs += source.collect_urls(str(ROOT / cfg["content"]["sources_dir"]), str(ROOT / cfg["content"]["work_dir"]))
    if not srcs:
        print("No sources found in", cfg["content"]["sources_dir"])
        return 0

    t0 = time.time()
    # trend discovery (best-effort, never blocks production)
    try:
        from shorts_studio.queue.runner import DailyRunner
        opps = DailyRunner(cfg, db).discover(cfg, db)
        print(f"Discovery: {len(opps)} opportunities found")
    except Exception as e:
        print(f"Discovery skipped: {e}")

    from shorts_studio.queue import pipeline
    prof = args.profile or cfg["profiles"]["default"]
    allow = getattr(args, "allow_unverified", False)
    min_score = getattr(args, "min_score", None)
    beat_cuts = getattr(args, "beat_cuts", False) or bool(cfg.get("editing", {}).get("beat_synced_cuts", False))
    narration = getattr(args, "narration", None)
    produced, blocked, failed = 0, 0, 0
    for src in srcs[:cfg["youtube"]["max_uploads_per_day"]]:
        print(f"\n=== {Path(src).name} ===")
        try:
            res = pipeline.process_source(
                cfg, db, ROOT, src, prof,
                allow_unverified=allow, min_score=min_score, move_source=True,
                beat_cuts=beat_cuts, narration_path=narration,
                niche=getattr(args, "niche", None))
        except Exception as ex:
            failed += 1
            print(f"  ERROR: {type(ex).__name__}: {ex}")
            continue
        if res["status"] == "OK":
            produced += 1
        elif res["status"] == "BLOCKED":
            blocked += 1
        else:
            failed += 1

    db.log_run(t0, time.time(), produced, [])
    print(f"\nproduced={produced} blocked={blocked} failed={failed} "
          f"in {time.time()-t0:.1f}s")
    return 0


SCOPE_LABELS = {
    "https://www.googleapis.com/auth/youtube.upload": "youtube.upload",
    "https://www.googleapis.com/auth/youtube": "youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly": "yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly": "yt-analytics-monetary",
}


def _token_state(token_file):
    """Inspect the OAuth token WITHOUT printing any secret material."""
    info = {"present": False}
    if not token_file or not os.path.exists(token_file):
        return info
    st = os.stat(token_file)
    info.update({"present": True, "mode": oct(st.st_mode & 0o777),
                 "bytes": st.st_size, "scopes": None,
                 "has_refresh": False, "valid": False, "expired": None})
    try:
        import pickle
        with open(token_file, "rb") as f:
            creds = pickle.load(f)
        scopes = getattr(creds, "scopes", None) or []
        info["scopes"] = [SCOPE_LABELS.get(s, s.rsplit("/", 1)[-1]) for s in scopes]
        info["has_refresh"] = bool(getattr(creds, "refresh_token", None))
        info["valid"] = bool(getattr(creds, "valid", False))
        info["expired"] = bool(getattr(creds, "expired", False))
    except Exception as e:  # corrupt / keyring-backed / not a pickle
        info["unreadable"] = type(e).__name__
    return info


def _audio_asset_state(cfg):
    """Report licensed vs test audio assets from the central libraries."""
    lib = Path(cfg.get("audio", {}).get("music_library_dir", "data/audio_library"))
    if not lib.is_absolute():
        lib = ROOT / lib
    music_assets = []
    sfx_assets = []
    try:
        from shorts_studio.media import music_library
        music_assets = music_library.load_library(str(lib))
    except Exception:
        pass
    try:
        import shorts_studio.editing.sfx as sfx_mod
        sfx_assets = sfx_mod.load_sfx_library(str(lib))
    except Exception:
        pass
    music_registered = [a for a in music_assets if a.get("permitted_use") != "none"]
    music_licensed = [a for a in music_registered if a.get("permitted_use") in ("publish", "internal")]
    music_test = [a for a in music_registered if a.get("permitted_use") == "test"]
    sfx_registered = [a for a in sfx_assets if a.get("permitted_use") != "none"]
    sfx_licensed = [a for a in sfx_registered if a.get("permitted_use") in ("publish", "internal")]
    sfx_test = [a for a in sfx_registered if a.get("permitted_use") == "test"]
    unregistered = (len(music_assets) - len(music_registered)) + (len(sfx_assets) - len(sfx_registered))
    return (len(music_registered), len(music_licensed), len(music_test),
            len(sfx_registered), len(sfx_licensed), unregistered, lib)


def cmd_status(args):
    cfg, db = load()
    yt = cfg.get("youtube", {})
    offline = getattr(args, "offline", False)
    width, height = cfg["video"]["width"], cfg["video"]["height"]

    print()
    print(f"  Shorts Studio — {cfg['channel']['name']}  ({width}x{height})")
    print("  " + "-" * 58)

    # ---- OAuth -------------------------------------------------------
    tok = _token_state(yt.get("token_file"))
    client = yt.get("client_secrets")
    client_ok = bool(client and os.path.exists(client))
    live = None
    if tok["present"] and not offline:
        try:
            from shorts_studio.youtube.publishing import YouTubePublisher
            live = YouTubePublisher(cfg, dry_run=True).channel_info()
        except Exception as e:
            live = {"error": type(e).__name__}

    if not tok["present"]:
        print("  YouTube auth   NOT AUTHORIZED — run: python -m shorts_studio.cli.main auth")
    elif live and live.get("error"):
        print(f"  YouTube auth   token present, live check failed ({live['error']})")
    elif live:
        print(f"  YouTube auth   AUTHORIZED as '{live.get('title')}' "
              f"({live.get('subscriber_count')} subs, {live.get('video_count')} videos)")
    else:
        state = "valid" if tok.get("valid") else ("refreshable" if tok.get("has_refresh") else "needs refresh")
        print(f"  YouTube auth   token present, locally {state} (offline check)")
    if tok["present"]:
        perms = "600 (private)" if tok.get("mode") == "0o600" else f"{tok.get('mode')} (should be 600)"
        print(f"                 token perms {perms} · client_secret {'OK' if client_ok else 'MISSING'}")
        if tok.get("scopes"):
            print(f"                 scopes: {', '.join(tok['scopes'])}")

    # ---- publishing / analytics capability ---------------------------
    dry = bool(yt.get("dry_run", True))
    can_publish = tok["present"] and client_ok and any(
        s in ("youtube", "youtube.upload") for s in (tok.get("scopes") or []))
    if dry:
        print("  Publishing     DRY RUN — nothing is uploaded (youtube.dry_run: true)")
    elif can_publish:
        print("  Publishing     LIVE — uploads enabled (privacy: %s)" % yt.get("privacy", "private"))
    else:
        print("  Publishing     LIVE requested but NOT READY — missing OAuth credentials")
    can_analytics = tok["present"] and any(
        "yt-analytics" in s for s in (tok.get("scopes") or []))
    print(f"  Analytics      {'AUTHORIZED (read-only)' if can_analytics else 'NOT AUTHORIZED'}")

    # ---- tooling -----------------------------------------------------
    import shutil as _sh
    ff = _sh.which("ffmpeg")
    fp = _sh.which("ffprobe")
    try:
        import av
        avv = av.__version__
        avs = "OK" if avv == "12.3.0" else f"MISMATCH (need 12.3.0, have {avv})"
    except Exception:
        avs = "MISSING"
    try:
        import scipy, numpy  # noqa: F401
        audio_lib = "OK"
    except Exception:
        audio_lib = "MISSING"
    print(f"  Tooling        ffmpeg {'OK' if ff else 'MISSING'} · ffprobe {'OK' if fp else 'MISSING'} "
          f"· av {avs} · audio {audio_lib}")

    # ---- assets ------------------------------------------------------
    music_total, music_licensed, music_test, sfx_total, sfx_licensed, unregistered, lib = _audio_asset_state(cfg)
    if music_licensed:
        print(f"  Music assets   {music_licensed} licensed / {music_total} registered")
    elif music_total:
        print(f"  Music assets   {music_total} TEST-ONLY — no licensed music")
        print("                 Shorts fall back to source dialogue")
    else:
        print("  Music assets   NONE — dialogue-only shorts")
    if sfx_licensed:
        print(f"  SFX assets     {sfx_licensed} licensed / {sfx_total} registered")
    elif sfx_total:
        print(f"  SFX assets     {sfx_total} TEST-ONLY")
    if unregistered:
        print(f"  Unregistered   {unregistered} audio files (no library entry) — not usable")

    # ---- jobs --------------------------------------------------------
    jobs = db.count_by_status()
    if jobs:
        pretty = ", ".join(f"{k}:{v}" for k, v in sorted(jobs.items()))
        print(f"  Jobs           {pretty}")
    else:
        print("  Jobs           none yet")
    try:
        free_gb = _sh.disk_usage(str(ROOT)).free / (1024 ** 3)
        print(f"  Disk           {free_gb:.1f} GB free")
    except Exception:
        pass
    print()
    if not offline:
        print("  (use `status --offline` to skip the live YouTube check)")
        print()
    return 0

def cmd_thumbnail(args):
    cfg, db = load()
    from shorts_studio.media import thumbnail
    title = args.title or Path(args.path).stem.replace("_"," ").title()[:40]
    out = args.out or str(ROOT / "data" / "output" / (Path(args.path).stem + "_thumb.jpg"))
    p = thumbnail.make_thumbnail(args.path, title, out, cfg)
    print("thumbnail:", p, os.path.exists(p))
    return 0


def cmd_search_stock(args):
    cfg, db = load()
    from shorts_studio.media import discovery, stock_video
    ad = discovery.get_adapter("pexels")
    kw = {"query": args.query, "per_page": args.count or 8,
          "download": getattr(args, "download", False),
          "download_dir": args.out_dir, "min_duration": args.min_duration or 3}
    if getattr(args, "api_key", None):
        kw["api_key"] = args.api_key
    res = ad.discover(**kw)
    for r in res:
        if "error" in r:
            print("ERROR:", r["error"]); continue
        print(f"  {r.get('topic','?')[:60]}  dur={r.get('duration')}s  rights={r.get('rights_status')}")
        if r.get("local_path"):
            print(f"     -> {r['local_path']}")
        elif r.get("download_url"):
            print(f"     url: {r['download_url'][:80]}...")
    return 0
    from shorts_studio.core import opportunity, rights, duplicates
    adapter = discovery.get_adapter(args.adapter)
    if adapter is None:
        print("unknown adapter", args.adapter); return 1
    kw = {}
    if args.sources_dir: kw["sources_dir"] = args.sources_dir
    if args.channel_id: kw["channel_id"] = args.channel_id
    if args.query: kw["query"] = args.query
    if args.adapter == "local" and not kw.get("sources_dir"):
        kw["sources_dir"] = str(ROOT / cfg["content"]["sources_dir"])
    raw = adapter.discover(**kw)
    print(f"adapter {args.adapter}: {len(raw)} results")
    rr = rights.RightsRegistry(db)
    existing = db.list_opportunities()
    for r in raw:
        if "error" in r:
            print("  ERROR:", r["error"]); continue
        opp = opportunity.make_opportunity(r.get("topic","unknown"), source_url=r.get("source_url"),
                                          source_adapter=r.get("source_adapter", args.adapter),
                                          rights_status=r.get("rights_status","UNKNOWN"))
        # duplicate check
        is_dup, reason, kind = duplicates.check_duplicate(opp, existing)
        opp["duplicate_status"] = kind if is_dup else "none"
        # rights register
        rid = rr.register(source_url=opp["source_url"], creator=None, acquisition_method=args.adapter,
                          license_type="UNKNOWN", review_status="UNKNOWN")
        db.add_opportunity(opp)
        print(f"  {opp['opportunity_id']} {opp['topic'][:60]} dup={opp['duplicate_status']} rights={opp['rights_status']}")
    return 0

def cmd_publish_dryrun(args):
    cfg, db = load()
    from shorts_studio.youtube.publishing import YouTubePublisher
    from shorts_studio.core import publish_gate
    job = None
    if getattr(args, "job_id", None):
        job = db.get_job(args.job_id)
        ready, reasons = publish_gate.publish_ready(job, rights.RightsRegistry(db) if False else None, cfg)
        # rights registry
        from shorts_studio.core import rights
        ready, reasons = publish_gate.publish_ready(job, rights.RightsRegistry(db), cfg)
        print("publish_ready:", ready, reasons)
        if not ready:
            print("BLOCKED: not publish-ready"); return 1
    pub = YouTubePublisher(cfg, dry_run=True)
    res = pub.upload(args.video, args.title, "dry run", [], None)
    print(json.dumps(res, indent=2))
    return 0

def cmd_daily_plan(args):
    cfg, db = load()
    from shorts_studio.queue.runner import DailyRunner
    srcs = source.collect_local(str(ROOT / (args.sources_dir or cfg["content"]["sources_dir"])))
    runner = DailyRunner(cfg, db)
    runner.dry_run(srcs)
    return 0

def cmd_run_daily(args):
    """Run today's planned workload through the same pipeline `run` uses."""
    cfg, db = load()
    from shorts_studio.queue.runner import DailyRunner
    from shorts_studio.queue import pipeline

    srcs = source.collect_local(str(ROOT / (args.sources_dir or cfg["content"]["sources_dir"])))
    runner = DailyRunner(cfg, db)
    if args.dry_run:
        runner.dry_run(srcs)
        return 0

    recovered = runner.recover()
    if recovered:
        print(f"recovered {recovered} interrupted job(s)")

    def execute_fn(spec, job_id):
        res = pipeline.process_source(
            cfg, db, ROOT, spec["source"], spec["profile"],
            allow_unverified=False,
            min_score=cfg.get("candidate", {}).get("min_score", 0.1),
            job_id=job_id, move_source=False,
            beat_cuts=getattr(args, "beat_cuts", False))
        if res["status"] != "OK":
            raise RuntimeError(res.get("reason") or "pipeline did not produce a passing video")
        return res

    plan = runner.plan_daily(srcs)
    if not plan:
        print("Nothing to do: no sources in", args.sources_dir or cfg["content"]["sources_dir"])
        return 0
    results = []
    for spec in plan:
        status, err = runner.run_job(spec, execute_fn)
        results.append((spec, status, err))
        print(f"[{Path(spec['source']).name}] {status} {err or ''}")
    ok = sum(1 for _, s, _ in results if s == "OK")
    print(f"\ndaily: {ok}/{len(plan)} shorts ready for review")
    return 0

def cmd_approve(args):
    cfg, db = load()
    job = db.get_job(args.job_id)
    if not job:
        print("job not found"); return 1
    db.update_job(args.job_id, human_approved=1, status="APPROVED")
    print(f"job {args.job_id} approved")
    return 0


def cmd_publish(args):
    """Publish an approved job to YouTube. Requires BOTH --confirm-live and dry_run:false."""
    cfg, db = load()
    job = db.get_job(args.job_id)
    if not job:
        print("job not found"); return 1
    from shorts_studio.core import publish_gate, rights
    rr = rights.RightsRegistry(db)
    ready, reasons = publish_gate.publish_ready(job, rr, cfg)
    print("publish_ready:", ready, reasons)
    if not ready:
        print("BLOCKED: not publish-ready"); return 1

    dry = bool(cfg["youtube"].get("dry_run", True))
    confirm = getattr(args, "confirm_live", False)
    if dry:
        print("REFUSED: youtube.dry_run is true in config.yaml.")
        print("  To go live: set youtube.dry_run: false, then re-run with --confirm-live.")
        return 1
    if not confirm:
        print("REFUSED: pass --confirm-live to actually upload.")
        print("  (safety gate: two independent confirmations required)")
        return 1

    from shorts_studio.youtube.publishing import YouTubePublisher
    title = args.title or Path(job["source_path"]).stem.replace("_", " ").title()[:100]
    desc = args.description or ""
    tags = cfg["youtube"].get("default_tags", [])
    pub = YouTubePublisher(cfg, dry_run=False)
    res = pub.upload(job["output_path"], title, desc, tags, job.get("thumbnail_path"))
    print(json.dumps({k: v for k, v in res.items() if k != "would_upload"}, indent=2))
    if res.get("status") == "UPLOADED":
        db.update_job(args.job_id, status="PUBLISHED", youtube_id=res.get("video_id"), youtube_url=res.get("url"))
        print("PUBLISHED:", res.get("url"))
    elif res.get("status") == "FAILED":
        db.update_job(args.job_id, status="FAILED", error=res.get("error"))
    return 0 if res.get("status") == "UPLOADED" else 1

def cmd_discover_auto(args):
    cfg, db = load()
    from shorts_studio.media import trend_discovery
    adapters = [("local", {"sources_dir": str(ROOT / cfg["content"]["sources_dir"])}),
                ("youtube_rss", {"channel_id": args.channel_id or "UCpjFY6TMK1KeCPlKXkndE0A"})]
    opps = trend_discovery.discover_and_rank(adapters, cfg, db)
    print(f"discovered {len(opps)} opportunities")
    for o in opps[:10]:
        sc = o["_score"]
        print(f"  {o['opportunity_id']} score={sc['final_score']} rights={o['rights_status']} dup={o['duplicate_status']} {o['topic'][:50]}")
    return 0

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]

def cmd_auth(args):
    cfg, db = load()
    secrets = cfg["youtube"].get("client_secrets")
    token_file = cfg["youtube"].get("token_file")
    if not secrets or not os.path.exists(secrets):
        print("BLOCKED: client_secret.json not found at", secrets)
        return 1
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(secrets, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(token_file).parent.mkdir(parents=True, exist_ok=True)
        import pickle
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)
        # restrict permissions
        os.chmod(token_file, 0o600)
        print("Auth OK. Token saved to", token_file)
        print("Scopes:", creds.scopes)
        return 0
    except Exception as e:
        print("Auth failed:", type(e).__name__, str(e)[:200])
        return 1

def cmd_dashboard(args):
    from shorts_studio.dashboard.server import run_dashboard
    run_dashboard(args.port)
    return 0
    from shorts_studio.media import discovery
    from shorts_studio.core import opportunity, rights, duplicates
    adapter = discovery.get_adapter(args.adapter)
    if adapter is None:
        print("unknown adapter", args.adapter); return 1
    kw = {}
    if args.sources_dir: kw["sources_dir"] = args.sources_dir
    if args.channel_id: kw["channel_id"] = args.channel_id
    if args.query: kw["query"] = args.query
    if args.adapter == "local" and not kw.get("sources_dir"):
        kw["sources_dir"] = str(ROOT / cfg["content"]["sources_dir"])
    raw = adapter.discover(**kw)
    print(f"adapter {args.adapter}: {len(raw)} results")
    rr = rights.RightsRegistry(db)
    existing = db.list_opportunities()
    for r in raw:
        if "error" in r:
            print("  ERROR:", r["error"]); continue
        opp = opportunity.make_opportunity(r.get("topic","unknown"), source_url=r.get("source_url"),
                                          source_adapter=r.get("source_adapter", args.adapter),
                                          rights_status=r.get("rights_status","UNKNOWN"))
        is_dup, reason, kind = duplicates.check_duplicate(opp, existing)
        opp["duplicate_status"] = kind if is_dup else "none"
        rid = rr.register(source_url=opp["source_url"], creator=None, acquisition_method=args.adapter,
                          license_type="UNKNOWN", review_status="UNKNOWN")
        db.add_opportunity(opp)
        print(f"  {opp['opportunity_id']} {opp['topic'][:60]} dup={opp['duplicate_status']} rights={opp['rights_status']}")
    return 0


def cmd_agent(args):
    """Agentic mode: natural language -> find viral clip -> edit -> deliver."""
    cfg, db = load()
    niche_name = getattr(args, "niche", None)
    if niche_name:
        from shorts_studio.editing import niche as niche_mod
        cfg = niche_mod.apply_niche_to_config(cfg, niche_name)
        print(f"niche: {niche_name}")
    from shorts_studio.media import viral_finder
    from shorts_studio.queue import pipeline
    from shorts_studio.media import seo

    query = " ".join(args.query) if isinstance(args.query, list) else args.query
    print()
    print("=" * 60)
    print("  SHORTS STUDIO AGENT")
    print("=" * 60)
    print(f"  Request: {query}")
    print()

    # ---- Step 1: Find viral clips ----
    print("[1/6] Searching for viral clips...")
    all_candidates = []
    seen_urls = set()
    queries = [query, f"{query} short", f"{query} clip", f"{query} funny"]
    for q in queries:
        print(f"  searching: {q}...")
        cands = viral_finder.find_viral_clips(q, limit=5)
        for c in cands:
            if c["url"] not in seen_urls:
                seen_urls.add(c["url"])
                all_candidates.append(c)
    all_candidates.sort(key=lambda x: x["viral_score"], reverse=True)
    candidates = all_candidates[:8]
    if not candidates:
        print("  No clips found. Try a different query.")
        return 1
    print(f"  Found {len(candidates)} unique candidates:")
    for i, c in enumerate(candidates[:5]):
        print(f"    [{i}] score={c['viral_score']:5.1f}  views={c['views']:>8}  dur={c['duration']:5.1f}s  {c['title'][:50]}")
    # pick best
    pick = 0
    if not getattr(args, "auto", False) and len(candidates) > 1:
        try:
            choice = input(f"\n  Pick clip [0-{min(4,len(candidates)-1)}] (default 0): ").strip()
            if choice.isdigit():
                pick = min(int(choice), len(candidates) - 1)
        except EOFError:
            pick = 0
    chosen = candidates[pick]
    print(f"\n  Selected: {chosen['title']}")
    print(f"  URL: {chosen['url']}")
    print(f"  Viral score: {chosen['viral_score']}/100  Views: {chosen['views']:,}")

    # ---- Step 2+3: Download + Edit (try candidates until one works) ----
    edited = False
    for attempt, chosen in enumerate(candidates):
        print(f"\n  Trying candidate [{attempt}]: {chosen['title'][:50]}")
        print(f"  URL: {chosen['url']}")
        print(f"  Viral score: {chosen['viral_score']}/100  Views: {chosen['views']:,}")

        print("\n[2/6] Downloading...")
        out_dir = ROOT / "data" / "content" / "sources" / "agent_downloads"
        out_dir.mkdir(parents=True, exist_ok=True)
        path, err = viral_finder.download_clip(chosen["url"], out_dir)
        if err or not path:
            print(f"  Download failed: {err}")
            continue
        src = str(Path(path).resolve())
        # verify validity
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", src],
                               capture_output=True, text=True, timeout=60)
        if probe.returncode != 0 or not probe.stdout.strip():
            print(f"  Downloaded file invalid, trying next candidate...")
            continue
        print(f"  Downloaded: {Path(src).name} ({probe.stdout.strip()}s)")

        print("\n[3/6] Editing...")
        profile = getattr(args, "profile", None) or cfg["profiles"]["default"]
        cfg["content"]["work_dir"] = "data/work/agent_edit"
        cfg["content"]["output_dir"] = "data/output/agent_edits"
        Path(cfg["content"]["output_dir"]).mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        try:
            r = pipeline.process_source(cfg, db, ROOT, src, profile,
                                       allow_unverified=True, move_source=False,
                                       beat_cuts=getattr(args, "beat_cuts", True),
                                       niche=getattr(args, "niche", None))
        except Exception as e:
            print(f"  Edit error: {e}")
            continue
        if r["status"] != "OK":
            print(f"  Edit failed: {r.get('reason')}")
            continue
        edited = True
        print(f"  Edited in {time.time()-t0:.1f}s -> {Path(r['output']).name}")
        print(f"  Duration: {r['qc']['checks'].get('duration'):.2f}s  QC: PASS")
        break

    if not edited:
        print("\n  All candidates failed. Try a different query.")
        return 1

    # ---- Step 4: SEO metadata ----
    print("\n[4/6] Generating SEO metadata...")
    stem = Path(src).stem
    srt = ROOT / cfg["content"]["work_dir"] / stem / (stem + ".srt")
    transcript = seo.transcript_from_srt(str(srt)) if srt.exists() else ""
    meta = seo.generate_metadata(transcript, cfg=cfg, source_name=stem, profile=profile)
    print(f"  Title: {meta['title']}")
    print(f"  Tags: {', '.join(meta['tags'][:5])}")
    print(f"  Provider: {meta['provider']}")
    # save sidecar
    sidecar = Path(r["output"]).with_suffix(".seo.json")
    sidecar.write_text(json.dumps(meta, indent=2))

    # ---- Step 5: Thumbnail (already done) ----
    print("\n[5/6] Thumbnail generated:", Path(r['thumbnail']).name if r['thumbnail'] else "none")

    # ---- Step 6: Deliver ----
    print("\n[6/6] DELIVERED")
    print("=" * 60)
    print(f"  Video:      {r['output']}")
    print(f"  Thumbnail:  {r['thumbnail']}")
    print(f"  Metadata:   {sidecar}")
    print(f"  Duration:   {r['qc']['checks'].get('duration'):.2f}s")
    print(f"  Music:      {r.get('score', 'n/a')}")
    print("=" * 60)
    print()
    print("  To publish: shorts approve <job_id> then shorts publish <job_id> --confirm-live")
    print("  (after setting youtube.dry_run: false in config.yaml)")
    return 0

def cmd_download_url(args):
    """Download a video from any URL (TikTok, YouTube, etc.) using yt-dlp."""
    import subprocess
    urls = args.urls if isinstance(args.urls, list) else [args.urls]
    out_dir = Path(args.out_dir or (ROOT / "data" / "content" / "sources" / "downloaded"))
    out_dir.mkdir(parents=True, exist_ok=True)
    for url in urls:
        print(f"downloading: {url}")
        cmd = ["yt-dlp", "--js-runtimes", "node", "--remote-components", "ejs:github",
               "--cookies-from-browser", "chrome",
               "-o", str(out_dir / "%(title).80s.%(ext)s"), url]
        if args.format:
            cmd += ["-f", args.format]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                print("  ERROR:", r.stderr[-300:])
            else:
                print("  OK")
        except Exception as e:
            print("  ERROR:", e)
    print("output dir:", out_dir)
    return 0
    from shorts_studio.core import opportunity, rights, duplicates
    adapter = discovery.get_adapter(args.adapter)
    if adapter is None:
        print("unknown adapter", args.adapter); return 1
    kw = {}
    if args.sources_dir: kw["sources_dir"] = args.sources_dir
    if args.channel_id: kw["channel_id"] = args.channel_id
    if args.query: kw["query"] = args.query
    if args.adapter == "local" and not kw.get("sources_dir"):
        kw["sources_dir"] = str(ROOT / cfg["content"]["sources_dir"])
    raw = adapter.discover(**kw)
    print(f"adapter {args.adapter}: {len(raw)} results")
    rr = rights.RightsRegistry(db)
    existing = db.list_opportunities()
    for r in raw:
        if "error" in r:
            print("  ERROR:", r["error"]); continue
        opp = opportunity.make_opportunity(r.get("topic","unknown"), source_url=r.get("source_url"),
                                          source_adapter=r.get("source_adapter", args.adapter),
                                          rights_status=r.get("rights_status","UNKNOWN"))
        is_dup, reason, kind = duplicates.check_duplicate(opp, existing)
        opp["duplicate_status"] = kind if is_dup else "none"
        rid = rr.register(source_url=opp["source_url"], creator=None, acquisition_method=args.adapter,
                          license_type="UNKNOWN", review_status="UNKNOWN")
        db.add_opportunity(opp)
        print(f"  {opp['opportunity_id']} {opp['topic'][:60]} dup={opp['duplicate_status']} rights={opp['rights_status']}")
    return 0


def cmd_gen_video(args):
    cfg, db = load()
    from shorts_studio.media import ai_video
    provider = args.provider
    out_dir = args.out_dir or str(ROOT / "data" / "content" / "sources" / "generated")
    try:
        res = ai_video.generate(provider, args.prompt, cfg=cfg,
                                duration=args.duration, aspect_ratio=args.aspect,
                                image_path=args.image, poll=True,
                                out_dir=out_dir, mode=args.mode)
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e)[:500]); return 1
    print(json.dumps(res, indent=2))
    if res.get("path"):
        print("saved:", res["path"])
    return 0


def cmd_gen_metadata(args):
    cfg, db = load()
    from shorts_studio.media import seo, transcribe
    job = None
    if getattr(args, "job_id", None):
        job = db.get_job(args.job_id)
        if not job:
            print("job not found"); return 1
    transcript = ""
    if getattr(args, "transcript", None):
        transcript = seo.transcript_from_srt(args.transcript)
    elif job and job.get("output_path"):
        # try to find srt in work dir
        stem = Path(job["source_path"]).stem
        srt = ROOT / cfg["content"]["work_dir"] / stem / (stem + ".srt")
        if srt.exists():
            transcript = seo.transcript_from_srt(str(srt))
    elif getattr(args, "source", None):
        srt, ass, segs = transcribe.transcribe(args.source, str(ROOT / cfg["content"]["work_dir"] / Path(args.source).stem), "base")
        transcript = " ".join(s.text.strip() for s in segs)
    if not transcript:
        print("no transcript available; pass --transcript or --source or --job-id")
        return 1
    source_name = None
    if job:
        source_name = Path(job["source_path"]).stem
    elif getattr(args, "source", None):
        source_name = Path(args.source).stem
    meta = seo.generate_metadata(transcript, cfg=cfg, source_name=source_name,
                                 profile=(job["profile"] if job else "chaos"))
    print(json.dumps(meta, indent=2))
    # if job, save metadata to db? store in a sidecar file
    if job:
        sidecar = Path(job["output_path"]).with_suffix(".seo.json")
        sidecar.write_text(json.dumps(meta, indent=2))
        print("saved sidecar:", sidecar)
    return 0


def cmd_analytics_learn(args):
    cfg, db = load()
    from shorts_studio.analytics import learning
    res = learning.run_learning_loop(cfg, db)
    if res.get("error"):
        print("ERROR:", res["error"]); return 1
    import json
    print(json.dumps(res["analysis"], indent=2))
    return 0
    from shorts_studio.media import discovery
    from shorts_studio.core import opportunity, rights, duplicates
    adapter = discovery.get_adapter(args.adapter)
    if adapter is None:
        print("unknown adapter", args.adapter); return 1
    kw = {}
    if args.sources_dir: kw["sources_dir"] = args.sources_dir
    if args.channel_id: kw["channel_id"] = args.channel_id
    if args.query: kw["query"] = args.query
    if args.adapter == "local" and not kw.get("sources_dir"):
        kw["sources_dir"] = str(ROOT / cfg["content"]["sources_dir"])
    raw = adapter.discover(**kw)
    print(f"adapter {args.adapter}: {len(raw)} results")
    rr = rights.RightsRegistry(db)
    existing = db.list_opportunities()
    for r in raw:
        if "error" in r:
            print("  ERROR:", r["error"]); continue
        opp = opportunity.make_opportunity(r.get("topic","unknown"), source_url=r.get("source_url"),
                                          source_adapter=r.get("source_adapter", args.adapter),
                                          rights_status=r.get("rights_status","UNKNOWN"))
        is_dup, reason, kind = duplicates.check_duplicate(opp, existing)
        opp["duplicate_status"] = kind if is_dup else "none"
        rid = rr.register(source_url=opp["source_url"], creator=None, acquisition_method=args.adapter,
                          license_type="UNKNOWN", review_status="UNKNOWN")
        db.add_opportunity(opp)
        print(f"  {opp['opportunity_id']} {opp['topic'][:60]} dup={opp['duplicate_status']} rights={opp['rights_status']}")
    return 0


def cmd_discover(args):
    cfg, db = load()
    from shorts_studio.media import discovery
    from shorts_studio.core import opportunity, rights, duplicates
    adapter = discovery.get_adapter(args.adapter)
    if adapter is None:
        print("unknown adapter", args.adapter); return 1
    kw = {}
    if args.sources_dir: kw["sources_dir"] = args.sources_dir
    if args.channel_id: kw["channel_id"] = args.channel_id
    if args.query: kw["query"] = args.query
    if args.adapter == "local" and not kw.get("sources_dir"):
        kw["sources_dir"] = str(ROOT / cfg["content"]["sources_dir"])
    raw = adapter.discover(**kw)
    print(f"adapter {args.adapter}: {len(raw)} results")
    rr = rights.RightsRegistry(db)
    existing = db.list_opportunities()
    for r in raw:
        if "error" in r:
            print("  ERROR:", r["error"]); continue
        opp = opportunity.make_opportunity(r.get("topic","unknown"), source_url=r.get("source_url"),
                                          source_adapter=r.get("source_adapter", args.adapter),
                                          rights_status=r.get("rights_status","UNKNOWN"))
        is_dup, reason, kind = duplicates.check_duplicate(opp, existing)
        opp["duplicate_status"] = kind if is_dup else "none"
        rid = rr.register(source_url=opp["source_url"], creator=None, acquisition_method=args.adapter,
                          license_type="UNKNOWN", review_status="UNKNOWN")
        db.add_opportunity(opp)
        print(f"  {opp['opportunity_id']} {opp['topic'][:60]} dup={opp['duplicate_status']} rights={opp['rights_status']}")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="shorts-studio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-deps")
    p = sub.add_parser("inspect"); p.add_argument("path")
    p = sub.add_parser("analyze"); p.add_argument("path")
    p = sub.add_parser("plan"); p.add_argument("path"); p.add_argument("--profile", default=None); p.add_argument("--duration", type=int, default=30); p.add_argument("--out", default=None)
    p = sub.add_parser("validate"); p.add_argument("path")
    p = sub.add_parser("render"); p.add_argument("--plan", required=True); p.add_argument("--output", default=None); p.add_argument("--force", action="store_true")
    p = sub.add_parser("qc"); p.add_argument("path")
    p = sub.add_parser("jobs"); p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("run"); p.add_argument("--profile", default=None); p.add_argument("--allow-unverified", action="store_true"); p.add_argument("--min-score", type=float, default=None); p.add_argument("--beat-cuts", action="store_true"); p.add_argument("--narration", default=None); p.add_argument("--niche", default=None)
    sub.add_parser("status").add_argument("--offline", action="store_true")
    sub.add_parser("auth")
    p = sub.add_parser("thumbnail"); p.add_argument("path"); p.add_argument("--title", default=None); p.add_argument("--out", default=None)
    p = sub.add_parser("search-stock"); p.add_argument("--query", required=True); p.add_argument("--count", type=int, default=8); p.add_argument("--download", action="store_true"); p.add_argument("--out-dir", default="data/content/sources/stock"); p.add_argument("--min-duration", type=int, default=3); p.add_argument("--api-key", default=None)
    p = sub.add_parser("download-url"); p.add_argument("urls", nargs="+"); p.add_argument("--out-dir", default=None); p.add_argument("--format", default=None)
    p = sub.add_parser("gen-metadata"); p.add_argument("--job-id", type=int, default=None); p.add_argument("--transcript", default=None); p.add_argument("--source", default=None)
    p = sub.add_parser("gen-video"); p.add_argument("--provider", choices=["kling","higgsfield"], default="kling"); p.add_argument("--prompt", required=True); p.add_argument("--duration", type=int, default=5); p.add_argument("--aspect", default="9:16"); p.add_argument("--image", default=None); p.add_argument("--mode", default="text2video"); p.add_argument("--out-dir", default=None)
    p = sub.add_parser("publish-dryrun"); p.add_argument("--video", required=True); p.add_argument("--title", required=True); p.add_argument("--job-id", type=int, default=None)
    p = sub.add_parser("approve"); p.add_argument("job_id", type=int)
    p = sub.add_parser("publish"); p.add_argument("job_id", type=int); p.add_argument("--confirm-live", action="store_true"); p.add_argument("--title", default=None); p.add_argument("--description", default=None)
    p = sub.add_parser("daily-plan"); p.add_argument("--sources-dir", default=None)
    p = sub.add_parser("run-daily"); p.add_argument("--sources-dir", default=None); p.add_argument("--dry-run", action="store_true"); p.add_argument("--beat-cuts", action="store_true")
    p = sub.add_parser("agent"); p.add_argument("query", nargs="+"); p.add_argument("--auto", action="store_true"); p.add_argument("--profile", default=None); p.add_argument("--limit", type=int, default=8); p.add_argument("--niche", default=None)
    p = sub.add_parser("dashboard"); p.add_argument("--port", type=int, default=8765)
    p = sub.add_parser("analytics-learn")
    p = sub.add_parser("discover"); p.add_argument("--adapter", default="local"); p.add_argument("--sources-dir", default=None); p.add_argument("--channel-id", default=None); p.add_argument("--query", default=None)
    p = sub.add_parser("discover-auto"); p.add_argument("--channel-id", default=None)
    args = ap.parse_args()
    dispatch = {
        "check-deps": cmd_check_deps, "inspect": cmd_inspect, "analyze": cmd_analyze,
        "plan": cmd_plan, "validate": cmd_validate, "render": cmd_render, "qc": cmd_qc,
        "jobs": cmd_jobs, "run": cmd_run, "status": cmd_status, "thumbnail": cmd_thumbnail,
    "auth": cmd_auth,
    "download-url": cmd_download_url, "discover": cmd_discover, "search-stock": cmd_search_stock, "gen-video": cmd_gen_video,
    "gen-metadata": cmd_gen_metadata, "publish-dryrun": cmd_publish_dryrun,
    "dashboard": cmd_dashboard, "analytics-learn": cmd_analytics_learn, "discover": cmd_discover, "discover-auto": cmd_discover_auto, "agent": cmd_agent, "daily-plan": cmd_daily_plan, "run-daily": cmd_run_daily,
    "approve": cmd_approve, "publish": cmd_publish,
    }
    return dispatch[args.cmd](args)

if __name__ == "__main__":
    sys.exit(main())
