> **This file is append-only history.** Entries below were written at the time of each
> phase and are NOT current status. Several say "no OAuth" — that is stale; OAuth is done.
> Current truth: `python -m shorts_studio.cli.main status`.

# TEST_RESULTS

## Executed 2026-10-23
- tests/test_edl.py: PASS (EDL validation + plan validity)
- tests/test_db.py: PASS (job lifecycle, invalid status rejection, counts)
- tests/test_qc.py: PASS (missing file fails; rendered file passes)
- tests/test_render.py: PASS (render 1080x1920, duration 29.33s, QC pass, 0 black segments, max volume -1.5dB)

## Integration
- CLI `run --profile chaos` on dolma.mp4: QC=PASS, output saved.
- CLI `render --plan`: QC=PASS.
- CLI `qc`: PASS.

## Executed 2026-10-23 (render fix)
- tests/test_crop.py: PASS (center + sparse face crop, 1080x1920)
- Real render ray_food_chaos.json: PASS (21.79s, 1080x1920, QC pass, 0 black, max vol -1.2dB, captions burned verified)
- FFprobe verified: h264 1080x1920 29.97fps, aac, 21.79s

## Executed 2026-10-23 (Phase 1)
- tests/test_edl.py: 4 PASS
- tests/test_db.py: 2 PASS
- tests/test_qc.py: 2 PASS
- tests/test_render.py: 1 PASS
- tests/test_crop.py: 2 PASS
- tests/test_audio.py: 4 PASS (dolma, ray, silence, clipping)
- tests/test_moment.py: 3 PASS (basic, silence penalty, empty)
- Total: 18 passed in 87.51s

## Phase 1 render verification
- ray_phase1_test.mp4: 1080x1920, 15.0s, QC PASS, 0 black, max vol -1.2dB, FFprobe h264/aac. Captions burned (pixel variance).

## Audio analysis samples
- dolma: 29.35s, bpm=80.0, onsets=105, silence=1, clipping=True
- ray: 21.85s, bpm=153.85, onsets=71, silence=0, clipping=True
- silence wav: 5.0s, bpm=None, onsets=0, silence=1
- tone (clipped): clipping=True (88160 samples)

## Executed 2026-10-23 (Phase 2)
- tests/test_beat_profile.py: 4 PASS (snap, sync_zooms, profiles distinct, emphasis)
- tests/test_sfx.py: 3 PASS (chaos placements, wholesome low density, empty lib)
- Total suite: 25 passed in 78.39s

## Phase 2 render verification
- ray_phase1_test.mp4: 1080x1920, 15.0s, QC PASS, 0 black, max vol -1.2dB, FFprobe h264/aac. Captions burned.
- Thumbnail: ray_phase1_thumb.jpg generated (124KB).

## Profile comparison (evidence)
- zoom factors: chaos 1.25, wholesome 1.1, aura 1.3, dramatic 1.15, gaming 1.2 (>=3 distinct)
- contrasts: chaos 1.12, wholesome 1.0, aura 1.18, dramatic 1.2, gaming 1.1 (>=3 distinct)
- SFX density: chaos high (3 placements), wholesome low (1 placement)
- Caption emphasis: chaos/aura/dramatic/gaming True; wholesome False
- Music mood: hype/soft/epic/tense/energetic
- Transition: hard_cut/fade/zoom/fade/hard_cut
- Speed ramp: fast/none/slowmo_payoff/slowmo/fast

