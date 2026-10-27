# CURRENT_PROJECT_STATE

**Source of truth:** `shorts status`
It probes the live token, config, tooling and job DB. Never trust prose here over that command.

Last reconciled: 2026-10-25.

---

## YouTube OAuth — DONE (verified live)

| Item | State |
|---|---|
| `secrets/client_secret.json` | present, perms `600` |
| `secrets/token.json` | present, perms `600`, refresh token stored |
| Granted scopes | `youtube.upload`, `youtube`, `yt-analytics.readonly` |
| Live read check | channel **Karikkkshorts** — 1890 subs, 141 videos |
| Analytics read | working (real numbers, no fabricated data) |
| Publishing mode | **DRY RUN** (`youtube.dry_run: true`) — uploads refused by design |

OAuth is **not** a blocker. Earlier phase reports saying "no OAuth" are stale history and are
now marked with a superseded banner.

## What works today

- **Shorts pipeline**: source → transcribe → audio/beat analysis → scene detect → candidate
  moment scoring → profile planning → EDL validation → render (1080x1920, captions burned,
  music+SFX mix, beat-synced zooms) → QC → thumbnail → `READY_FOR_REVIEW`.
- **Long-form**: script generation + Edge TTS narration + title card + caption chunks +
  chapters file + `qc_longform`, renders ≥5 min at 1080x1920.
- **Safety gates**: rights hard gate, NaN/inf-safe candidate scoring, min-score gate,
  duplicate detection, output non-overwrite (`unique_path`), human-approval gate,
  publish-readiness gate.
- **Discovery**: local, RSS, Data API, Google Trends adapters; `discover-auto` ranks and
  stores opportunities.
- **Publishing**: `publish-dryrun` exercises metadata + thumbnail + privacy with no upload.
- **CLI**: `status`, `check-deps`, `inspect`, `analyze`, `plan`, `validate`, `render`, `qc`,
  `jobs`, `run`, `thumbnail`, `discover`, `discover-auto`, `publish-dryrun`, `approve`,
  `daily-plan`, `run-daily`, `auth`.

## Known limitations (honest list)

- **No licensed music/SFX.** Only 2 test-only assets; shorts fall back to source dialogue.
  Mixer is wired and validated with synthetic assets.
- **Publishing is dry-run only** by configuration. Real upload path exists but is untested
  against the live API — intentionally, until you approve.
- **Beat-synced internal cuts** are deliberately not implemented (they cut dialogue
  mid-sentence). Beat-synced *zooms* and boundary snapping are implemented.
- **Long-form** is narration + title cards + captions over a branded background; it is not a
  B-roll edit and has no scene-graph QC.
- **TikTok discovery** has no authorized free API.
- **Speed**: a ~22 s 60 fps source takes roughly 2 min on this M1/8 GB machine, dominated by
  transcription.

## Verification commands

```bash
shorts status              # live truth (works from any directory)
shorts status --offline    # no network call
shorts check-deps          # ffmpeg / python modules / av pin
cd "<project>" && PYTHONPATH=src python3 -m pytest tests/ -q   # full suite
```

If `shorts` isn't found, `~/.local/bin` is missing from PATH, or the symlink was removed:

```bash
ln -sf "/Users/ashim/Downloads/ai automation OPENCODE/shorts_studio/shorts" ~/.local/bin/shorts
```
