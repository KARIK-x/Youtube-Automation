> **HISTORICAL REPORT — superseded.** Written at the time of that phase.
> Blocker lines below (e.g. "no OAuth") reflect that moment, not today.
> Current truth: run `python -m shorts_studio.cli.main status`.

# PHASE 0 AUDIT REPORT

**Date:** 2026-10-23
**Project:** `~/Downloads/ai automation OPENCODE/shorts_studio/`
**Research:** `~/Downloads/ai automation OPENCODE/FINAL_AUTOMATION_BLUEPRINT/`
**Scope:** Research + audit only. No Phase 1 implementation.

## 1. Repository state
- Git: not a git repository. No remote configured.
- Python 3.12.3, pytest 9.1.1.
- FFmpeg 8.0.1 (no libass). faster-whisper 1.2.1 (av 12.3.0). OpenCV 4.10. Pillow 12.3. edge-tts 7.3.1. APScheduler 3.11. yt-dlp 2026.10.21.
- macOS 14.3.1 (Sonoma), Apple M1, 8 GB RAM.

## 2. Component audit (evidence-based)

| Component | Status | Evidence |
|---|---|---|
| Config (YAML) | IMPLEMENTED | config.yaml |
| SQLite job store | IMPLEMENTED+TESTED-PASS | core/db.py; test_db.py (2 tests pass) |
| Source collection (local + urls.txt) | IMPLEMENTED | media/source.py |
| Transcription (faster-whisper, word ts) | IMPLEMENTED+TESTED-PASS | media/transcribe.py; test_render.py |
| EDL schema v1.0 + validator | IMPLEMENTED+TESTED-PASS | editing/edl.py; test_edl.py (3 tests pass) |
| Planner (deterministic, first-N-seconds) | IMPLEMENTED+TESTED-PASS | editing/planner.py; test_edl.py |
| Renderer (FFmpeg+OpenCV, sparse face crop, captions, audio, mux) | IMPLEMENTED+TESTED-PASS | editing/renderer.py, media/editor.py; test_render.py, test_crop.py |
| QC (dims/duration/black frames/clipping) | IMPLEMENTED+TESTED-PASS | editing/qc.py; test_qc.py (2 tests pass) |
| CLI (10 commands) | IMPLEMENTED | cli/main.py (verified manually) |
| Job persistence/recovery | IMPLEMENTED | DB transitions; test_db.py |
| Beat detection | NOT IMPLEMENTED | — |
| Music/SFX integration | NOT IMPLEMENTED | music=None in EDL |
| Candidate moment selection | NOT IMPLEMENTED | first-window only |
| YouTube publishing | NOT IMPLEMENTED (adapter in ~/yt-auto, unported) | — |
| Analytics adapter | NOT IMPLEMENTED | — |
| Thumbnail generation in pipeline | NOT IMPLEMENTED | media/thumbnail.py exists, unused |
| Caption word emphasis | NOT IMPLEMENTED | segment-level only |
| Content discovery | NOT IMPLEMENTED | — |
| Long-form | OUT OF SCOPE (v1) | — |

## 3. Rendering failure investigation

### Reported symptom
ray_food_chaos.json render appeared stuck in OpenCV face detection (Ctrl+C).

### Root cause (evidence from code)
`media/editor.py` `render_visual()` called `cascade.detectMultiScale(gray, 1.2, 5, minSize=(60,60))` on **every frame** at **full 1080×1920** resolution. For the 21.85s/60fps source (~1305 frames), this is ~1305 full-res Haar detections — slow on M1/8GB, appearing hung. No progress logging existed.

### Fix applied (Phase 0 blocker fix)
- Sparse face detection: every 15 frames (`face_detect_interval`), on 0.5× downscale, coordinates mapped back.
- Added progress logging every 300 frames + stage logging.
- Subprocess `run()` now has timeout=300s.
- Center-crop fallback via config `crop: center`.
- Face-aware crop preserved as optional mode.

### Reproduction status
The pre-fix hang was not reproduced separately (would require reverting; risky). The root cause is established by code inspection. Post-fix render of ray_food_chaos.json completes in ~115s with QC pass.

## 4. Tests run (actual results)
```
pytest tests/ -v  →  11 passed in 113.88s
```
- test_crop.py: test_center_crop PASS, test_face_crop_sparse PASS
- test_db.py: test_db_job_lifecycle PASS, test_db_counts PASS
- test_edl.py: test_edl_valid PASS, test_edl_invalid_duration PASS, test_edl_invalid_segment PASS, test_plan_creates_valid_edl PASS
- test_qc.py: test_qc_pass_on_rendered PASS, test_qc_fail_on_missing PASS
- test_render.py: test_render_integration PASS

## 5. Safe end-to-end render test
- Input: `data/work/plan/ray_food_chaos.json` (source 21.85s, 1080×1920, 60fps, chaos profile, 5 captions).
- Command: `PYTHONPATH=src python3 -m shorts_studio.cli.main render --plan data/work/plan/ray_food_chaos.json --output ray_food_chaos_test.mp4`
- Result: rendered in ~115s. QC PASS. Errors: none.
- FFprobe: h264 1080×1920 @ 29.97fps, aac, 21.79s.
- QC checks: has_video=True, has_audio=True, dimensions=1080x1920, duration=21.788s, black_segments=0, max_volume_db=-1.2.
- Captions verified burned: bottom-band pixel std 47.86 (caption frame) vs 26.19 (no-caption frame).

## 6. Baseline performance
- Transcription: 2.92s for 21.85s source (0.13× realtime) using faster-whisper base (CPU int8).
- Render: ~115s for 21.85s/60fps source (sparse face crop, 1306 frames).
- Output size: 24.8 MB for 21.8s.
- Peak memory: not precisely measured (ru_maxrss unreliable on macOS); faster-whisper base estimated 1-2GB. Render peak estimated 2-3GB. Sequential jobs keep peak <5GB target.

## 7. Preserved outputs
- `data/output/dolma_final.mp4` (24.4 MB) preserved.
- `data/output/final_final.mp4` (23.4 MB) preserved.
- `data/output/ray_food_chaos_test.mp4` (24.8 MB) new, distinct name.

## 8. Remaining blockers
- No YouTube publishing credentials (OAuth not configured) — publishing BLOCKED.
- No music/SFX integration (audio = normalized dialogue only).
- No beat detection.
- No candidate moment selection (first-window).
- No thumbnails in pipeline.
- Caption styling basic (no libass).
- av pin (12.3.0) not enforced in requirements.
- No first-party analytics.

## 9. Files changed (Phase 0)
- `src/shorts_studio/media/editor.py` (sparse detection, progress logging, timeout)
- `src/shorts_studio/editing/renderer.py` (stage logging, timeout, final_name param)
- `src/shorts_studio/cli/main.py` (render --output/--force, overwrite protection)
- `config.yaml` (face_detect_interval)
- `tests/test_crop.py` (new)
- Durable docs updated (KNOWN_BUGS, CURRENT_PROJECT_STATE, TEST_RESULTS)
- `PHASE_0_AUDIT_REPORT.md` (this file)

`~/yt-auto` not modified.

## 10. Exact next recommended task
Phase 1, task 1: enforce av==12.3.0 pin in requirements.txt and add beat detection module (librosa) with tests on ≥3 audio samples, before moment selection.

## Evidence
- Test output: 11 passed in 113.88s.
- FFprobe + QC output above.
- Source code inspection of editor.py lines ~100-130 (face detection loop).
- No uploads performed. No publishing configured.
