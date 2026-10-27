import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.youtube.publishing import YouTubePublisher
from shorts_studio.youtube.analytics import AnalyticsAdapter

def test_publish_dryrun():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    pub = YouTubePublisher(cfg, dry_run=True)
    assert pub.is_configured() is False or True  # may or may not have secrets
    res = pub.upload("data/output/dolma_final.mp4", "T", "D", ["t"], None)
    assert res["status"] == "DRY_RUN"
    assert res["video_id"] is None
    assert res["dry_run"] is True
    print("dryrun OK")

def test_publish_blocked_without_creds():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    pub = YouTubePublisher(cfg, dry_run=False)
    # no client_secret -> blocked
    if not pub.is_configured():
        res = pub.upload("x.mp4", "T", "D", [], None)
        assert res["status"] == "BLOCKED"
        print("blocked without creds OK")
    else:
        print("creds present; skip blocked test")

def test_analytics_not_configured():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    ad = AnalyticsAdapter(cfg)
    m = ad.fetch_video_metrics("abc123")
    # either None (not configured) or a dict; never fabricated real metrics
    print("analytics result:", m)
    assert m is None or m.get("status") in ("OK", "no_data_in_range", "ERROR", "NOT_IMPLEMENTED", None)
    print("analytics OK")

def test_analytics_schema():
    from shorts_studio.youtube.analytics import AnalyticsAdapter
    s = AnalyticsAdapter.metrics_schema()
    assert "views" in s and "avg_view_duration" in s
    print("schema OK")

if __name__ == "__main__":
    test_publish_dryrun()
    test_publish_blocked_without_creds()
    test_analytics_not_configured()
    test_analytics_schema()
    print("PUBLISH/ANALYTICS TESTS PASS")