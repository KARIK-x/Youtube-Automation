import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.youtube.analytics import AnalyticsAdapter
from shorts_studio.youtube.publishing import YouTubePublisher

def test_analytics_readonly():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    ad = AnalyticsAdapter(cfg)
    assert ad.is_configured() is True
    m = ad.fetch_video_metrics("EogWjkR7ZcU")
    print("analytics:", m)
    assert m is not None
    assert m.get("status") in ("OK", "no_data_in_range", "ERROR")
    # no fabricated metrics if status is OK
    if m.get("status") == "OK":
        assert "views" in m
    print("analytics readonly OK")

def test_channel_info_readonly():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    pub = YouTubePublisher(cfg, dry_run=True)
    info = pub.channel_info()
    assert info is not None
    assert "error" not in info
    assert info["title"] == "Karikkkshorts"
    print("channel_info OK:", info["title"], info["subscriber_count"], "subs")

def test_dryrun_no_upload():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    pub = YouTubePublisher(cfg, dry_run=True)
    res = pub.upload("x.mp4", "T", "D", [], None)
    assert res["status"] == "DRY_RUN"
    assert res["video_id"] is None
    print("dryrun no upload OK")

if __name__ == "__main__":
    test_channel_info_readonly()
    test_analytics_readonly()
    test_dryrun_no_upload()
    print("READ-ONLY VERIFICATION TESTS PASS")