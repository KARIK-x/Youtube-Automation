> **HISTORICAL REPORT — superseded.** Written at the time of that phase.
> Blocker lines below (e.g. "no OAuth") reflect that moment, not today.
> Current truth: run `python -m shorts_studio.cli.main status`.

# PHASE 2.1 REPORT

## Objective
Integration phase: connect audio mixer, complete beat-aware editing, integrate thumbnails, validate moment scoring, verify dependency reproducibility, end-to-end test.

## Files changed
- src/shorts_studio/editing/renderer.py (music/SFX mixer wired, beat-synced zooms, stage logging)
- src/shorts_studio/media/editor.py (caption keyword emphasis; render_visual zooms param)
- src/shorts_studio/editing/sfx.py (load_sfx_library; Path import fix)
- src/shorts_studio/cli/main.py (thumbnail cmd, check-deps av check, cmd_run thumbnail integration)
- config.yaml (audio library dirs)
- requirements.txt (already present)
- tests/test_moment_validation.py (new, 4 tests)
- Durable docs updated (CURRENT_PROJECT_STATE, TASK_QUEUE, TEST_RESULTS, KNOWN_BUGS)

## Tests and results
- pytest tests/: 29 passed in 72.52s
  - test_edl.py: 4 PASS
  - test_db.py: 2 PASS
  - test_qc.py: 2 PASS
  - test_render.py: 1 PASS
  - test_crop.py: 2 PASS
  - test_audio.py: 4 PASS
  - test_moment.py: 3 PASS
  - test_beat_profile.py: 4 PASS
  - test_sfx.py: 3 PASS
  - test_moment_validation.py: 4 PASS

## Rendered output
- dolma_phase21_test.mp4: 1080x1920, 20.0s, QC PASS, 0 black, max vol -1.2dB. FFprobe h264/aac. Captions burned. Music+SFX mixed (max_volume=-1.5dB, clipping=False).
- dolma_phase21_thumb.jpg: 253KB, exists.

## Music/SFX reached rendered output?
YES (with synthetic test assets). Mixer path exercised: music "Synthetic test music" + 3 SFX placements. max_volume=-1.5dB, clipping=False. Fallback (dialogue-only) path also exists when no assets.

## Beat synchronization verified?
Partially. Beat detection (bpm 80 for dolma) and sync_zooms applied to zooms in planner (zoom window snapped to beats). Beat-synced cuts NOT in renderer. Logged via "[renderer] beat-synced zooms".

## Thumbnail verification
dolma_phase21_thumb.jpg exists (253KB). Standalone CLI command works. Integrated into cmd_run.

## Dependency reproducibility
requirements.txt pins av==12.3.0. check-deps verifies av version and warns on mismatch. scipy/numpy checked.

## Candidate scoring validation
Features documented in moment_selector.py: speech coverage, early hook, beat richness, scene changes, audio energy, clipping penalty, silence penalty. Tested: short dialogue, repeated segments (dedup), zero-duration, reasons present. Heuristic score, not virality probability. Source rights eligibility is a gate (not yet enforced in selector; documented).

## Existing outputs unchanged
md5 verified: dolma_final.mp4, final_final.mp4, ray_food_chaos_test.mp4, ray_phase1_test.mp4 all unchanged.

## Limitations
- Music/SFX tested with synthetic test assets only (permitted_use=test), not licensed music.
- Beat-synced cuts not implemented (zoom sync only).
- Moment selection heuristic, not semantic.
- Caption emphasis keyword-based.
- av pin in requirements but not auto-enforced at install.
- No YouTube publishing (no credentials).
- No trend discovery, long-form.

## Features not yet tested
- Beat-synced cuts in renderer: NOT IMPLEMENTED
- Music mixing with licensed audio: NOT TESTED (no licensed assets)
- YouTube publishing: BLOCKED (no credentials)
- Analytics: BLOCKED

## Exact next recommended phase (Phase 3)
Implement candidate scoring v1 with source-rights tracking and duplicate detection; port YouTube publishing adapter in dry-run mode; add beat-synced cuts to renderer; tune profiles with real samples. Wait for approval.