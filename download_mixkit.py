"""Download free SFX from Mixkit (royalty-free, commercial use, no attribution).

Mixkit SFX pages list preview MP3s at:
  https://assets.mixkit.co/active_storage/sfx/{id}/{id}-preview.mp3
The full WAV is at:
  https://assets.mixkit.co/active_storage/sfx/{id}/{id}.wav

This script scrapes category pages, extracts IDs, downloads full WAVs, and
registers them in sfx_library.json with permitted_use="publish".
"""
import json, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "data" / "audio_library"
SFX = LIB / "sfx"
SFX.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["whoosh", "impact", "transition", "glitch", "cinematic", "hit",
              "pop", "notification", "ding", "sweep", "swoosh", "thud", "boom",
              "crash", "swoosh", "whoosh", "swish", "zoom", "whoosh", "sweep"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def scrape_ids(category):
    url = f"https://mixkit.co/free-sound-effects/{category}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  fetch failed {category}: {e}")
        return []
    ids = set(re.findall(r"active_storage/sfx/(\d+)/\d+-preview\.mp3", r.text))
    return sorted(ids, key=int)


def download_sfx(sid, out_dir):
    url = f"https://assets.mixkit.co/active_storage/sfx/{sid}/{sid}.wav"
    dst = out_dir / f"mixkit_{sid}.wav"
    if dst.exists() and dst.stat().st_size > 1000:
        return str(dst)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        dst.write_bytes(r.content)
        return str(dst)
    except Exception as e:
        print(f"    download failed {sid}: {e}")
        return None


# collect unique ids across categories
all_ids = set()
cat_map = {}
for cat in set(CATEGORIES):
    ids = scrape_ids(cat)
    print(f"{cat}: {len(ids)} sfx")
    for sid in ids:
        all_ids.add(sid)
        cat_map.setdefault(sid, cat)
    time.sleep(0.5)

print(f"\nTotal unique SFX IDs: {len(all_ids)}")

# download (limit to first 80 to keep storage reasonable)
to_download = sorted(all_ids, key=int)[:80]
downloaded = []
for sid in to_download:
    path = download_sfx(sid, SFX)
    if path:
        downloaded.append((sid, path, cat_map.get(sid, "misc")))
    time.sleep(0.2)

print(f"Downloaded: {len(downloaded)}")

# register in sfx_library.json
existing = json.loads((SFX.parent / "sfx_library.json").read_text()).get("tracks", [])
# remove old mixkit entries to avoid dupes
existing = [t for t in existing if "mixkit_" not in t.get("path", "")]
new_tracks = []
for sid, path, cat in downloaded:
    rel = "data/audio_library/sfx/" + Path(path).name
    new_tracks.append({
        "path": rel,
        "title": f"Mixkit {cat} {sid}",
        "mood": "sfx",
        "license": "Mixkit License (royalty-free, commercial use, no attribution required)",
        "source": "mixkit.co",
        "permitted_use": "publish",
        "attribution": "none required (Mixkit License)",
        "category": cat,
    })
all_tracks = existing + new_tracks
# keep test sfx
(SFX.parent / "sfx_library.json").write_text(json.dumps({"tracks": all_tracks}, indent=2))
print(f"Registered {len(new_tracks)} new Mixkit SFX. Total in library: {len(all_tracks)}")
