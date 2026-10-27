"""Daily job runner with recovery, retry, dry-run, discovery."""
import os, time, json
from pathlib import Path
from shorts_studio.core import db as dbmod

class DailyRunner:
    def __init__(self, cfg, db):
        self.cfg = cfg
        self.db = db
        self.max_attempts = cfg.get("runner", {}).get("max_attempts", 2)
        self.daily_shorts = cfg["channel"].get("uploads_per_day", 2)
        self.daily_longform = 1

    def discover(self, cfg, db):
        from shorts_studio.media import trend_discovery
        adapters = [("local", {"sources_dir": cfg["content"]["sources_dir"]}),
                    ("youtube_rss", {"channel_id": "UCpjFY6TMK1KeCPlKXkndE0A"})]
        try:
            opps = trend_discovery.discover_and_rank(adapters, cfg, db)
            print(f"[discover] {len(opps)} opportunities found")
            for o in opps[:5]:
                print(f"  {o['opportunity_id']} score={o['_score']['final_score']} {o['topic'][:50]}")
            return opps
        except Exception as e:
            print(f"[discover] failed: {e}")
            return []

    def plan_daily(self, sources):
        plan = []
        for i, src in enumerate(sources[:self.daily_shorts]):
            plan.append({"type": "short", "source": src, "profile": cfg_profile(self.cfg, i), "index": i})
        return plan

    def discover_and_plan(self, sources):
        opps = self.discover(self.cfg, self.db)
        plan = self.plan_daily(sources)
        return opps, plan

    def dry_run(self, sources):
        opps = self.discover(self.cfg, self.db)
        plan = self.plan_daily(sources)
        print("=== DRY RUN: planned daily workload ===")
        print(f"Discovery: {len(opps)} opportunities found")
        for j in plan:
            print(f"  [{j['type']}] {Path(j['source']).name} profile={j['profile']}")
        print(f"Total: {len(plan)} jobs (shorts={sum(1 for j in plan if j['type']=='short')})")
        print("No processing performed.")
        return plan, opps

    def run_job(self, job_spec, execute_fn):
        # run discovery first (best-effort, does not block production)
        try:
            self.discover(self.cfg, self.db)
        except Exception as e:
            print(f"[runner] discovery skipped: {e}")
        # check duplicate
        existing = self.db.list_jobs(status=None)
        for j in existing:
            if j["source_path"] == job_spec["source"] and j["status"] in ("READY_FOR_REVIEW","PUBLISHED","READY_TO_PUBLISH"):
                return "SKIPPED_DUPLICATE", "already processed"
        job_id = self.db.add_job(job_spec["source"], profile=job_spec["profile"], status="DISCOVERED")
        attempt = 0
        last_err = None
        while attempt < self.max_attempts:
            attempt += 1
            self.db.update_job(job_id, status="RENDERING", attempts=attempt)
            try:
                execute_fn(job_spec, job_id)
                self.db.update_job(job_id, status="READY_FOR_REVIEW")
                return "OK", None
            except Exception as e:
                last_err = str(e)
                self.db.update_job(job_id, status="FAILED", error=last_err)
                if attempt < self.max_attempts:
                    time.sleep(1)
        return "FAILED", last_err

    def recover(self):
        stuck = self.db.list_jobs(status="RENDERING")
        for j in stuck:
            self.db.update_job(j["id"], status="FAILED", error="interrupted (recovered)")
        return len(stuck)

def cfg_profile(cfg, i):
    profs = cfg.get("profiles", {}).get("available", ["chaos"])
    default = cfg.get("profiles", {}).get("default", "chaos")
    if i < len(profs):
        return profs[i % len(profs)]
    return default