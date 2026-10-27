"""Source ingestion: local files or URL download via yt-dlp."""
import os, shutil, subprocess, glob
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED = {".mp4",".mkv",".mov",".webm",".avi",".flv"}

def collect_urls(sources_dir, work_dir):
    uf = Path(sources_dir) / "urls.txt"
    if not uf.exists():
        return []
    urls = [l.strip() for l in uf.read_text().splitlines() if l.strip() and not l.startswith("#")]
    out = []
    for u in urls:
        try:
            out.append(download_url(u, os.path.join(work_dir, "downloads")))
        except Exception as e:
            print("download failed", u, e)
    return out
def collect_local(sources_dir):
    out = []
    for p in Path(sources_dir).rglob("*"):
        if p.suffix.lower() in SUPPORTED:
            out.append(str(p))
    return sorted(out)

def download_url(url, work_dir):
    """Download a video URL via yt-dlp. Returns path to file."""
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = os.path.join(work_dir, "%(id)s.%(ext)s")
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
           "-o", outtmpl, "--no-playlist", url]
    subprocess.run(cmd, check=True, capture_output=True)
    # find newest file
    files = sorted(Path(work_dir).glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        if f.suffix.lower() in SUPPORTED:
            return str(f)
    raise RuntimeError("yt-dlp produced no video file")

def ingest(source, work_dir):
    """source: file path, directory, or URL. Returns list of video paths."""
    if isinstance(source, (list, tuple)):
        paths = []
        for s in source:
            paths += ingest(s, work_dir)
        return paths
    s = str(source).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return [download_url(s, work_dir)]
    p = Path(s)
    if p.is_dir():
        return collect_local(s)
    if p.is_file():
        return [str(p)]
    # maybe a glob
    matches = glob.glob(s)
    if matches:
        return [m for m in matches if Path(m).suffix.lower() in SUPPORTED]
    raise FileNotFoundError(f"Source not found: {source}")
