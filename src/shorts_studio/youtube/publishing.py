"""YouTube publishing adapter (dry-run by default)."""
import os, json, time
from pathlib import Path

class YouTubePublisher:
    def __init__(self, cfg, dry_run=True):
        self.cfg = cfg
        self.dry_run = dry_run
        self.client_secrets = cfg["youtube"].get("client_secrets")
        self.token_file = cfg["youtube"].get("token_file")

    def is_configured(self):
        return bool(self.client_secrets and os.path.exists(self.client_secrets))

    def channel_info(self):
        """Read-only: retrieve authorized channel basic info. Returns dict or None."""
        if not os.path.exists(self.token_file):
            return None
        try:
            import pickle
            from googleapiclient.discovery import build
            with open(self.token_file, "rb") as f:
                creds = pickle.load(f)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                    with open(self.token_file, "wb") as f:
                        pickle.dump(creds, f)
                else:
                    return None
            yt = build("youtube", "v3", credentials=creds)
            r = yt.channels().list(part="snippet,statistics", mine=True).execute()
            items = r.get("items", [])
            if not items:
                return None
            ch = items[0]
            return {
                "id": ch["id"],
                "title": ch["snippet"].get("title"),
                "description": ch["snippet"].get("description", "")[:200],
                "subscriber_count": ch["statistics"].get("subscriberCount"),
                "video_count": ch["statistics"].get("videoCount"),
                "view_count": ch["statistics"].get("viewCount"),
                "scopes": getattr(creds, "scopes", None),
            }
        except Exception as e:
            return {"error": type(e).__name__}

    def upload(self, video_path, title, description, tags, thumbnail_path=None, scheduled_at=None):
        """Returns dict with status, video_id (None in dry run), url, dry_run."""
        if self.dry_run:
            return {"status": "DRY_RUN", "video_id": None, "url": None,
                    "dry_run": True, "title": title, "would_upload": video_path}
        if not self.is_configured():
            return {"status": "BLOCKED", "video_id": None, "url": None,
                    "dry_run": False, "error": "OAuth client_secret.json missing"}
        # real upload (only if explicitly enabled)
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            import pickle
            creds = None
            if os.path.exists(self.token_file):
                with open(self.token_file,"rb") as f:
                    creds = pickle.load(f)
            if not creds or not creds.valid:
                return {"status": "BLOCKED", "error": "OAuth token invalid/expired; run auth first"}
            yt = build("youtube","v3",credentials=creds)
            body = {"snippet": {"title": title[:100], "description": description[:5000],
                                "tags": tags or [], "categoryId": self.cfg["youtube"]["category_id"]},
                    "status": {"privacyStatus": self.cfg["youtube"].get("privacy","private"),
                               "selfDeclaredMadeForKids": False}}
            if scheduled_at:
                body["status"]["privacyStatus"] = "private"
                body["status"]["publishAt"] = scheduled_at
            media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True, mimetype="video/mp4")
            req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
            resp = None
            while resp is None:
                status, resp = req.next_chunk()
            vid = resp["id"]
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumbnail_path)).execute()
                except Exception as e:
                    pass
            return {"status": "UPLOADED", "video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "dry_run": False}
        except Exception as e:
            return {"status": "FAILED", "video_id": None, "url": None, "dry_run": False, "error": str(e)}