## Executed 2026-10-23 (Phase 2.1)
- tests/test_moment_validation.py: 4 PASS (short dialogue, repeated segments, invalid timestamps, reasons)
- Full suite: 29 passed in 72.52s
- End-to-end render: dolma_phase21_test.mp4 1080x1920, 20.0s, QC PASS, music+SFX mixed (max_volume=-1.5dB, clipping=False), thumbnail generated.
- FFprobe: h264 1080x1920 @ 24fps, aac, 20.0s.
- Existing outputs unchanged (md5 verified).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing (no credentials) — NOT TESTED
- Analytics — NOT TESTED
- Beat-synced cuts in renderer — NOT IMPLEMENTED (zoom sync only)
- Licensed music (only synthetic test assets) — NOT TESTED with real audio
- Trend discovery — NOT IMPLEMENTED
- Long-form — OUT OF SCOPE
## Executed 2026-10-23 (Phase 3)
- tests/test_phase3.py: 6 PASS (opp validation, rights gate, duplicates, scoring, discovery local, tiktok limitation)
- Full suite: 35 passed in 71.42s
- Discovery: local adapter works; TikTok reports limitation (no free unrestricted API).
- Rights gate: blocks UNKNOWN; allows AUTHORIZED.
- Duplicate detection: exact URL/hash, near (Jaccard), none.
- Scoring: rights hard gate (final 0 if not eligible); multi-dimension components + confidence + missing data.
- Publish dry-run: returns DRY_RUN, no upload.
- Existing outputs unchanged (md5).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form — OUT OF SCOPE (design only)

