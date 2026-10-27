"""Generate a large original, royalty-free music + SFX library.

Target aesthetic: high-energy "clipping" (IShowSpeed / Kai Cenat style) — fast BPM,
aggressive drums, heavy bass, meme-y SFX (airhorn, vine boom, hits, whooshes).

Everything is synthesized from scratch with numpy — no external samples, no
third-party copyright. All tracks registered as permitted_use="publish".
"""
import json
import numpy as np
from pathlib import Path
from scipy.io import wavfile

SR = 44100
ROOT = Path(__file__).resolve().parent
LIB = ROOT / "data" / "audio_library"
SFX = LIB / "sfx"
LIB.mkdir(parents=True, exist_ok=True)
SFX.mkdir(parents=True, exist_ok=True)


def write_wav(path, audio, sr=SR):
    audio = np.asarray(audio, dtype=np.float32)
    peak = np.max(np.abs(audio)) if audio.size else 1.0
    if peak > 0:
        audio = audio / peak * 0.88
    wavfile.write(str(path), sr, (audio * 32767).astype(np.int16))
    print(f"  wrote {path.name} ({len(audio)/sr:.1f}s)")


def env_decay(n, attack=0.001, decay=0.15):
    t = np.arange(n) / SR
    e = np.exp(-t / decay)
    a = int(attack * SR)
    if a > 0:
        e[:a] *= np.linspace(0, 1, a)
    return e.astype(np.float32)


def kick(dur=0.25, pitch=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = (120 * pitch) * np.exp(-t * 30) + (40 * pitch)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * env_decay(n, 0.001, 0.08)
    click = np.random.randn(n).astype(np.float32) * env_decay(n, 0.0005, 0.01) * 0.3
    return (body + click).astype(np.float32)


def snare(dur=0.2):
    n = int(dur * SR)
    noise = np.random.randn(n).astype(np.float32)
    return (noise * env_decay(n, 0.001, 0.12)).astype(np.float32)


def hat(dur=0.06, bright=1.0):
    n = int(dur * SR)
    noise = np.random.randn(n).astype(np.float32)
    hp = np.diff(noise, prepend=noise[0])
    return (hp * env_decay(n, 0.0005, 0.03) * 0.5 * bright).astype(np.float32)


def bass_note(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2*np.pi*freq*t) + 0.5*np.sin(2*np.pi*freq*2*t)
         + 0.25*np.sin(2*np.pi*freq*3*t))
    return (x * env_decay(n, 0.005, dur*0.9) * 0.6).astype(np.float32)


