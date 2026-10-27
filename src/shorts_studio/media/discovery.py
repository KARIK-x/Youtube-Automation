"""Source discovery adapters (modular)."""
import os, json, hashlib, time
from urllib.parse import urlparse
try:
    import requests
except Exception:
    requests = None

class SourceAdapter:
    name = "base"
    def discover(self, **kw):
        raise NotImplementedError

class LocalFilesAdapter(SourceAdapter):
    name = "local_files"
    def discover(self, sources_dir, **kw):
        from .source import collect_local
        out = []
        for p in collect_local(sources_dir):
            out.append({"topic": os.path.basename(p), "source_url": None, "source_adapter": self.name,
                        "engagement_metrics": None, "rights_status": "UNKNOWN"})
        return out

class YouTubeRSSAdapter(SourceAdapter):
    name = "youtube_rss"
    def discover(self, channel_id=None, **kw):
        # Free, no auth. https://www.youtube.com/feeds/videos.xml?channel_id=...
        if not channel_id or requests is None:
            return []
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
        except Exception as e:
            return [{"error": str(e), "source_adapter": self.name}]
        # parse with stdlib
        import xml.etree.ElementTree as ET
        ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}
        try:
            root = ET.fromstring(r.text)
        except Exception as e:
            return [{"error": str(e), "source_adapter": self.name}]
        out = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", default="", namespaces=ns)
            vid = entry.findtext("yt:videoId", default="", namespaces=ns)
            link = entry.find("atom:link", ns)
            href = link.get("href") if link is not None else None
            published = entry.findtext("atom:published", default=None, namespaces=ns)
            out.append({"topic": title, "source_url": href, "source_adapter": self.name,
                        "publication_ts": published, "engagement_metrics": None,
                        "rights_status": "UNKNOWN"})
        return out

class YouTubeDataAPIAdapter(SourceAdapter):
    name = "youtube_data_api"
    def discover(self, api_key=None, query=None, max_results=10, **kw):
        if not api_key or requests is None:
            return [{"error": "no api key", "source_adapter": self.name}]
        # search endpoint
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {"part": "snippet", "q": query or "", "maxResults": max_results, "type": "video", "key": api_key}
        try:
            r = requests.get(url, params=params, timeout=20).json()
        except Exception as e:
            return [{"error": str(e), "source_adapter": self.name}]
        out = []
        for it in r.get("items", []):
            sn = it.get("snippet", {})
            out.append({"topic": sn.get("title"), "source_url": f"https://www.youtube.com/watch?v={it['id'].get('videoId')}",
                        "source_adapter": self.name, "publication_ts": sn.get("publishedAt"),
                        "engagement_metrics": None, "rights_status": "UNKNOWN"})
        return out

class RedditAdapter(SourceAdapter):
    name = "reddit"
    def discover(self, subreddits=None, limit=10, **kw):
        if requests is None:
            return [{"error": "requests not installed", "source_adapter": self.name}]
        subs = subreddits or ["videos", "PublicFreakout", "ContagiousLaughter", "MadeMeSmile"]
        out = []
        blocked = False
        for sub in subs:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
            try:
                r = requests.get(url, headers={"User-Agent": "shorts-studio/1.0"}, timeout=20)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                blocked = True
                continue
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                if d.get("is_video") or d.get("post_hint") == "hosted:video":
                    out.append({
                        "topic": d.get("title", "")[:120],
                        "source_url": "https://www.reddit.com" + d.get("permalink", ""),
                        "source_adapter": self.name,
                        "engagement_metrics": {"score": d.get("score", 0), "comments": d.get("num_comments", 0),
                                              "upvote_ratio": d.get("upvote_ratio")},
                        "rights_status": "UNKNOWN",
                        "subreddit": sub,
                        "duration": d.get("duration"),
                    })
        out = [o for o in out if "error" not in o]
        out.sort(key=lambda x: (x.get("engagement_metrics") or {}).get("score", 0), reverse=True)
        if not out and blocked:
            return [{"error": "Reddit blocked automated access (403). Use manual URL input or YouTube search instead.",
                    "source_adapter": self.name, "rights_status": "UNKNOWN"}]
        return out[:limit*2]


