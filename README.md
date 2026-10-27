# Shorts Studio

**AI-powered YouTube Shorts production pipeline.** Discover viral clips, edit them into professional 10–60s vertical videos, generate SEO metadata, and publish — all from one command.

Built for **KARIKKKSHORTS** (1890 subs, 141 videos). Runs on macOS (M1 8GB) with Python 3.10+.

## ✨ Features

- **One-command agent**: `shorts agent "IShowSpeed funny" --auto` — searches YouTube, scores viral potential, downloads, edits, generates SEO, delivers the final video.
- **Professional editing**: face-tracking 9:16 crop, word-level karaoke captions with emphasis highlighting, licensed music + SFX mixing, beat-synced zooms, beat-synced internal cuts (opt-in), hook title overlay, sharpen/contrast.
- **Long-form production**: genuine 5–10 minute videos with original graphics, crossfade transitions, synced captions, chapters, thumbnail + metadata.
- **Licensed asset library**: 58 music tracks + 185 SFX (Mixkit royalty-free + original synthesis), mood-matched selection.
- **SEO metadata**: LLM-generated title/description/tags/hashtags (OpenAI/Anthropic/Gemini) with template fallback.
- **Quality control**: automated QC (dimensions, duration, black frames, audio levels, sync). Human approval gate before publish.
- **Dashboard**: web UI at `http://127.0.0.1:8765` with 7 pages (overview, discover, studio, queue, library, analytics, settings).
- **Trend discovery**: Reddit, Hacker News, Google Trends, YouTube RSS, Pexels stock, local files.
- **Safety**: rights gate, scoring gate, duplicate detection, min-score enforcement, output collision protection, dry-run publishing default.
- **Performance**: -36% render time via ffmpeg rawvideo pipe + caption cache. Transcription cache (model reuse + disk cache).

## 🚀 Quick start

```bash
# 1. Clone
git clone https://github.com/KARIK-x/Youtube-Automation.git
cd Youtube-Automation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Check environment
shorts check-deps

# 4. Run the dashboard
shorts dashboard
# Open http://127.0.0.1:8765
```

### One-command viral short

```bash
shorts agent "IShowSpeed funny moments" --auto
```

This searches YouTube, scores clips by viral potential, downloads the best one, edits it into a Short, generates SEO metadata + thumbnail, and delivers the final video.

## 📋 Commands

| Command | Description |
|---|---|
| `shorts agent "query" --auto` | Find viral clip → edit → deliver (one command) |
| `shorts run --profile chaos` | Edit all sources in `data/content/sources/` |
| `shorts run-daily --dry-run` | Plan today's workload |
| `shorts status` | Live capability report (OAuth, assets, jobs, disk) |
| `shorts dashboard` | Start web dashboard (port 8765) |
| `shorts discover --adapter reddit` | Find viral Reddit clips |
| `shorts discover --adapter hackernews` | Find trending HN stories |
| `shorts search-stock --query "..." --download` | Download free Pexels stock video |
| `shorts download-url <url>` | Download from any URL (TikTok, YT, etc.) |
| `shorts gen-metadata --source video.mp4` | Generate SEO title/desc/tags |
| `shorts gen-video --provider kling --prompt "..."` | AI video gen (needs paid key) |
| `shorts approve <job_id>` | Human approval for a job |
| `shorts publish <job_id> --confirm-live` | Publish (needs `dry_run: false`) |
| `shorts check-deps` | Verify environment |
| `shorts jobs` | List jobs |
| `shorts qc <path>` | Quality check a video |

## ⚙️ Configuration

Edit `config.yaml`:
- `youtube.dry_run: true` (keep true until ready to publish)
- `candidate.min_score: 0.1` (minimum candidate score)
- `profiles.default: chaos` (editing profile)
- `editing.beat_synced_cuts: false` (opt-in beat cuts)
- `audio.music_library_dir` / `sfx_library_dir`

### Optional API keys (env vars or config.yaml)
- `PEXELS_API_KEY` — free stock video (https://www.pexels.com/api/)
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` — SEO metadata generation
- `KLING_ACCESS_KEY` / `KLING_SECRET_KEY` — AI video generation (paid)
- `HIGGSFIELD_API_KEY` — AI video generation (paid)

## 🧪 Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -q
```

101+ tests pass. Covers: EDL validation, DB lifecycle, QC, rendering, crop, audio, TTS, scoring, publishing, status, launcher, transcription cache, pipeline gates, long-form.

## 📁 Project structure

```
shorts_studio/
├── src/shorts_studio/
│   ├── cli/           # CLI commands (main.py)
│   ├── core/          # DB, scoring, rights, output safety, publish gate, config
│   ├── editing/       # planner, renderer, qc, profiles, sfx, beat_sync, moment_selector
│   ├── media/         # transcribe, audio_analysis, scene_detect, thumbnail, discovery,
│   │                  # tts, tts_interface, music_library, stock_video, ai_video, seo,
│   │                  # viral_finder, trend_discovery
│   ├── longform/      # prototype.py (genuine 5-10 min production)
│   ├── queue/         # runner.py, pipeline.py
│   ├── youtube/       # publishing (dry-run), analytics
│   └── dashboard/     # web UI (server.py + static/index.html)
├── tests/             # 30 test files, 101+ tests
├── config.yaml        # configuration
├── shorts             # launcher script (works from any folder)
├── gen_audio.py       # generate original music/SFX
├── download_mixkit.py # download Mixkit SFX
├── download_mixkit_music.py  # download Mixkit music
└── data/
    ├── audio_library/ # music + SFX (gitignored, regenerable)
    ├── content/sources/ # input videos
    ├── output/        # rendered videos (gitignored)
    └── work/          # intermediate files (gitignored)
```

## 🔒 Safety

- **Publishing is dry-run by default.** No uploads happen unless you explicitly flip `youtube.dry_run: false` AND pass `--confirm-live`.
- **Secrets are gitignored.** `secrets/` (OAuth tokens) never committed.
- **Output collision protection.** Files are never silently overwritten (suffix on collision).
- **Rights gate.** Sources without verified rights are blocked (use `--allow-unverified` for local testing only).
- **Human approval required** before any publish.
- **`~/yt-auto` is never touched.**

## 📊 Performance (M1 MacBook Air, 8GB)

| Task | Time |
|---|---|
| 15s Short (60fps) | ~50s (was 76s, -36%) |
| 5-min long-form | ~5 min |
| Full test suite (101 tests) | ~3 min |

## 📝 License

MIT — see [LICENSE](LICENSE).

## 🙏 Credits

- [Mixkit](https://mixkit.co) — royalty-free SFX and music
- [Pexels](https://pexels.com) — free stock video
- [Edge TTS](https://github.com/rany2/edge-tts) — free text-to-speech
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — transcription
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — video download
- Various open-source repos that inspired the architecture (see research notes)