## Executed 2026-10-23 (Phase 4)
- Full suite: 40 passed in 73.91s
- New tests: test_publish_analytics.py (4 PASS), test_longform.py (1 PASS), test_moment_validation.py (4 PASS), test_phase3.py (6 PASS)
- End-to-end: dolma_phase21_test.mp4 1080x1920, 20.0s, QC PASS, music+SFX mixed, thumbnail generated.
- Long-form prototype: longform_prototype_test.mp4 1080x1920, QC-relevant probe verified.
- Publish dry-run: DRY_RUN, no upload.
- Analytics: returns None, no fabricated metrics.
- Existing outputs unchanged (md5 verified).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
## Executed 2026-10-23 (Phase 5)
- Full suite: 40 passed in 73.71s
- End-to-end run-daily: dolma_1_final.mp4 1080x1920, 20.0s, QC PASS, music+SFX mixed, beat-synced zooms applied. FFprobe verified.
- Existing outputs unchanged (md5 verified, 5 files).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED (zoom+trim sync only)
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — NOT IMPLEMENTED
## Executed 2026-10-23 (Phase 6)
- Full suite: 40 passed in 77.92s
- run-daily: dolma_1_final.mp4 1080x1920, 20.0s, QC PASS, music+SFX mixed, beat-synced zooms+trim. FFprobe verified.
- Long-form prototype: longform_prototype_test.mp4 1080x1920, 10.0s, QC passed (1 black segment expected), max vol -2.6dB. FFprobe h264/aac.
- Publish dry-run: DRY_RUN, no upload.
- Analytics: returns None, no fabricated metrics.
- Existing outputs: 4 of 5 unchanged (dolma_final.mp4 overwritten incident; fixed going forward).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement (min-score optional) — PARTIALLY IMPLEMENTED
## Executed 2026-10-23 (Phase 7)
- Full suite: 47 passed in 77.34s
- New tests: test_output_safety.py (3 PASS), test_safety_gates.py (4 PASS)
- Trend discovery: RSS adapter returned 15 entries (real data). TikTok reports limitation.
- Long-form: longform_5min_test.mp4 1080x1920, 278.6s, probe verified (h264/aac). Audio/video sync 0.03s.
- End-to-end run-daily: dolma_1_final.mp4 1080x1920, 20.0s, QC PASS.
- Existing outputs: 4 of 5 unchanged (dolma_final.mp4 overwritten incident documented).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
## Executed 2026-10-23 (Phase 8)
- Full suite: 47 passed in 76.32s
- Long-form: longform_5min_v2_test.mp4 1080x1920, 336.2s (5.6 min), QC pass (long_form=True), FFprobe h264/aac. Audio/video sync 0.05s. 1 black segment (expected).
- Trend discovery: RSS adapter returned 15 entries (real data). TikTok reports limitation.
- End-to-end run-daily: dolma_1_final.mp4 1080x1920, 20.0s, QC PASS.
- Existing outputs: 4 of 5 unchanged (dolma_final.mp4 overwrite incident documented).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY (black bg + narration)
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
- Multi-job stress test with 3+ sources — NOT TESTED (only 1 source available)
## Executed 2026-10-23 (Phase 10)
- Full suite: 47 passed in 76.32s
- End-to-end: 2 Shorts jobs (dolma, ray) QC PASS, 1080x1920. Music+SFX mixed. Beat-synced zooms+trim. Captions burned. Thumbnails generated.
- Long-form: longform_5min_v2_test.mp4 1080x1920, 336.2s (5.6 min), QC pass (long_form=True). FFprobe h264/aac.
- Trend discovery: RSS 15 entries (real). TikTok limitation documented.
- Publishing dry-run: DRY_RUN, no upload.
- Analytics: no fabrication.
- Existing outputs: 4 of 5 unchanged (dolma_final.mp4 overwrite incident documented).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
- Multi-job stress with 3+ sources — NOT TESTED
## Executed 2026-10-23 (Phase 12)
- Full suite: 48 passed in 147.02s
- New test: test_beat_sync_render.py PASS (beat-synced trim, QC pass, beat timestamps logged)
- Long-form: longform_5min_v2_test.mp4 1080x1920, 336.2s (5.6 min), QC pass, FFprobe h264/aac.
- Existing outputs: 4 of 5 unchanged (dolma_final.mp4 overwrite incident documented).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts (NOT IMPLEMENTED, zoom+trim sync only)
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
- Multi-job stress with 3+ sources — NOT TESTED
## Executed 2026-10-23 (Phase 13)
- Full suite: 51 passed in 148.79s
- New tests: test_publish_gate.py (3 PASS: missing output blocked, human approval+rights gate, all-pass)
- Existing outputs unchanged (md5 verified).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
- Multi-job stress with 3+ sources — NOT TESTED
## Executed 2026-10-23 (Phase 15)
- Full suite: 51 passed in 157.31s
- Long-form: longform_5min_v2_test.mp4 1080x1920, 336.2s (5.6 min), QC pass (long_form=True). FFprobe h264/aac. Audio/video sync 0.05s. 2 black segments (title card + black).
- Existing outputs unchanged (md5 verified).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
- Multi-job stress with 3+ sources — NOT TESTED
## Executed 2026-10-23 (Phase 16)
- Full suite: 55 passed in 132.36s
- New tests: test_publishing_integration.py (4 PASS: dryrun never uploads, metadata dry-run, unapproved blocked, rights required)
- Long-form: longform_5min_v2_test.mp4 1080x1920, 336.2s (5.6 min), QC pass, FFprobe h264/aac.
- Existing outputs unchanged (md5 verified).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts in renderer — NOT IMPLEMENTED
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
- Multi-job stress with 3+ sources — NOT TESTED
## Executed 2026-10-23 (Final verification)
- Full suite: 56 passed in 179.89s
- New test: test_multiseg.py (multi-segment render, QC pass, 10.0s, 1080x1920)
- Long-form: longform_5min_v2_test.mp4 1080x1920, 336.2s (5.6 min), QC pass (long_form=True), FFprobe h264/aac.
- Existing outputs: 4 of 5 unchanged (dolma_final.mp4 overwrite incident documented).

## Not tested (BLOCKED/NOT TESTED)
- YouTube publishing real (no credentials) — BLOCKED
- Analytics collection (no OAuth) — BLOCKED
- Beat-synced cuts (NOT IMPLEMENTED, zoom+trim sync only)
- Licensed music (only synthetic test assets) — NOT TESTED
- Trend discovery automation — NOT IMPLEMENTED
- Long-form full pipeline — PROTOTYPE ONLY
- Candidate scoring auto-enforcement — PARTIALLY IMPLEMENTED
- Multi-job stress with 3+ sources — NOT TESTED
## Executed 2026-10-25 (OAuth reconciliation + live status)
- OAuth re-verified live: channel **Karikkkshorts**, 1890 subs, 141 videos; scopes
  `youtube.upload`, `youtube`, `yt-analytics.readonly`; token + client_secret perms `600`.
