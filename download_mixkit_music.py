"""Download free music from Mixkit (royalty-free, commercial use, no attribution).

Music page lists preview MP3s at:
  https://assets.mixkit.co/music/{id}/{id}.mp3
This script scrapes category pages, extracts IDs, downloads full MP3s, and
registers them in music_library.json with permitted_use="publish".
"""
import json, re, time
from pathlib import Path
import requests

ROOT = Path("/Users/ashim/Downloads/ai automation OPENCODE/shorts_studio")
LIB = ROOT / "data" / "audio_library"
LIB.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["hip-hop", "trap", "edm", "electronic", "cinematic", "ambient",
              "pop", "rock", "funk", "drum-and-bass", "dubstep", "house",
              "techno", "synthwave", "lo-fi-beats", "epic", "dramatic"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def scrape_ids(category):
    url = f"https://mixkit.co/free-stock-music/{category}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  fetch failed {category}: {e}")
        return []
    ids = set(re.findall(r"assets\.mixkit\.co/music/(\d+)/\d+\.mp3", r.text))
    return sorted(ids, key=int)


def download_track(sid, out_dir):
    url = f"https://assets.mixkit.co/music/{sid}/{sid}.mp3"
    dst = out_dir / f"mixkit_music_{sid}.mp3"
    if dst.exists() and dst.stat().st_size > 10000:
        return str(dst)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code != 200:
            return None
        dst.write_bytes(r.content)
        return str(dst)
    except Exception as e:
        print(f"    download failed {sid}: {e}")
        return None


all_ids = set()
cat_map = {}
for cat in set(CATEGORIES):
    ids = scrape_ids(cat)
    print(f"{cat}: {len(ids)} tracks")
    for sid in ids:
        all_ids.add(sid)
        cat_map.setdefault(sid, cat)
    time.sleep(0.5)

print(f"\nTotal unique music IDs: {len(all_ids)}")

# download (limit to 40 to keep storage reasonable)
to_download = sorted(all_ids, key=int)[:40]
downloaded = []
for sid in to_download:
    path = download_track(sid, LIB)
    if path:
        downloaded.append((sid, path, cat_map.get(sid, "misc")))
    time.sleep(0.3)

print(f"Downloaded: {len(downloaded)}")

# register in music_library.json
existing = json.loads((LIB / "music_library.json").read_text()).get("tracks", [])
existing = [t for t in existing if "mixkit_music_" not in t.get("path", "")]
new_tracks = []
for sid, path, cat in downloaded:
    rel = "data/audio_library/" + Path(path).name
    new_tracks.append({
        "path": rel,
        "title": f"Mixkit {cat} {sid}",
        "mood": "hype" if cat in ("hip-hop","trap","edm","electronic","dubstep","house","techno") else
                "epic" if cat in ("cinematic",) else
                "soft" if cat in ("ambient",) else "energetic",
        "bpm": None,
        "license": "Mixkit License (royalty-free, commercial use, no attribution required)",
        "source": "mixkit.co",
        "permitted_use": "publish",
        "attribution": "none required (Mixkit License)",
        "category": cat,
    })
all_tracks = existing + new_tracks
(LIB / "music_library.json").write_text(json.dumps({"tracks": all_tracks}, indent=2))
print(f"Registered {len(new_tracks)} new Mixkit music tracks. Total in library: {len(all_tracks)}")
