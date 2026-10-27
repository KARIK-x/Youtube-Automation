"""Transcription with faster-whisper -> SRT + ASS captions.

Speed matters here: transcription dominates a Short's render time on this machine.
Two caches keep repeat work near-zero:
  * the Whisper model is loaded once per (size, compute_type) and kept in memory;
  * transcripts are cached on disk, keyed by source size + mtime, so re-running the
    same source (or re-planning after a failed render) skips decoding entirely.
"""
import json, os, re
from pathlib import Path

_TRANSCRIPT_CACHE_VERSION = 2
_MODEL_CACHE = {}


class _Word:
    __slots__ = ("start", "end", "word", "probability")

    def __init__(self, start, end, word, probability=None):
        self.start, self.end = start, end
        self.word, self.probability = word, probability


class _Seg:
    """Duck-types faster_whisper.Segment closely enough for planner/selector."""
    __slots__ = ("start", "end", "text", "words")

    def __init__(self, start, end, text, words=None):
        self.start, self.end = start, end
        self.text = text
        self.words = words if words is not None else []


def _fmt_srt(t):
    h = int(t//3600); m = int((t%3600)//60); s = int(t%60); ms = int((t-int(t))*1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_ass(t):
    h = int(t//3600); m = int((t%3600)//60); s = int(t%60); cs = int((t-int(t))*100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def get_model(model_size="base", compute_type="int8"):
    """Load (and reuse) a WhisperModel. Reloading per call cost several seconds each."""
    key = (model_size, compute_type)
    model = _MODEL_CACHE.get(key)
    if model is None:
        from faster_whisper import WhisperModel
        threads = max(1, min(8, (os.cpu_count() or 4)))
        model = WhisperModel(model_size, device="cpu", compute_type=compute_type,
                             cpu_threads=threads)
        _MODEL_CACHE[key] = model
    return model


def clear_model_cache():
    _MODEL_CACHE.clear()


def _cache_path(work_dir, base, model_size):
    return os.path.join(work_dir, f"{base}.transcript.v{_TRANSCRIPT_CACHE_VERSION}.{model_size}.json")


def _load_cache(path, video_path, model_size):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if data.get("model") != model_size or data.get("version") != _TRANSCRIPT_CACHE_VERSION:
        return None
    st = os.stat(video_path)
    if data.get("source_size") != st.st_size or int(data.get("source_mtime", 0)) != int(st.st_mtime):
        return None
    segs = []
    for s in data.get("segments", []):
        words = [_Word(w[0], w[1], w[2], w[3] if len(w) > 3 else None) for w in s.get("words", [])]
        segs.append(_Seg(s["start"], s["end"], s["text"], words))
    return segs


def _save_cache(path, video_path, model_size, segs):
    st = os.stat(video_path)
    payload = {
        "version": _TRANSCRIPT_CACHE_VERSION,
        "model": model_size,
        "source_size": st.st_size,
        "source_mtime": st.st_mtime,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text,
             "words": [[w.start, w.end, w.word, getattr(w, "probability", None)]
                       for w in (s.words or [])]}
            for s in segs
        ],
    }
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, path)
    except OSError:
        pass


def transcribe(video_path, work_dir, model_size="base", use_cache=True):
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    base = Path(video_path).stem
    srt_path = os.path.join(work_dir, base + ".srt")
    ass_path = os.path.join(work_dir, base + ".ass")
    cache = _cache_path(work_dir, base, model_size)

    segs = _load_cache(cache, video_path, model_size) if use_cache else None
    if segs is None:
        model = get_model(model_size)
        segments, info = model.transcribe(video_path, beam_size=5, word_timestamps=True,
                                          vad_filter=True)
        segs = list(segments)
        if use_cache:
            _save_cache(cache, video_path, model_size, segs)

    # SRT
    with open(srt_path, "w") as f:
        for i, seg in enumerate(segs, 1):
            f.write(f"{i}\n{_fmt_srt(seg.start)} --> {_fmt_srt(seg.end)}\n{seg.text.strip()}\n\n")
    # ASS with word-level highlighting (karaoke-ish)
    write_ass(ass_path, segs)
    return srt_path, ass_path, segs

def write_ass(ass_path, segs, font="Impact", size=72, color="&H00FFFFFF", highlight="&H0000FFFF"):
    header = f"""[Script Info]
Title: captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{color},{highlight},&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,2,2,40,40,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for seg in segs:
        words = getattr(seg, "words", None) or []
        if not words:
            # fall back to segment-level
            lines.append(f"Dialogue: 0,{_fmt_ass(seg.start)},{_fmt_ass(seg.end)},Default,,0,0,0,,{seg.text.strip()}")
            continue
        # Build karaoke text: highlight current word via \k tags
        parts = []
        for w in words:
            dur = max(1, int((w.end - w.start)*100))
            parts.append(f"{{\\k{dur}}}{w.word.strip()}")
        text = " ".join(parts)
        lines.append(f"Dialogue: 0,{_fmt_ass(seg.start)},{_fmt_ass(seg.end)},Default,,0,0,0,,{text}")
    with open(ass_path, "w") as f:
        f.write("\n".join(lines))
