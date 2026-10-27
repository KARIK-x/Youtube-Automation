"""Regression tests for the `shorts` launcher script.

The launcher exists so the CLI works from any directory without python/python3
confusion. These tests keep it from silently rotting.
"""
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "shorts"


def test_launcher_exists_and_is_executable():
    assert LAUNCHER.is_file(), "shorts launcher missing"
    assert os.access(LAUNCHER, os.X_OK), "shorts launcher is not executable"


def test_launcher_points_at_real_project():
    text = LAUNCHER.read_text()
    # ROOT is now resolved dynamically (follows symlinks), so just check
    # that the project path is referenced and the script is self-locating.
    assert "BASH_SOURCE" in text or "dirname" in text
    assert "shorts_studio" in text or "ROOT" in text
    # functional check: running from a foreign dir resolves to this project
    import subprocess, os
    env = {**os.environ}; env.pop("PYTHONPATH", None)
    out = subprocess.run([str(LAUNCHER), "status", "--offline"],
                         cwd="/tmp", capture_output=True, text=True, env=env, timeout=120)
    assert out.returncode == 0
    assert "Shorts Studio" in out.stdout


def test_launcher_runs_from_foreign_directory(tmp_path):
    """The whole point: run it from somewhere that isn't the project."""
    env = {**os.environ}
    env.pop("PYTHONPATH", None)
    out = subprocess.run(
        [str(LAUNCHER), "--help"],
        cwd=str(tmp_path), capture_output=True, text=True, env=env, timeout=120,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert "status" in out.stdout


def test_launcher_defaults_to_status(tmp_path):
    env = {**os.environ}
    env.pop("PYTHONPATH", None)
    out = subprocess.run(
        [str(LAUNCHER), "status", "--offline"],
        cwd=str(tmp_path), capture_output=True, text=True, env=env, timeout=120,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert "Shorts Studio" in out.stdout
    assert "YouTube auth" in out.stdout
