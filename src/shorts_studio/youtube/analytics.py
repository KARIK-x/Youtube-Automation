"""YouTube analytics adapter (design + data model; collection requires OAuth)."""
import os, json, time

class AnalyticsAdapter:
    def __init__(self, cfg):
        self.cfg = cfg

    def is_configured(self):
        return os.path.exists(self.cfg["youtube"].get("token_file",""))

    def fetch_video_metrics(self, video_id):
        """Read-only: fetch basic metrics for a video via YouTube Analytics API. Returns dict or None."""
        if not self.is_configured():
            return None
        try:
            import pickle
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            with open(self.cfg["youtube"].get("token_file"), "rb") as f:
                creds = pickle.load(f)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(self.cfg["youtube"].get("token_file"), "wb") as f:
                        pickle.dump(creds, f)
                else:
                    return None
            yt = build("youtubeAnalytics", "v2", credentials=creds)
            from datetime import date, timedelta
            end = date.today()
            start = end - timedelta(days=30)
            resp = yt.reports().query(
                ids="channel==MINE",
                startDate=start.isoformat(),
                endDate=end.isoformat(),
                metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained",
                dimensions="video",
                filters=f"video=={video_id}",
                maxResults=1,
            ).execute()
            rows = resp.get("rows", [])
            if not rows:
                return {"video_id": video_id, "status": "no_data_in_range", "range": f"{start} to {end}"}
            r = rows[0]
            # columns: video, views, estimatedMinutesWatched, averageViewDuration, subscribersGained
            return {
                "video_id": video_id,
                "views": r[1],
                "watch_time_minutes": r[2],
                "avg_view_duration": r[3],
                "subscribers_gained": r[4],
                "range": f"{start} to {end}",
                "status": "OK",
            }
        except Exception as e:
            return {"video_id": video_id, "status": "ERROR", "error": type(e).__name__}

    @staticmethod
    def metrics_schema():
        return ["video_id","views","watch_time_minutes","avg_view_duration","avg_percentage_viewed",
                "impressions","ctr","likes","comments","shares","subscribers_gained","collected_at"]
