"""Regression tests for live-publish safety gates and beat-synced cuts."""
import json, os, sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.core import config, db as dbmod
from shorts_studio.cli import main as cli


def test_publish_refuses_without_confirm_live(tmp_path, monkeypatch):
    cfg = config.load_config(str(ROOT / "config.yaml"))
    # force dry_run false to test the confirm-live gate alone
    cfg["youtube"]["dry_run"] = False
    # monkeypatch load() by writing a temp config? load() reads ROOT/config.yaml.
    # Instead test the gate logic directly via cmd_publish with a fake job.
    db = dbmod.DB(str(tmp_path / "t.db"))
    out = tmp_path / "v.mp4"; out.write_bytes(b"x")
    thumb = tmp_path / "t.jpg"; thumb.write_bytes(b"x")
    jid = db.add_job("/tmp/x.mp4", profile="chaos", status="READY_FOR_REVIEW")
    db.update_job(jid, output_path=str(out), thumbnail_path=str(thumb),
                  duration=15.0, human_approved=1)
    # rights unknown -> publish_ready will fail on rights; approve rights by registering
    from shorts_studio.core import rights
    rr = rights.RightsRegistry(db)
    rr.register(asset_path="/tmp/x.mp4", acquisition_method="test",
               license_type="test", review_status="AUTHORIZED")
    # call cmd_publish with a fake args namespace, dry_run forced false via config edit
    # We'll temporarily flip config on disk? Instead monkeypatch config.load_config.
    import shorts_studio.core.config as cmod
    orig = cmod.load_config
    monkeypatch.setattr(cmod, "load_config", lambda p: cfg)
    # also patch cli.load (it calls config.load_config)
    monkeypatch.setattr(cli, "load", lambda: (cfg, db))
    ns = type("A", (), {"job_id": jid, "confirm_live": False,
                        "title": None, "description": None})()
    rc = cli.cmd_publish(ns)
    assert rc != 0


def test_publish_refuses_when_dry_run_true(tmp_path, monkeypatch):
    cfg = config.load_config(str(ROOT / "config.yaml"))
    cfg["youtube"]["dry_run"] = True
    db = dbmod.DB(str(tmp_path / "t.db"))
    out = tmp_path / "v.mp4"; out.write_bytes(b"x")
    thumb = tmp_path / "t.jpg"; thumb.write_bytes(b"x")
    jid = db.add_job("/tmp/x.mp4", profile="chaos", status="READY_FOR_REVIEW")
    db.update_job(jid, output_path=str(out), thumbnail_path=str(thumb),
                  duration=15.0, human_approved=1)
    from shorts_studio.core import rights
    rights.RightsRegistry(db).register(asset_path="/tmp/x.mp4", acquisition_method="test",
                                      license_type="test", review_status="AUTHORIZED")
    import shorts_studio.core.config as cmod
    monkeypatch.setattr(cmod, "load_config", lambda p: cfg)
    monkeypatch.setattr(cli, "load", lambda: (cfg, db))
    ns = type("A", (), {"job_id": jid, "confirm_live": True,
                        "title": None, "description": None})()
    rc = cli.cmd_publish(ns)
    assert rc != 0


def test_publish_calls_upload_when_gates_pass(tmp_path, monkeypatch):
    cfg = config.load_config(str(ROOT / "config.yaml"))
    cfg["youtube"]["dry_run"] = False
    db = dbmod.DB(str(tmp_path / "t.db"))
    out = tmp_path / "v.mp4"; out.write_bytes(b"x")
    thumb = tmp_path / "t.jpg"; thumb.write_bytes(b"x")
    jid = db.add_job("/tmp/x.mp4", profile="chaos", status="READY_FOR_REVIEW")
    db.update_job(jid, output_path=str(out), thumbnail_path=str(thumb),
                  duration=15.0, human_approved=1)
    from shorts_studio.core import rights
    rights.RightsRegistry(db).register(asset_path="/tmp/x.mp4", acquisition_method="test",
                                      license_type="test", review_status="AUTHORIZED")
    import shorts_studio.core.config as cmod
    monkeypatch.setattr(cmod, "load_config", lambda p: cfg)
    monkeypatch.setattr(cli, "load", lambda: (cfg, db))

    # mock the publisher so no real API call happens
    class FakePub:
        def __init__(self, cfg, dry_run=False):
            self.dry_run = dry_run
        def upload(self, *a, **k):
            return {"status": "UPLOADED", "video_id": "TEST123",
                    "url": "https://www.youtube.com/watch?v=TEST123", "dry_run": False}
    import shorts_studio.youtube.publishing as pubmod
    monkeypatch.setattr(pubmod, "YouTubePublisher", FakePub)

    ns = type("A", (), {"job_id": jid, "confirm_live": True,
                        "title": "T", "description": "D"})()
    rc = cli.cmd_publish(ns)
    assert rc == 0
    job = db.get_job(jid)
    assert job["status"] == "PUBLISHED"
    assert job["youtube_id"] == "TEST123"
    import types
    from shorts_studio.editing import planner
    src = "/tmp/s3.mp4"
    if not Path(src).exists():
        return
    seg = types.SimpleNamespace(start=0.0, end=10.0, text="hello world", words=[])
    # audio with beats + a silence gap near a beat
    audio = {"beats": [2.0, 4.5, 7.0], "silence": [{"start": 1.8, "end": 2.3}],
             "duration": 15.0, "clipping": {"clipping": False}}
    edl = planner.plan(src, [seg], profile="chaos", target_duration=15,
                       moment={"start": 0.0, "end": 15.0}, audio=audio, beat_cuts=True)
    assert "segments" in edl
    assert all(s["end"] > s["start"] for s in edl["segments"])
    # at least one segment boundary should land on a beat when silence permits
    bounds = {round(s["start"], 2) for s in edl["segments"]} | {round(s["end"], 2) for s in edl["segments"]}
    # 2.0 is near a silence gap -> expect a cut there
    assert any(abs(b - 2.0) < 0.6 for b in bounds), f"no beat cut near 2.0: {bounds}"


def test_beat_cuts_off_by_default_single_segment():
    import types
    from shorts_studio.editing import planner
    src = "/tmp/s3.mp4"
    if not Path(src).exists():
        return
    seg = types.SimpleNamespace(start=0.0, end=10.0, text="hello world", words=[])
    audio = {"beats": [2.0, 4.5, 7.0], "silence": [{"start": 1.8, "end": 2.3}],
             "duration": 15.0, "clipping": {"clipping": False}}
    edl = planner.plan(src, [seg], profile="chaos", target_duration=15,
                       moment={"start": 0.0, "end": 15.0}, audio=audio)
    assert len(edl["segments"]) == 1