class HackerNewsAdapter(SourceAdapter):
    name = "hackernews"
    def discover(self, limit=15, **kw):
        if requests is None:
            return [{"error": "requests not installed", "source_adapter": self.name}]
        try:
            r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=20)
            r.raise_for_status()
            ids = r.json()[:limit*3]
        except Exception as e:
            return [{"error": str(e), "source_adapter": self.name}]
        out = []
        for sid in ids:
            try:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10).json()
            except Exception:
                continue
            if not item or item.get("type") != "story":
                continue
            title = item.get("title", "")
            # only video-ish / interesting topics
            out.append({
                "topic": title[:120],
                "source_url": item.get("url"),
                "source_adapter": self.name,
                "engagement_metrics": {"score": item.get("score", 0), "comments": item.get("descendants", 0)},
                "rights_status": "UNKNOWN",
            })
            if len(out) >= limit:
                break
        out.sort(key=lambda x: (x.get("engagement_metrics") or {}).get("score", 0), reverse=True)
        return out
class TikTokAdapter(SourceAdapter):
    name = "tiktok"
    def discover(self, **kw):
        return [{"error": "TikTok search requires login (no free API). "
                          "Workaround: find videos on TikTok, then run 'shorts download-url <tiktok_url>'. "
                          "Or search YouTube: yt-dlp 'ytsearch5:your query' --flat-playlist",
                "source_adapter": self.name, "rights_status": "UNKNOWN"}]


class PexelsAdapter(SourceAdapter):
    name = "pexels"
    def discover(self, query=None, api_key=None, per_page=8, download=False,
                 download_dir=None, min_duration=3, **kw):
        from . import stock_video
        key = api_key or os.environ.get("PEXELS_API_KEY")
        if not key:
            return [{"error": "PEXELS_API_KEY not set (free key: https://www.pexels.com/api/)",
                    "source_adapter": self.name, "rights_status": "UNKNOWN"}]
        try:
            items = stock_video.pexels_search(query or "", api_key=key,
                                             per_page=per_page, min_duration=min_duration)
        except Exception as e:
            return [{"error": str(e), "source_adapter": self.name}]
        out = []
        for it in items:
            rec = {"topic": it["topic"], "source_url": it["url"],
                   "source_adapter": self.name, "engagement_metrics": None,
                   "rights_status": "LICENSED", "license": it["license"],
                   "duration": it.get("duration"), "download_url": it.get("download_url")}
            if download and it.get("download_url"):
                try:
                    ddir = download_dir or os.path.join("data", "content", "sources", "stock")
                    path = stock_video.pexels_download(it, ddir)
                    rec["local_path"] = path
                    rec["topic"] = os.path.basename(path)
                except Exception as e:
                    rec["download_error"] = str(e)
            out.append(rec)
        return out

class GoogleTrendsAdapter(SourceAdapter):
    name = "google_trends"
    def discover(self, keywords=None, **kw):
        try:
            from pytrends.request import TrendReq
        except Exception:
            return [{"error": "pytrends not installed", "source_adapter": self.name}]
        try:
            pt = TrendReq(hl="en-US", tz=360)
            kw = keywords or ["IShowSpeed"]
            pt.build_payload(kw, timeframe="now 7-d")
            df = pt.interest_over_time()
            out = []
            for k in kw:
                score = float(df[k].iloc[-1]) if (k in df.columns and len(df)) else 0
                out.append({"topic": k, "source_url": None, "source_adapter": self.name,
                            "engagement_metrics": {"trend_score": score}, "rights_status": "UNKNOWN"})
            return out
        except Exception as e:
            return [{"error": str(e), "source_adapter": self.name}]

def get_adapter(name):
    mapping = {"local": LocalFilesAdapter, "youtube_rss": YouTubeRSSAdapter,
               "youtube_data_api": YouTubeDataAPIAdapter, "tiktok": TikTokAdapter,
               "google_trends": GoogleTrendsAdapter, "pexels": PexelsAdapter,
               "reddit": RedditAdapter, "hackernews": HackerNewsAdapter}
    cls = mapping.get(name)
    return cls() if cls else None

def list_adapters():
    return ["local", "youtube_rss", "youtube_data_api", "tiktok", "google_trends"]
