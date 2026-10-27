"""Regression tests for the `status` capability report.

Guards two things:
  1. status must report OAuth state from the live token, never from stale prose;
  2. status must never print secret material.
"""
import json, os, pickle, subprocess, sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.cli import main as cli


class _FakeCreds:
    def __init__(self, scopes=None, valid=True, expired=False, refresh="refresh-token-value"):
        self.scopes = scopes or [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/yt-analytics.readonly",
        ]
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh
        self.token = "SECRET-ACCESS-TOKEN-DO-NOT-PRINT"
        self.client_secret = "SECRET-CLIENT-SECRET-DO-NOT-PRINT"


def _write_token(tmp_path, creds):
    p = tmp_path / "token.json"
    with open(p, "wb") as f:
        pickle.dump(creds, f)
    os.chmod(p, 0o600)
    return str(p)


def test_token_state_reports_scopes_and_perms(tmp_path):
    tf = _write_token(tmp_path, _FakeCreds())
    st = cli._token_state(tf)
    assert st["present"] is True
    assert st["mode"] == "0o600"
    assert "youtube.upload" in st["scopes"]
    assert "yt-analytics.readonly" in st["scopes"]
    assert st["has_refresh"] is True


def test_token_state_missing_file(tmp_path):
    st = cli._token_state(str(tmp_path / "nope.json"))
    assert st == {"present": False}


def test_token_state_never_exposes_secrets(tmp_path):
    tf = _write_token(tmp_path, _FakeCreds())
    st = cli._token_state(tf)
    blob = repr(st)
    assert "SECRET-ACCESS-TOKEN" not in blob
    assert "SECRET-CLIENT-SECRET" not in blob
    assert "refresh-token-value" not in blob


def test_token_state_survives_corrupt_file(tmp_path):
    p = tmp_path / "token.json"
    p.write_bytes(b"not a pickle")
    st = cli._token_state(str(p))
    assert st["present"] is True
    assert "unreadable" in st


def test_audio_asset_state_counts_licensed(tmp_path):
    lib = tmp_path / "audio_library"
    lib.mkdir()
    (lib / "a.wav").write_bytes(b"x")
    (lib / "b.wav").write_bytes(b"x")
    (lib / "music_library.json").write_text(json.dumps({"tracks": [
        {"path": str(lib / "a.wav"), "title": "A", "mood": "hype",
         "license": "test-lic", "source": "t", "permitted_use": "test"},
        {"path": str(lib / "b.wav"), "title": "B", "mood": "soft",
         "license": "real-lic", "source": "t", "permitted_use": "publish"},
    ]}))
    cfg = {"audio": {"music_library_dir": str(lib)}}
    music_total, licensed, test, sfx_total, sfx_licensed, unregistered, _ = cli._audio_asset_state(cfg)
    assert music_total == 2
    assert licensed == 1
    assert test == 1


def test_status_command_reports_true_oauth_state():
    """The real repo status must reflect the token, not hardcoded prose."""
    out = subprocess.run(
        [sys.executable, "-m", "shorts_studio.cli.main", "status", "--offline"],
        cwd=str(ROOT), capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, timeout=120,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    text = out.stdout
    token_exists = (ROOT / "secrets" / "token.json").exists()
    if token_exists:
        assert "NOT AUTHORIZED" not in text
        assert "token present" in text or "AUTHORIZED" in text
    else:
        assert "NOT AUTHORIZED" in text
    # no secret leakage in stdout
    assert "refresh_token" not in text
    assert "ya29." not in text
