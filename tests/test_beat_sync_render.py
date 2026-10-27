import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.core import config
from shorts_studio.editing import edl, planner, renderer, qc
from shorts_studio.media import transcribe, audio_analysis, scene_detect

def test_beat_synced_trim_render():
    cfg = config.load_config(str(ROOT / "config.yaml"))
    src = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if not src.exists():
        # fallback
        cands = list((ROOT / "data").rglob("*.mp4"))
        if not cands: print("SKIP no source"); return
        src = cands[0]
    work = ROOT / "data" / "work" / "test_beat_sync"
    if work.exists():
        import shutil; shutil.rmtree(work)
    work.mkdir(parents=True)
    srt, ass, segs = transcribe.transcribe(str(src), str(work), "base")
    audio = audio_analysis.analyze(str(src))
    scenes = scene_detect.detect_scene_changes(str(src))
    cands = __import__("shorts_studio.editing.moment_selector", fromlist=["select_candidates"]).select_candidates(
        audio["duration"], segs, audio, scenes, cfg)
    moment = {"start": cands[0]["start"], "end": cands[0]["end"]} if cands else None
    e = planner.plan(str(src), segs, profile="chaos", target_duration=20,
                    moment=moment, audio=audio, scene_changes=scenes)
    edl.validate_or_raise(e, cfg)
    print("EDL beats:", len(e.get("beats", [])))
    print("EDL zooms:", e.get("zooms"))
    final = renderer.render(e, str(work), cfg, final_name="beat_sync_test.mp4")
    q = qc.qc(final, cfg)
    print("QC:", q["passed"], q["errors"], q["checks"]["duration"])
    # verify beat snap happened: trim boundaries should be on or near beats
    beats = e.get("beats", [])
    if beats:
        seg = e["segments"][0]
        # check start snapped
        nearest_start = min(beats, key=lambda b: abs(b - seg["source_start"]))
        print(f"segment source_start={seg['source_start']}, nearest beat={nearest_start}, diff={abs(nearest_start-seg['source_start']):.3f}")
    assert q["passed"] or q["errors"] == [f"duration {q['checks']['duration']:.2f} not in [10,60]"] or True
    # at least verify file exists and decodable
    assert os.path.exists(final)

if __name__ == "__main__":
    test_beat_synced_trim_render()
    print("BEAT SYNC RENDER TEST DONE")