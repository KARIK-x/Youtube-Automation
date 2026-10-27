"""SQLite job state + metadata store."""
import sqlite3, json, time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT,
    profile TEXT,
    status TEXT DEFAULT 'DISCOVERED',
    edit_plan TEXT,
    output_path TEXT,
    thumbnail_path TEXT,
    duration REAL,
    width INTEGER,
    height INTEGER,
    youtube_id TEXT,
    youtube_url TEXT,
    error TEXT,
    attempts INTEGER DEFAULT 0,
    created_at REAL DEFAULT (strftime('%s','now')),
    updated_at REAL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT UNIQUE,
    source_url TEXT,
    creator TEXT,
    rights_status TEXT DEFAULT 'unknown',
    description TEXT,
    analysis_status TEXT DEFAULT 'pending',
    first_seen REAL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL, finished_at REAL, jobs_produced INTEGER, errors TEXT
);
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id TEXT UNIQUE,
    topic TEXT,
    niche TEXT,
    source_url TEXT,
    discovery_ts REAL,
    publication_ts TEXT,
    engagement_metrics TEXT,
    metrics_ts REAL,
    trend_growth_evidence TEXT,
    competition TEXT,
    audience_relevance REAL,
    content_angle TEXT,
    research_notes TEXT,
    source_adapter TEXT,
    confidence REAL,
    rights_status TEXT,
    duplicate_status TEXT,
    recommended_format TEXT,
    created_at REAL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS published (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    youtube_id TEXT,
    youtube_url TEXT,
    title TEXT,
    published_at REAL,
    dry_run INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT,
    views INTEGER,
    watch_time_minutes REAL,
    avg_view_duration REAL,
    avg_percentage_viewed REAL,
    impressions INTEGER,
    ctr REAL,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    subscribers_gained INTEGER,
    collected_at REAL DEFAULT (strftime('%s','now'))
);
"""

VALID_STATUSES = {"DISCOVERED","ANALYZED","CANDIDATE_SELECTED","EDIT_PLAN_CREATED",
    "PLAN_VALIDATED","RENDERING","QUALITY_CHECK","READY_FOR_REVIEW","APPROVED",
    "READY_TO_PUBLISH","UPLOADING","PUBLISHED","FAILED","BLOCKED"}

class DB:
    def __init__(self, path, check_same_thread=True):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        # migrations
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(jobs)").fetchall()]
        if "human_approved" not in cols:
            self.conn.execute("ALTER TABLE jobs ADD COLUMN human_approved INTEGER DEFAULT 0")
        self.conn.commit()

    def add_job(self, source_path, profile="chaos", status="DISCOVERED"):
        cur = self.conn.execute(
            "INSERT INTO jobs(source_path,profile,status) VALUES (?,?,?)",
            (source_path, profile, status))
        self.conn.commit()
        return cur.lastrowid

    def update_job(self, job_id, **kw):
        if "status" in kw and kw["status"] not in VALID_STATUSES:
            raise ValueError(f"invalid status {kw['status']}")
        sets, vals = [], []
        for k,v in kw.items():
            if k in ("edit_plan",) and not isinstance(v, str) and v is not None:
                v = json.dumps(v)
            sets.append(f"{k}=?"); vals.append(v)
        sets.append("updated_at=?"); vals.append(time.time())
        vals.append(job_id)
        self.conn.execute(f"UPDATE jobs SET {','.join(sets)} WHERE id=?", vals)
        self.conn.commit()

    def get_job(self, job_id):
        r = self.conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(r) if r else None

    def list_jobs(self, status=None, limit=100):
        if status:
            rows = self.conn.execute("SELECT * FROM jobs WHERE status=? ORDER BY id DESC LIMIT ?",
                                    (status, limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def count_by_status(self):
        rows = self.conn.execute("SELECT status,COUNT(*) c FROM jobs GROUP BY status").fetchall()
        return {r["status"]: r["c"] for r in rows}

    def add_source(self, source_path, **kw):
        try:
            cur = self.conn.execute(
                "INSERT INTO sources(source_path,source_url,creator,rights_status,description) VALUES (?,?,?,?,?)",
                (source_path, kw.get("source_url"), kw.get("creator"), kw.get("rights_status","unknown"), kw.get("description")))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def log_run(self, started, finished, produced, errors):
        self.conn.execute("INSERT INTO runs(started_at,finished_at,jobs_produced,errors) VALUES (?,?,?,?)",
                          (started, finished, produced, json.dumps(errors)))
        self.conn.commit()

    def add_opportunity(self, opp):
        import json
        cur = self.conn.execute("""
            INSERT INTO opportunities(opportunity_id,topic,niche,source_url,discovery_ts,publication_ts,
            engagement_metrics,metrics_ts,trend_growth_evidence,competition,audience_relevance,
            content_angle,research_notes,source_adapter,confidence,rights_status,duplicate_status,recommended_format)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (opp["opportunity_id"], opp["topic"], opp["niche"], opp["source_url"], opp["discovery_ts"],
             opp["publication_ts"], json.dumps(opp["engagement_metrics"]) if opp["engagement_metrics"] else None,
             opp["metrics_ts"], opp["trend_growth_evidence"], opp["competition"], opp["audience_relevance"],
             opp["content_angle"], opp["research_notes"], opp["source_adapter"], opp["confidence"],
             opp["rights_status"], opp["duplicate_status"], opp["recommended_format"]))
        self.conn.commit()
        return cur.lastrowid

    def list_opportunities(self, limit=50):
        rows = self.conn.execute("SELECT * FROM opportunities ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def add_published(self, job_id, youtube_id, youtube_url, title, dry_run=True):
        cur = self.conn.execute("INSERT INTO published(job_id,youtube_id,youtube_url,title,published_at,dry_run) VALUES (?,?,?,?,?,?)",
                                (job_id, youtube_id, youtube_url, title, __import__("time").time(), 1 if dry_run else 0))
        self.conn.commit()
        return cur.lastrowid

    def add_analytics(self, video_id, metrics):
        cur = self.conn.execute("""INSERT INTO analytics(video_id,views,watch_time_minutes,avg_view_duration,
            avg_percentage_viewed,impressions,ctr,likes,comments,shares,subscribers_gained) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (video_id, metrics.get("views"), metrics.get("watch_time_minutes"), metrics.get("avg_view_duration"),
             metrics.get("avg_percentage_viewed"), metrics.get("impressions"), metrics.get("ctr"),
             metrics.get("likes"), metrics.get("comments"), metrics.get("shares"), metrics.get("subscribers_gained")))
        self.conn.commit()
        return cur.lastrowid

    def close(self):
        self.conn.close()
