"""Lightweight dashboard server for Shorts Studio.

Uses only the Python standard library (no Flask/FastAPI/Streamlit) so it
runs on the Mac without new dependencies. Long-running work (rendering,
agent runs) is executed in background threads; the HTTP request returns
immediately with a job handle that the UI polls.

Run:  shorts dashboard [--port 8765]
"""
import os, sys, json, time, threading, subprocess, mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

from shorts_studio.core import config, db as dbmod
from shorts_studio.cli import main as cli

CFG = config.load_config(str(ROOT / "config.yaml"))
DB = dbmod.DB(CFG["db"]["path"], check_same_thread=False)

# background task registry
TASKS = {}  # id -> {status, started, finished, log, result, error}
TASK_LOCK = threading.Lock()
TASK_COUNTER = [0]


def _run_task(fn, *args, **kwargs):
    with TASK_LOCK:
        TASK_COUNTER[0] += 1
        tid = TASK_COUNTER[0]
        TASKS[tid] = {"id": tid, "status": "running", "started": time.time(),
                      "finished": None, "log": [], "result": None, "error": None}
    def worker():
        t = TASKS[tid]
        # capture stdout
        import io, contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                res = fn(*args, **kwargs)
            t["result"] = res
            t["status"] = "done"
        except Exception as e:
            t["error"] = f"{type(e).__name__}: {e}"
            t["status"] = "failed"
        finally:
            t["log"] = buf.getvalue().splitlines()
            t["finished"] = time.time()
    threading.Thread(target=worker, daemon=True).start()
    return tid