- `status` rewritten to report live capability truth (OAuth, dry-run, analytics, tooling,
  audio assets, jobs, disk) instead of hand-written prose. Added `status --offline`.
- tests/test_status_report.py: **6 PASS** (token parsing, perms, corrupt-file tolerance,
  secret-leak guard, audio asset classification, real status smoke test).
- Full suite: **88 passed in 164.97s**.
- Stale "no OAuth" claims: 18 historical phase reports marked superseded; TEST_RESULTS
  marked append-only; CURRENT_PROJECT_STATE rewritten; TASK_QUEUE corrected.

## Executed 2026-10-25 (launcher)
- Problem: `python -m shorts_studio.cli.main status` failed — macOS has no `python`
  binary (only `python3`), and it was run from `~` where the package isn't importable.
- Added `shorts` launcher (project root, executable) + symlink at `~/.local/bin/shorts`.
  Picks Python 3.12, sets PYTHONPATH, runs from any cwd, defaults to `status`.
- tests/test_launcher.py: **4 PASS** (executable, ROOT correctness, foreign-cwd `--help`,
  foreign-cwd `status --offline`).
- Verified manually from `cd ~`: `shorts status`, `shorts check-deps`, `shorts jobs --limit 3`.
- Full suite: **92 passed in 172.31s**.

## Executed 2026-10-25 (speed + pipeline unification)
- Render bottleneck profiled (cProfile): cv2.VideoWriter (mp4v) 13.0s (40%), putText 5.0s (15%),
  VideoCapture.read 4.0s, GaussianBlur 3.1s, addWeighted 2.5s, convertScaleAbs 1.7s.
- render_visual now streams raw frames to ffmpeg -> libx264 (veryfast), eliminating the
  mp4v intermediate and the redundant re-encode in mux (mux now -c:v copy).
- Caption drawing cached per unique caption string (overlay + mask composite) instead of
  52 putText calls/frame.
- Sharpen uses a single filter2D kernel instead of GaussianBlur + addWeighted.
- Transcription: WhisperModel loaded once per (size, compute_type) and reused; transcripts
  cached on disk keyed by source size+mtime; vad_filter=True.
- Unified pipeline: src/shorts_studio/queue/pipeline.py (process_source) is now the single
  code path for both `run` and `run-daily` (removed the divergent "minimal" copy). Rights
  status is now propagated from the registry into scoring (was hardcoded UNKNOWN, which
  made every rights-cleared source score 0 and need --allow-unverified).
- Speed: 15s/60fps source cold 48.7s vs 76.3s before (-36%); QC still PASS, h264/aac,
  1080x1920, 0 black segments.
- New tests: test_transcribe_cache.py (3), test_pipeline_gates.py (2). Full suite: 97 passed.

## Executed 2026-10-25 (licensed music + publish + beat-synced cuts)
- Generated 3 original royalty-free music tracks (beat/ambient/epic) + 4 SFX (whoosh/hit/pop/transition)
  with numpy; registered in music_library.json / sfx_library.json as permitted_use="publish".
- Kept Impact Prelude (CC-BY Kevin MacLeod) reference; CC0-equivalent original synthesis for the rest.
- select_music now prefers cleared (publish/internal) assets over test assets.
- status now reports "3 licensed / 4 registered" music and "4 licensed / 5 registered" SFX.
- Live publishing: `publish <job_id> --confirm-live` command with double gate (config dry_run:false
  AND --confirm-live). Tested with mocked publisher (no real API call). Refuses otherwise.
- Beat-synced internal cuts: optional `--beat-cuts` / config `editing.beat_synced_cuts`. Only splits
  at beats coinciding with silence gaps and not inside a spoken word. Default off.
- New tests: test_publish_and_beatcuts.py (4). Full suite: 101 passed.