def pad_chord(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for f in freqs:
        x += np.sin(2*np.pi*f*t) + 0.3*np.sin(2*np.pi*f*2*t)
    swell = 0.5 + 0.5*np.sin(2*np.pi*0.1*t)
    return (x * swell * env_decay(n, 0.3, dur*1.2) * 0.25).astype(np.float32)


def mix_layers(layers, total_len):
    out = np.zeros(total_len, dtype=np.float32)
    for arr, start in layers:
        if start >= total_len or start < 0:
            continue
        arr = np.asarray(arr, dtype=np.float32)
        end = start + len(arr)
        if end > total_len:
            arr = arr[:total_len - start]
            end = total_len
        if len(arr) == 0:
            continue
        out[start:end] += arr
    return out


def make_track(duration=45.0, bpm=140, key=0.0, style="beat", mood="hype"):
    """Parameterized track generator. style: beat|ambient|epic|trap|drill."""
    total = int(duration * SR)
    beat = 60.0 / bpm
    sixteenth = beat / 4.0
    root = 55.0 * (2 ** (key / 12.0))
    fifth = root * 1.5
    layers = []
    if style in ("beat", "trap", "drill"):
        t = 0.0
        bar = 0
        while t < duration - beat:
            s = int(t * SR)
            layers.append((kick(0.2, 1.0 if style != "drill" else 0.8), s))
            layers.append((hat(0.05, 1.2), s))
            layers.append((hat(0.05, 1.0), s + int(sixteenth*2*SR)))
            s2 = int((t + beat) * SR)
            if style != "drill":
                layers.append((snare(), s2))
            layers.append((hat(0.05, 1.0), s2))
            layers.append((hat(0.05, 0.9), s2 + int(sixteenth*2*SR)))
            layers.append((bass_note(root, beat*0.9), s))
            if style in ("trap", "drill"):
                layers.append((bass_note(root*0.5, beat*0.9) * 0.9, int((t+2*beat)*SR)))
            else:
                layers.append((bass_note(fifth, beat*0.9), int((t+2*beat)*SR)))
            if bar % 2 == 0:
                chord = [root*4, root*4*1.25, root*4*1.5]
                layers.append((pad_chord(chord, beat*4) * (0.9 if style=="epic" else 0.7), s))
            t += 4 * beat
            bar += 1
    elif style == "ambient":
        layers.append((pad_chord([root*4, root*4*1.25, root*4*1.5, root*8], duration), 0))
        layers.append((pad_chord([root*3.5, root*4*1.1, root*4*1.4], duration), int(duration/2*SR)))
        tt = 0.0
        while tt < duration:
            s = int(tt * SR)
            layers.append((bass_note(root*0.5, (60/bpm)*0.8) * 0.3, s))
            tt += (60/bpm) * 2
    elif style == "epic":
        t = 0.0
        bar = 0
        beat = 60.0 / bpm
        while t < duration - 4*beat:
            s = int(t * SR)
            layers.append((kick(0.22, 1.3), s))
            layers.append((snare() * 1.1, int((t+beat)*SR)))
            layers.append((kick(0.22, 1.3), int((t+2*beat)*SR)))
            layers.append((snare() * 1.1, int((t+3*beat)*SR)))
            for i in range(8):
                layers.append((hat(0.04, 1.3), int((t + i*beat/2)*SR)))
            layers.append((bass_note(root, beat*0.95) * 1.2, s))
            layers.append((bass_note(root, beat*0.95) * 1.2, int((t+2*beat)*SR)))
            if bar % 2 == 0:
                layers.append((pad_chord([root*2, root*2*1.25, root*2*1.5, root*4], beat*4) * 1.3, s))
            t += 4*beat
            bar += 1
    return mix_layers(layers, total)


# ---------- SFX generators ----------
def sfx_whoosh(dur=0.4, low=200, high=2000):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.random.randn(n).astype(np.float32)
    f = low + (high-low)*(t/(n/SR))
    sweep = np.sin(2*np.pi*np.cumsum(f)/SR)
    env = env_decay(n, 0.02, dur*0.4)
    return ((noise*0.3 + sweep*0.7) * env).astype(np.float32)


def sfx_hit():
    n = int(0.25 * SR)
    k = kick(0.12, 1.2)
    out = np.zeros(n, dtype=np.float32)
    out[:len(k)] = k
    s = snare()[:min(len(snare()), n-len(k))]
    out[len(k):len(k)+len(s)] += s * 0.7
    return out * env_decay(n, 0.001, 0.1)


def sfx_pop(pitch=1.0):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = (600*pitch) * np.exp(-t*20) + (200*pitch)
    phase = 2*np.pi*np.cumsum(f)/SR
    return (np.sin(phase) * env_decay(n, 0.001, 0.05) * 0.8).astype(np.float32)


def sfx_transition(dur=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 300 + 2000 * (t / (n/SR))
    phase = 2*np.pi*np.cumsum(f)/SR
    env = np.linspace(0.2, 1.0, n) * env_decay(n, 0.01, 0.3)
    return (np.sin(phase) * env * 0.7).astype(np.float32)


def sfx_airhorn():
    n = int(0.8 * SR)
    t = np.arange(n) / SR
    # chord: F5, A5, C6
    freqs = [698.5, 880.0, 1046.5]
    x = np.zeros(n, dtype=np.float32)
    for f in freqs:
        x += np.sin(2*np.pi*f*t) * 0.3
    # saw-ish
    for f in freqs:
        x += (2*( (f*t) % 1) - 1) * 0.15
    env = np.ones(n, dtype=np.float32)
    env[:int(0.02*SR)] = np.linspace(0, 1, int(0.02*SR))
    env[-int(0.15*SR):] = np.linspace(1, 0, int(0.15*SR))
    return (x * env * 0.6).astype(np.float32)


def sfx_vine_boom():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    # deep sine drop
    f = 120 * np.exp(-t*4) + 30
    phase = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(phase) * env_decay(n, 0.001, 0.4) * 1.2
    # add a click
    click = np.zeros(n, dtype=np.float32)
    click[:int(0.01*SR)] = np.random.randn(int(0.01*SR)) * 0.5
    return (body + click).astype(np.float32)


def sfx_riser(dur=1.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 200 + 3000 * (t / (n/SR))**2
    phase = 2*np.pi*np.cumsum(f)/SR
    env = np.linspace(0.1, 1.0, n) * env_decay(n, 0.05, dur*2)
    noise = np.random.randn(n).astype(np.float32) * 0.2
    return ((np.sin(phase) + noise) * env * 0.6).astype(np.float32)


def sfx_drop():
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    # bass drop: sine sweep down + sub
    f = 200 * np.exp(-t*6) + 40
    phase = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(phase) * (1 - np.exp(-t*8)) * env_decay(n, 0.001, 0.5)
    # impact
    imp = kick(0.15, 0.7)
    out = np.zeros(n, dtype=np.float32)
    out[:len(imp)] += imp * 1.3
    out += body * 0.8
    return out.astype(np.float32)


def sfx_click():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return (np.sin(2*np.pi*1200*t) * env_decay(n, 0.0005, 0.015) * 0.6).astype(np.float32)


def sfx_glitch():
    n = int(0.18 * SR)
    out = np.zeros(n, dtype=np.float32)
    # stuttered bursts
    pos = 0
    while pos < n:
        chunk = np.random.randint(20, 80)
        if pos + chunk > n:
            chunk = n - pos
        burst = np.random.randn(chunk).astype(np.float32) * np.random.uniform(0.3, 1.0)
        out[pos:pos+chunk] = burst
        pos += chunk + np.random.randint(10, 60)
    return (out * env_decay(n, 0.001, 0.1)).astype(np.float32)


def sfx_ding():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 880.0
    x = np.sin(2*np.pi*f*t) + 0.5*np.sin(2*np.pi*f*2*t) + 0.25*np.sin(2*np.pi*f*3*t)
    return (x * env_decay(n, 0.001, 0.2) * 0.5).astype(np.float32)


def sfx_sweep_up():
    return sfx_whoosh(0.5, 300, 3500)


def sfx_sweep_down():
    return sfx_whoosh(0.5, 3500, 300)


def sfx_impact_heavy():
    n = int(0.4 * SR)
    k = kick(0.18, 0.6)
    out = np.zeros(n, dtype=np.float32)
    out[:len(k)] += k * 1.5
    # low boom
    t = np.arange(n) / SR
    boom = np.sin(2*np.pi*45*t) * env_decay(n, 0.001, 0.3) * 0.8
    out += boom
    return out.astype(np.float32)


def sfx_sparkle():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for f in (2000, 2500, 3000, 3500, 4000):
        x += np.sin(2*np.pi*f*t) * np.random.uniform(0.1, 0.25)
    return (x * env_decay(n, 0.01, 0.2)).astype(np.float32)


def sfx_down():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 800 - 600*(t/(n/SR))
    phase = 2*np.pi*np.cumsum(f)/SR
    return (np.sin(phase) * env_decay(n, 0.01, 0.2) * 0.6).astype(np.float32)


def sfx_boom():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = np.sin(2*np.pi*40*t) * env_decay(n, 0.001, 0.35) * 1.2
    noise = np.random.randn(n).astype(np.float32) * env_decay(n, 0.001, 0.08) * 0.4
    return (x + noise).astype(np.float32)


# ============================================================
print("Generating music tracks...")
music_specs = [
    ("beat", 128, 0, "hype"), ("beat", 140, 2, "hype"), ("beat", 150, -2, "hype"),
    ("beat", 135, 5, "hype"), ("beat", 160, -5, "hype"),
    ("trap", 140, 0, "hype"), ("trap", 150, 3, "hype"), ("trap", 130, -3, "hype"),
    ("drill", 145, 0, "tense"), ("drill", 155, -2, "tense"),
    ("epic", 140, 0, "epic"), ("epic", 120, 5, "epic"), ("epic", 150, -3, "epic"),
    ("ambient", 72, 0, "soft"), ("ambient", 80, -2, "soft"), ("ambient", 68, 3, "soft"),
    ("beat", 120, 7, "energetic"), ("beat", 145, -7, "energetic"),
]
music_tracks = []
for i, (style, bpm, key, mood) in enumerate(music_specs):
    dur = 45.0 if style != "ambient" else 60.0
    name = f"music_{style}_{i:02d}.wav"
    write_wav(LIB / name, make_track(dur, bpm, key, style, mood))
    music_tracks.append({"path": f"data/audio_library/{name}",
        "title": f"Original {style.title()} {i:02d} ({bpm}bpm)",
        "mood": mood, "bpm": bpm,
        "license": "original-synthesis (author-generated, no third-party copyright)",
        "source": "generated-locally", "permitted_use": "publish",
        "attribution": "none required"})

# keep test track
existing = json.loads((LIB / "music_library.json").read_text()).get("tracks", [])
existing = [t for t in existing if "Original" not in t.get("title", "")
            and "Impact Prelude" not in t.get("title", "")
            and "Synthetic test" not in t.get("title", "")]
music_tracks = existing + music_tracks
if (LIB / "Impact Prelude.mp3").exists():
    music_tracks.append({"path": "data/audio_library/Impact Prelude.mp3",
        "title": "Impact Prelude (Kevin MacLeod)", "mood": "epic",
        "license": "CC-BY 4.0", "source": "incompetech.com",
        "permitted_use": "publish",
        "attribution": "Impact Prelude by Kevin MacLeod (incompetech.com) — CC-BY 4.0"})
# keep synthetic test track for backward compat
music_tracks.append({"path": "data/audio_library/test_music.wav",
    "title": "Synthetic test music", "mood": "hype",
    "license": "synthetic-test-only", "source": "generated-locally",
    "permitted_use": "test"})
(LIB / "music_library.json").write_text(json.dumps({"tracks": music_tracks}, indent=2))

# ============================================================
print("\nGenerating SFX...")
sfx_generators = {
    "whoosh": lambda: sfx_whoosh(0.4, 200, 2000),
    "whoosh_short": lambda: sfx_whoosh(0.2, 400, 2500),
    "whoosh_long": lambda: sfx_whoosh(0.7, 150, 1800),
    "whoosh_reverse": lambda: sfx_whoosh(0.4, 2000, 200)[::-1].copy(),
    "whoosh_high": lambda: sfx_whoosh(0.3, 1000, 4000),
    "whoosh_low": lambda: sfx_whoosh(0.5, 100, 800),
    "hit": lambda: sfx_hit(),
    "hit_heavy": lambda: sfx_impact_heavy(),
    "hit_soft": lambda: sfx_hit() * 0.5,
    "pop": lambda: sfx_pop(1.0),
    "pop_high": lambda: sfx_pop(1.5),
    "pop_low": lambda: sfx_pop(0.7),
    "pop_double": lambda: np.concatenate([sfx_pop(1.0), np.zeros(int(0.05*SR)), sfx_pop(1.3)]),
    "transition": lambda: sfx_transition(0.6),
    "transition_fast": lambda: sfx_transition(0.3),
    "transition_slow": lambda: sfx_transition(1.0),
    "airhorn": lambda: sfx_airhorn(),
    "airhorn_short": lambda: sfx_airhorn()[:int(0.4*SR)],
    "airhorn_long": lambda: sfx_airhorn(),
    "vine_boom": lambda: sfx_vine_boom(),
    "vine_boom_short": lambda: sfx_vine_boom()[:int(0.5*SR)],
    "vine_boom_deep": lambda: sfx_vine_boom() * 0.9,
    "riser": lambda: sfx_riser(1.2),
    "riser_short": lambda: sfx_riser(0.6),
    "riser_long": lambda: sfx_riser(2.0),
    "riser_fast": lambda: sfx_riser(0.4),
    "drop": lambda: sfx_drop(),
    "drop_heavy": lambda: sfx_drop() * 1.2,
    "click": lambda: sfx_click(),
    "click_double": lambda: np.concatenate([sfx_click(), np.zeros(int(0.05*SR)), sfx_click()]),
    "click_triple": lambda: np.concatenate([sfx_click(), np.zeros(int(0.04*SR)), sfx_click(), np.zeros(int(0.04*SR)), sfx_click()]),
    "glitch": lambda: sfx_glitch(),
    "glitch_short": lambda: sfx_glitch()[:int(0.1*SR)],
    "glitch_long": lambda: sfx_glitch() * 1.0,
    "ding": lambda: sfx_ding(),
    "ding_double": lambda: np.concatenate([sfx_ding(), np.zeros(int(0.1*SR)), sfx_ding()]),
    "sweep_up": lambda: sfx_sweep_up(),
    "sweep_down": lambda: sfx_sweep_down(),
    "sweep_fast_up": lambda: sfx_whoosh(0.25, 500, 4000),
    "sweep_fast_down": lambda: sfx_whoosh(0.25, 4000, 500),
    "impact_heavy": lambda: sfx_impact_heavy(),
    "impact_soft": lambda: sfx_impact_heavy() * 0.5,
    "sparkle": lambda: sfx_sparkle(),
    "sparkle_short": lambda: sfx_sparkle()[:int(0.25*SR)],
    "down": lambda: sfx_down(),
    "down_fast": lambda: sfx_down()[:int(0.25*SR)],
    "boom": lambda: sfx_boom(),
    "boom_deep": lambda: sfx_boom() * 1.1,
    "whoosh_mid": lambda: sfx_whoosh(0.35, 500, 2500),
    "hit_mid": lambda: sfx_hit() * 0.8,
    "pop_mid": lambda: sfx_pop(1.2),
    "riser_mid": lambda: sfx_riser(0.8),
    "transition_mid": lambda: sfx_transition(0.45),
    "glitch_mid": lambda: sfx_glitch()[:int(0.12*SR)],
    "ding_high": lambda: sfx_ding() * 0.9,
}
# generate ~50+ by also creating pitched variants of core types
extra = {}
for nm in ("whoosh", "pop", "hit"):
    for i in range(3):
        def _make(nm=nm, i=i):
            base = {"whoosh": lambda: sfx_whoosh(0.4, 200, 2000),
                    "pop": lambda: sfx_pop(1.0),
                    "hit": lambda: sfx_hit()}[nm]()
            return base * (0.8 + 0.1*i)
        extra[f"{nm}_v{i+1}"] = _make
sfx_generators.update(extra)

sfx_tracks = []
for name, gen in sfx_generators.items():
    path = SFX / f"sfx_{name}.wav"
    try:
        write_wav(path, gen())
    except Exception as e:
        print(f"  FAILED {name}: {e}")
        continue
    sfx_tracks.append({"path": f"data/audio_library/sfx/sfx_{name}.wav",
        "title": f"SFX {name}", "mood": "sfx",
        "license": "original-synthesis (author-generated, no third-party copyright)",
        "source": "generated-locally", "permitted_use": "publish",
        "attribution": "none required"})

# keep test sfx
existing_sfx = json.loads((SFX.parent / "sfx_library.json").read_text()).get("tracks", [])
existing_sfx = [t for t in existing_sfx if "SFX" not in t.get("title", "")]
sfx_tracks = existing_sfx + sfx_tracks
(SFX.parent / "sfx_library.json").write_text(json.dumps({"tracks": sfx_tracks}, indent=2))

print(f"\nDone. Library now has {len(music_tracks)} music and {len(sfx_tracks)} sfx tracks.")
