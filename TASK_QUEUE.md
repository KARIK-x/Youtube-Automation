# TASK_QUEUE

## Done (Phases 0-15)
- [x] Research + blueprint deliverables
- [x] Shorts pipeline v0.1 (render + QC verified)
- [x] Audio analysis, scene detection, moment selector
- [x] 5 editing profiles with distinct decisions
- [x] Caption keyword emphasis
- [x] Beat sync helpers + music library + audio mixer + SFX
- [x] Thumbnail CLI + integrated into cmd_run
- [x] Rights registry, opportunity schema, duplicate detection, scoring
- [x] Source discovery adapters
- [x] YouTube publishing adapter (dry-run)
- [x] Analytics adapter (interface)
- [x] Long-form design doc + prototype (5.6min verified)
- [x] Safety gate in cmd_run
- [x] Daily job runner (daily-plan, run-daily, dry-run, recovery)
- [x] Beat-synced trim in renderer
- [x] Output safety (unique_path, atomic_copy)
- [x] Candidate scoring enforcement (partial)
- [x] Human-approval gate (persistent)
- [x] Publish-readiness gate
- [x] 51 tests pass

## Done (Phase 16)
- [x] Publishing integration tests (4 pass)
- [x] 55 tests pass (132.4s)
- [x] Long-form prototype enhanced (title card + chapters)
- [x] qc_longform added

## Next (Phase 17)
- [x] Beat-synced **zooms** + boundary snapping (internal cuts intentionally skipped — they break dialogue)
- [ ] Licensed music (replace synthetic test assets) — needs you to pick a library or supply files
- [x] YouTube publishing adapter integration tests (dry-run — test_publishing_integration)
- [x] Human review gate before publish (core/publish_gate.py + tests)
- [x] Candidate scoring hard block below threshold (min_score + rights hard gate)
- [x] Analytics collection — **OAuth done, read-only analytics verified** (Karikkkshorts, real numbers)
- [ ] Long-form full pipeline (real visuals, B-roll, chapters)
- [x] Trend discovery automation (`discover-auto`, run in daily flow)