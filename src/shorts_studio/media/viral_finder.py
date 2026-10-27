"""Viral clip finder: search YouTube/TikTok, score by viral potential, download best.

Uses yt-dlp (free, no API key) for search + metadata. Scoring combines
views, likes, engagement ratio, recency, and duration fit for Shorts.
"""
import json, subprocess, re, time
from pathlib import Path

def search_youtube(query, limit=10):
    """Search YouTube via yt-dlp. Returns list of metadata dicts."""
    cmd = ["yt-dlp", f"ytsearch{limit}:{query}", "--dump-json", "--flat-playlist",
           "--no-warnings", "--skip-download"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:
        return []
    out = []
    for line in r.stdout.strip().splitlines():
        try:
            d = json.loads(line)
            out.append(d)
        except Exception:
            continue
    return out


def viral_score(item, target_duration=30):
    """Score a video for viral Shorts potential (0-100)."""
    views = item.get("view_count") or 0
    likes = item.get("like_count") or 0
    dur = item.get("duration") or 0
    # engagement ratio
    eng = (likes / views) if views > 0 else 0
    # duration fit: prefer 15-60s
    if dur <= 0:
        dur_fit = 0.3
    elif 15 <= dur <= 60:
        dur_fit = 1.0
    elif dur < 15:
        dur_fit = dur / 15.0
    else:
        dur_fit = max(0.2, 1.0 - (dur - 60) / 120.0)
    # view score (log scale)
    import math
    view_score = min(1.0, math.log10(max(views, 1)) / 7.0)  # 10M views = 1.0
    # recency (if upload_date available)
    recency = 0.5
    ud = item.get("upload_date")
    if ud:
        try:
            from datetime import datetime, timedelta
            d = datetime.strptime(ud, "%Y%m%d")
            age_days = (datetime.now() - d).days
            if age_days <= 7:
                recency = 1.0
            elif age_days <= 30:
                recency = 0.8
            elif age_days <= 90:
                recency = 0.6
            else:
                recency = 0.3
        except Exception:
            pass
    score = (view_score * 40 + eng * 1000 * 20 + dur_fit * 20 + recency * 20)
    return min(100, round(score, 1))


def find_viral_clips(query, limit=10, min_duration=10, max_duration=600):
    """Search + score + return sorted list of viral clip candidates."""
    items = search_youtube(query, limit=limit)
    results = []
    for it in items:
        dur = it.get("duration") or 0
        if dur > 0 and (dur < min_duration or dur > max_duration):
            continue
        sc = viral_score(it)
        # strong preference for short clips (Shorts-friendly); penalize long compilations
        if dur > 120:
            sc = sc * 0.4
        results.append({
            "title": it.get("title", ""),
            "url": it.get("webpage_url") or it.get("url", ""),
            "duration": dur,
            "views": it.get("view_count", 0),
            "likes": it.get("like_count", 0),
            "upload_date": it.get("upload_date"),
            "channel": it.get("channel") or it.get("uploader", ""),
            "viral_score": sc,
        })
    results.sort(key=lambda x: x["viral_score"], reverse=True)
    return results


def download_clip(url, out_dir):
    """Download a clip via yt-dlp. Returns (path, error)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["yt-dlp", "--js-runtimes", "node", "--remote-components", "ejs:github",
           "--cookies-from-browser", "chrome", "--print", "after_move:filepath",
           "-o", str(out_dir / "%(title).60s.%(ext)s"), url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        return None, str(e)
    if r.returncode != 0:
        return None, r.stderr[-300:]
    # yt-dlp prints the final filepath
    downloaded = None
    for line in reversed(r.stdout.strip().splitlines()):
        line = line.strip()
        if line and Path(line).exists():
            downloaded = line
            break
    if not downloaded:
        files = sorted(out_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files:
            if f.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov"):
                downloaded = str(f)
                break
    if not downloaded:
        return None, "no video file found"
    p = Path(downloaded)
    if p.suffix.lower() != ".mp4":
        mp4 = p.with_suffix(".mp4")
        subprocess.run(["ffmpeg", "-y", "-i", str(p), "-c:v", "libx264",
                       "-preset", "fast", "-crf", "20", "-c:a", "aac",
                       "-b:a", "128k", str(mp4)], capture_output=True, timeout=600)
        if mp4.exists():
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "default=noprint_wrappers=1:nokey=1", str(mp4)],
                                   capture_output=True, text=True, timeout=60)
            if probe.returncode == 0 and probe.stdout.strip():
                return str(mp4), None
    return downloaded, None

