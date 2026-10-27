"""Analytics learning loop: retrieve YouTube metrics, associate with edit
metadata, generate evidence-based recommendations.

Read-only. Never fabricates data. Missing values stay missing.
"""
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
import sys
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.core import config, db as dbmod


def _load_edit_metadata(job, cfg):
    """Associate a job with its editing metadata (from sidecar or job record)."""
    meta = {
        "job_id": job.get("id"),
        "source": job.get("source_path"),
        "profile": job.get("profile"),
        "duration": job.get("duration"),
        "output": job.get("output_path"),
        "thumbnail": job.get("thumbnail_path"),
        "youtube_id": job.get("youtube_id") or job.get("youtube_video_id"),
        "human_approved": job.get("human_approved"),
        "status": job.get("status"),
    }
    # try sidecar seo.json
    out = job.get("output_path")
    if out:
        sidecar = Path(out).with_suffix(".seo.json")
        if sidecar.exists():
            try:
                s = json.loads(sidecar.read_text())
                meta["seo_title"] = s.get("title")
                meta["seo_tags"] = s.get("tags", [])
                meta["seo_provider"] = s.get("provider")
            except Exception:
                pass
    # try work dir metadata.json (long-form)
    if out:
        stem = Path(job.get("source_path", "")).stem
        work_meta = ROOT / cfg["content"]["work_dir"] / stem / "metadata.json"
        if work_meta.exists():
            try:
                m = json.loads(work_meta.read_text())
                meta["sections"] = m.get("sections", [])
                meta["chapters"] = m.get("chapters_file")
            except Exception:
                pass
    return meta


def retrieve_metrics(cfg, db, job_ids=None):
    """Retrieve YouTube analytics for published jobs. Returns list of (meta, metrics)."""
    from shorts_studio.youtube.analytics import AnalyticsAdapter
    ad = AnalyticsAdapter(cfg)
    if not ad.is_configured():
        return [], "analytics not configured (no OAuth token)"
    jobs = db.list_jobs(limit=200)
    if job_ids:
        jobs = [j for j in jobs if j["id"] in job_ids]
    published = [j for j in jobs if (j.get("youtube_id") or j.get("youtube_video_id"))]
    results = []
    for j in published:
        vid = j.get("youtube_id") or j.get("youtube_video_id")
        m = ad.fetch_video_metrics(vid)
        meta = _load_edit_metadata(j, cfg)
        results.append({"metadata": meta, "metrics": m})
    return results, None


def analyze_performance(results):
    """Analyze performance across videos. Returns summary + recommendations."""
    if not results:
        return {"summary": "No published videos with analytics.", "recommendations": [{
            "type": "no_data",
            "observation": "No published videos with YouTube analytics found.",
            "sample_size": 0,
            "limitation": "Publishing is in dry-run mode. No videos have been uploaded.",
            "suggestion": "Enable publishing (youtube.dry_run: false) and upload videos to collect analytics.",
        }], "sample_size": 0}
    # group by profile
    by_profile = {}
    for r in results:
        p = r["metadata"].get("profile", "unknown")
        by_profile.setdefault(p, []).append(r)
    summary = {}
    for p, rs in by_profile.items():
        views = [r["metrics"].get("views", 0) for r in rs if r["metrics"].get("status") == "OK"]
        dur = [r["metrics"].get("avg_view_duration") for r in rs if r["metrics"].get("avg_view_duration")]
        summary[p] = {
            "count": len(rs),
            "total_views": sum(views),
            "avg_views": round(sum(views)/len(views), 1) if views else None,
            "avg_view_duration": round(sum(dur)/len(dur), 1) if dur else None,
            "metrics_available": len(views),
        }
    # recommendations (evidence-based, with caveats)
    recs = []
    if len(by_profile) >= 2:
        # compare profiles by avg views
        ranked = sorted(by_profile.keys(), key=lambda p: summary[p].get("avg_views") or 0, reverse=True)
        if ranked and summary[ranked[0]].get("avg_views") and summary[ranked[-1]].get("avg_views"):
            best = ranked[0]
            worst = ranked[-1]
            if summary[best]["avg_views"] > summary[worst]["avg_views"] * 1.2:
                recs.append({
                    "type": "profile_performance",
                    "observation": f"Profile '{best}' has higher avg views ({summary[best]['avg_views']}) "
                                   f"than '{worst}' ({summary[worst]['avg_views']}).",
                    "sample_size": summary[best]["count"] + summary[worst]["count"],
                    "limitation": "Small sample; confounding factors (topic, duration, timing) not controlled.",
                    "suggestion": f"Consider testing '{best}' profile more, but verify with larger sample.",
                })
    # duration analysis
    durations = [(r["metadata"].get("duration"), r["metrics"].get("views", 0))
                  for r in results if r["metrics"].get("status") == "OK"]
    if len(durations) >= 5:
        short = [v for d, v in durations if d and d < 20]
        long = [v for d, v in durations if d and d >= 20]
        if short and long:
            avg_short = sum(short)/len(short)
            avg_long = sum(long)/len(long)
            if avg_short > avg_long * 1.3:
                recs.append({
                    "type": "duration",
                    "observation": f"Shorter videos (<20s) avg {avg_short:.0f} views vs longer {avg_long:.0f} views.",
                    "sample_size": len(durations),
                    "limitation": "Topic confounding; not a controlled experiment.",
                    "suggestion": "Consider testing shorter durations, but verify with larger sample.",
                })
    if not recs:
        recs.append({
            "type": "insufficient_data",
            "observation": f"Only {len(results)} published videos with analytics.",
            "sample_size": len(results),
            "limitation": "Need at least 5-10 published videos for meaningful patterns.",
            "suggestion": "Publish more videos and re-run analysis.",
        })
    return {
        "summary": summary,
        "recommendations": recs,
        "sample_size": len(results),
        "measurement_period": "all available",
        "note": "Recommendations are evidence-based suggestions, not causal claims. "
                "Confounding factors (topic, timing, thumbnail) are not fully controlled.",
    }


def run_learning_loop(cfg=None, db=None):
    """Full analytics learning loop. Returns analysis dict."""
    if cfg is None:
        cfg = config.load_config(str(ROOT / "config.yaml"))
    if db is None:
        db = dbmod.DB(cfg["db"]["path"])
    results, err = retrieve_metrics(cfg, db)
    if err:
        return {"error": err, "results": [], "analysis": None}
    analysis = analyze_performance(results)
    return {"error": None, "results": results, "analysis": analysis}