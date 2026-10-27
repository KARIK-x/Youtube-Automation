"""Regression tests for transcription caching and the model cache."""
import os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_studio.media import transcribe


def test_transcribe_cache_roundtrips_segments(tmp_path):
    src = "/tmp/s3.mp4"
    if not Path(src).exists():
        return  # skip quietly in CI without the fixture
    work = tmp_path / "w"
    work.mkdir()
    srt1, ass1, segs1 = transcribe.transcribe(src, str(work), "base", use_cache=True)
    assert len(segs1) > 0
    cache_files = list(work.glob("*.transcript.*.json"))
    assert cache_files, "transcript cache file was not written"

    # second call must come from cache and yield identical segments
    srt2, ass2, segs2 = transcribe.transcribe(src, str(work), "base", use_cache=True)
    assert len(segs2) == len(segs1)
    assert all(a.start == b.start and a.end == b.end and a.text == b.text
               for a, b in zip(segs1, segs2))


def test_transcribe_cache_invalidates_on_mtime(tmp_path):
    src = "/tmp/s3.mp4"
    if not Path(src).exists():
        return
    work = tmp_path / "w"
    work.mkdir()
    transcribe.transcribe(src, str(work), "base", use_cache=True)
    cache = list(work.glob("*.transcript.*.json"))[0]
    # tamper: bump the recorded source_mtime so the cache is rejected
    import json
    data = json.loads(cache.read_text())
    data["source_mtime"] = 0
    cache.write_text(json.dumps(data))
    # should still succeed (re-transcribes) and rewrite the cache
    srt, ass, segs = transcribe.transcribe(src, str(work), "base", use_cache=True)
    assert len(segs) > 0
    assert json.loads(cache.read_text())["source_mtime"] != 0


def test_model_cache_reuses_instance():
    m1 = transcribe.get_model("base")
    m2 = transcribe.get_model("base")
    assert m1 is m2, "model cache must reuse the instance"
    transcribe.clear_model_cache()
    m3 = transcribe.get_model("base")
    assert m3 is not m1
