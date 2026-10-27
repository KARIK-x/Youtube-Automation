"""Free stock video search: Pexels (and Pixabay fallback).

Pexels API is free (200 req/hour) — get a key instantly at https://www.pexels.com/api/.
Set via env PEXELS_API_KEY or config ai_video.pexels.api_key.
"""
import os
from pathlib import Path

try:
    import requests
except Exception:
    requests = None


def pexels_key(cfg=None):
    key = os.environ.get("PEXELS_API_KEY")
    if not key and cfg:
        cur = cfg
        for k in ("ai_video", "pexels", "api_key"):
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                cur = None
                break
        key = cur
    if not key:
        raise RuntimeError("Pexels API key missing. Get a free key at https://www.pexels.com/api/ "
                           "then set PEXELS_API_KEY or ai_video.pexels.api_key in config.yaml")
    return key


def pexels_search(query, *, cfg=None, per_page=8, orientation="portrait", min_duration=3):
    key = pexels_key(cfg)
    if requests is None:
        raise RuntimeError("requests not installed")
    r = requests.get("https://api.pexels.com/videos/search",
                     headers={"Authorization": key},
                     params={"query": query, "per_page": per_page,
                             "orientation": orientation, "size": "medium"},
                     timeout=30)
    r.raise_for_status()
    data = r.json()
    out = []
    for v in data.get("videos", []):
        # pick best mp4 file (prefer hd, portrait-friendly)
        files = v.get("video_files", [])
        # filter to mp4
        mp4s = [f for f in files if f.get("file_type") == "video/mp4"]
        if not mp4s:
            mp4s = files
        # prefer highest quality under 1080
        best = None
        for f in mp4s:
            w = f.get("width", 0)
            if best is None or (w <= 1080 and w > best.get("width", 0)):
                best = f
        if best is None and mp4s:
            best = mp4s[0]
        out.append({
            "id": v.get("id"),
            "topic": v.get("url", "").split("/")[-1] or f"pexels_{v.get('id')}",
            "url": v.get("url"),
            "duration": v.get("duration"),
            "width": v.get("width"),
            "height": v.get("height"),
            "download_url": best.get("link") if best else None,
            "source_adapter": "pexels",
            "rights_status": "LICENSED",  # Pexels license allows free use
            "license": "Pexels License (free, attribution appreciated)",
            "attribution": v.get("user", {}).get("name"),
        })
    # filter by min duration
    out = [o for o in out if (o.get("duration") or 0) >= min_duration]
    return out


def pexels_download(item, out_dir):
    if not item.get("download_url"):
        raise RuntimeError("no download url")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"pexels_{item['id']}.mp4"
    r = requests.get(item["download_url"], stream=True, timeout=120)
    r.raise_for_status()
    with open(dst, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return str(dst)