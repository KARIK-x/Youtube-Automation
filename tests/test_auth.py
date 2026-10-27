import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.cli import main as cli_main

def test_auth_missing_secrets():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    # point to nonexistent
    cfg["youtube"]["client_secrets"] = str(ROOT / "secrets" / "nonexistent.json")
    # monkeypatch load
    orig_load = cli_main.load
    cli_main.load = lambda: (cfg, __import__("shorts_studio.core.db", fromlist=["DB"]).DB(str(ROOT / "data" / "state.db")))
    # call cmd_auth
    import argparse
    args = argparse.Namespace()
    rc = cli_main.cmd_auth(args)
    assert rc == 1
    cli_main.load = orig_load
    print("auth missing secrets -> blocked (rc=1) OK")

def test_auth_scopes_defined():
    assert hasattr(cli_main, "SCOPES")
    assert "youtube.upload" in " ".join(cli_main.SCOPES)
    assert "yt-analytics.readonly" in " ".join(cli_main.SCOPES)
    print("scopes OK:", cli_main.SCOPES)

def test_publisher_dry_run_default():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    from shorts_studio.youtube.publishing import YouTubePublisher
    pub = YouTubePublisher(cfg)  # default dry_run=True
    assert pub.dry_run is True
    res = pub.upload("x.mp4", "T", "D", [], None)
    assert res["status"] == "DRY_RUN"
    assert res["video_id"] is None
    print("publisher default dry_run OK")

def test_publisher_is_configured_with_secret():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    from shorts_studio.youtube.publishing import YouTubePublisher
    pub = YouTubePublisher(cfg, dry_run=False)
    # secret exists now
    assert pub.is_configured() is True
    print("publisher is_configured OK (secret present)")

if __name__ == "__main__":
    test_auth_missing_secrets()
    test_auth_scopes_defined()
    test_publisher_dry_run_default()
    test_publisher_is_configured_with_secret()
    print("AUTH TESTS PASS")