def _status_payload():
    yt = CFG.get("youtube", {})
    tok_state = None
    try:
        tok_state = cli._token_state(yt.get("token_file"))
    except Exception:
        pass
    jobs = DB.count_by_status()
    # recent outputs
    out_dir = ROOT / CFG["content"]["output_dir"]
    outputs = []
    if out_dir.exists():
        for p in sorted(out_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            outputs.append({"name": p.name, "path": str(p), "size_mb": round(p.stat().st_size/1e6, 1),
                           "mtime": p.stat().st_mtime})
    # audio assets
    try:
        music_total, music_licensed, music_test, sfx_total, sfx_licensed, unreg, lib = cli._audio_asset_state(CFG)
    except Exception:
        music_total = music_licensed = sfx_total = sfx_licensed = 0; unreg = 0
    return {
        "channel": CFG["channel"]["name"],
        "resolution": f"{CFG['video']['width']}x{CFG['video']['height']}",
        "oauth": {
            "present": tok_state.get("present", False) if tok_state else False,
            "scopes": tok_state.get("scopes") if tok_state else None,
            "mode": tok_state.get("mode") if tok_state else None,
        },
        "dry_run": bool(yt.get("dry_run", True)),
        "jobs": jobs,
        "outputs": outputs,
        "audio": {"music_licensed": music_licensed, "music_total": music_total,
                  "sfx_licensed": sfx_licensed, "sfx_total": sfx_total},
        "disk_free_gb": round(__import__("shutil").disk_usage(str(ROOT)).free / 1e9, 1),
    }


def _run_shorts(profile=None, allow_unverified=False, beat_cuts=False):
    import argparse
    ns = argparse.Namespace(profile=profile, allow_unverified=allow_unverified,
                            min_score=None, beat_cuts=beat_cuts)
    cli.cmd_run(ns)
    return {"done": True}


def _run_agent(query, profile=None, auto=True, limit=5, beat_cuts=True):
    import argparse
    ns = argparse.Namespace(query=query.split() if isinstance(query, str) else query,
                            auto=auto, profile=profile, limit=limit, beat_cuts=beat_cuts)
    cli.cmd_agent(ns)
    return {"done": True}


def _run_daily(dry_run=False, beat_cuts=False):
    import argparse
    ns = argparse.Namespace(sources_dir=None, dry_run=dry_run, beat_cuts=beat_cuts)
    cli.cmd_run_daily(ns)
    return {"done": True}


def _discover(adapter="reddit", **kw):
    import argparse
    ns = argparse.Namespace(adapter=adapter, sources_dir=kw.get("sources_dir"),
                            channel_id=kw.get("channel_id"), query=kw.get("query"))
    cli.cmd_discover(ns)
    return {"done": True}


def _gen_metadata(source=None, job_id=None):
    import argparse
    ns = argparse.Namespace(source=source, job_id=job_id, transcript=None)
    cli.cmd_gen_metadata(ns)
    return {"done": True}


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        data = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path):
        p = Path(path)
        if not p.exists() or not p.is_file():
            self.send_error(404); return
        data = p.read_bytes()
        ct = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, path):
        self._file(path)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        qs = parse_qs(u.query)
        if path == "/" or path == "/index.html":
            self._html(ROOT / "src" / "shorts_studio" / "dashboard" / "static" / "index.html")
            return
        if path == "/api/status":
            self._json(_status_payload())
            return
        if path == "/api/jobs":
            limit = int(qs.get("limit", ["50"])[0])
            jobs = DB.list_jobs(limit=limit)
            self._json({"jobs": jobs})
            return
        if path == "/api/tasks":
            with TASK_LOCK:
                self._json({"tasks": list(TASKS.values())})
            return
        if path == "/api/task":
            tid = int(qs.get("id", ["0"])[0])
            with TASK_LOCK:
                t = TASKS.get(tid)
            if not t:
                self._json({"error": "not found"}, 404); return
            self._json(t)
            return
        if path == "/api/outputs":
            out_dir = ROOT / CFG["content"]["output_dir"]
            files = []
            if out_dir.exists():
                for p in sorted(out_dir.rglob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
                    files.append({"name": p.name, "path": str(p), "size_mb": round(p.stat().st_size/1e6,1),
                                  "mtime": p.stat().st_mtime})
            self._json({"outputs": files})
            return
        if path == "/api/qc":
            p = qs.get("path", [""])[0]
            if not p:
                self._json({"error": "path required"}, 400); return
            from shorts_studio.editing import qc
            try:
                # long-form if duration > 120
                import subprocess
                r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                                    "-of","default=noprint_wrappers=1:nokey=1", p],
                                   capture_output=True, text=True, timeout=30)
                dur = float(r.stdout.strip()) if r.stdout.strip() else 0
                if dur > 120:
                    res = qc.qc_longform(p, CFG)
                else:
                    res = qc.qc(p, CFG)
                self._json(res)
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if path == "/api/analytics":
            try:
                from shorts_studio.youtube.analytics import AnalyticsAdapter
                ad = AnalyticsAdapter(CFG)
                # fetch for recent jobs with output
                jobs = DB.list_jobs(limit=20)
                out = []
                for j in jobs:
                    vid = j.get("youtube_id") or j.get("youtube_video_id")
                    if vid:
                        m = ad.fetch_video_metrics(vid)
                        out.append({"job_id": j["id"], "video_id": vid, "metrics": m})
                self._json({"analytics": out, "note": "only jobs with youtube_id are queried"})
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if path.startswith("/files/"):
            rel = path[len("/files/"):]
            self._file(ROOT / rel)
            return
        if path.startswith("/thumb/"):
            rel = path[len("/thumb/"):]
            self._file(ROOT / rel)
            return
        self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        path = u.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        if path == "/api/run":
            profile = data.get("profile")
            allow = bool(data.get("allow_unverified", False))
            beat_cuts = bool(data.get("beat_cuts", False))
            tid = _run_task(_run_shorts, profile, allow, beat_cuts)
            self._json({"task_id": tid})
            return
        if path == "/api/agent":
            query = data.get("query", "")
            if not query:
                self._json({"error": "query required"}, 400); return
            tid = _run_task(_run_agent, query, data.get("profile"), bool(data.get("auto", True)),
                            int(data.get("limit", 5)), bool(data.get("beat_cuts", True)))
            self._json({"task_id": tid})
            return
        if path == "/api/daily":
            tid = _run_task(_run_daily, bool(data.get("dry_run", False)), bool(data.get("beat_cuts", False)))
            self._json({"task_id": tid})
            return
        if path == "/api/discover":
            adapter = data.get("adapter", "reddit")
            tid = _run_task(_discover, adapter, sources_dir=data.get("sources_dir"),
                            channel_id=data.get("channel_id"), query=data.get("query"))
            self._json({"task_id": tid})
            return
        if path == "/api/approve":
            jid = data.get("job_id")
            if not jid:
                self._json({"error": "job_id required"}, 400); return
            DB.update_job(jid, human_approved=1, status="APPROVED")
            self._json({"ok": True, "job_id": jid})
            return
        if path == "/api/gen-metadata":
            source = data.get("source")
            job_id = data.get("job_id")
            tid = _run_task(_gen_metadata, source, job_id)
            self._json({"task_id": tid})
            return
        self.send_error(404)

    def log_message(self, *args):
        pass  # quiet


def run_dashboard(port=8765):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Dashboard: http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    run_dashboard(args.port)