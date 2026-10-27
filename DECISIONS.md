# DECISIONS

- Primary engine: FFmpeg (deterministic, headless, free).
- Transcription: faster-whisper (cpu int8, av 12.3.0).
- TTS: edge-tts (free) for original mode.
- Face crop: OpenCV Haar cascades (basic; upgrade path to MediaPipe).
- Captions: Python burn (no libass in ffmpeg build).
- DB: SQLite.
- Publishing: dry-run by default; no uploads in tests.
- Source: user-provided authorized media only; no scraping.
- No CapCut MCP in automated path (experimental only).
