"""Lightweight audio analysis (no librosa). Uses scipy + numpy."""
import os, json, subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft, find_peaks

def load_audio(path):
    """Return (samples float32 mono, sr). Converts via ffmpeg if needed."""
    if path.lower().endswith(".wav"):
        sr, data = wavfile.read(path)
    else:
        # convert with ffmpeg to wav
        tmp = path + ".analysis.wav"
        subprocess.run(["ffmpeg","-y","-i",path,"-vn","-ac","1","-ar","22050",tmp],
                       capture_output=True, check=True)
        sr, data = wavfile.read(tmp)
        try: os.remove(tmp)
        except OSError: pass
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float32)
    if data.dtype == np.int16:
        data = data / 32768.0
    elif data.dtype == np.int32:
        data = data / 2147483648.0
    return data, sr

def rms_energy(samples, sr, frame_ms=50):
    frame = int(sr * frame_ms / 1000)
    if frame < 1: frame = 1
    n = len(samples) // frame
    if n == 0:
        return np.array([]), frame
    trimmed = samples[:n*frame].reshape(n, frame)
    rms = np.sqrt(np.mean(trimmed**2, axis=1) + 1e-12)
    return rms, frame

def detect_clipping(samples, threshold=0.99):
    n = int(np.sum(np.abs(samples) >= threshold))
    return {"clipping": n > 0, "clipped_samples": n, "ratio": n / max(1, len(samples))}

def detect_silence(samples, sr, threshold_db=-40, min_dur=0.3):
    rms, frame = rms_energy(samples, sr, 50)
    if len(rms) == 0:
        return []
    thr = 10**(threshold_db/20.0)
    silent = rms < thr
    # group
    out = []
    i = 0
    while i < len(silent):
        if silent[i]:
            j = i
            while j < len(silent) and silent[j]:
                j += 1
            dur = (j - i) * (frame / sr)
            if dur >= min_dur:
                out.append({"start": round(i*frame/sr,3), "end": round(j*frame/sr,3), "duration": round(dur,3)})
            i = j
        else:
            i += 1
    return out

def onset_detection(samples, sr):
    """Spectral-flux onset detection. Returns onset times (seconds)."""
    f, t, Zxx = stft(samples, fs=sr, nperseg=1024, noverlap=512)
    mag = np.abs(Zxx)
    flux = np.sum(np.diff(mag, axis=1).clip(min=0), axis=0)
    if len(flux) == 0:
        return []
    # normalize
    flux = flux - np.mean(flux)
    flux = flux / (np.std(flux) + 1e-9)
    # peak pick
    peaks, _ = find_peaks(flux, height=0.5, distance=max(1, int(0.1 * sr / 512)))
    times = [round(float(t[i+1]), 3) for i in peaks if i+1 < len(t)]
    return times

def beat_detection(samples, sr):
    """Estimate beat times via autocorrelation of onset envelope. Returns (bpm, [beat_times])."""
    onsets = onset_detection(samples, sr)
    if len(onsets) < 4:
        return {"bpm": None, "beats": [], "onsets": onsets}
    # build onset envelope at 100 Hz
    env_sr = 100
    n = int(len(samples) / sr * env_sr)
    env = np.zeros(n)
    for o in onsets:
        idx = int(o * env_sr)
        if 0 <= idx < n:
            env[idx] += 1.0
    # smooth
    kernel = np.ones(5) / 5
    env = np.convolve(env, kernel, mode="same")
    # autocorrelation
    ac = np.correlate(env - env.mean(), env - env.mean(), mode="full")
    ac = ac[len(ac)//2:]
    # find first major peak after min lag (60 bpm = 1.0s -> 100 samples; 180 bpm -> 33 samples)
    min_lag = int(env_sr * 60 / 180)  # 33
    max_lag = int(env_sr * 60 / 60)   # 100
    if max_lag >= len(ac):
        max_lag = len(ac) - 1
    segment = ac[min_lag:max_lag+1]
    if len(segment) == 0:
        return {"bpm": None, "beats": [], "onsets": onsets}
    lag = int(np.argmax(segment)) + min_lag
    bpm = 60.0 * env_sr / lag
    # generate beat grid aligned to first onset
    first = onsets[0]
    beats = []
    t = first
    dur = len(samples) / sr
    while t < dur:
        beats.append(round(float(t), 3))
        t += 60.0 / bpm
    return {"bpm": round(float(bpm), 2), "beats": beats, "onsets": onsets}

def analyze(path):
    samples, sr = load_audio(path)
    onsets = onset_detection(samples, sr)
    beats = beat_detection(samples, sr)
    silence = detect_silence(samples, sr)
    clip = detect_clipping(samples)
    rms, frame = rms_energy(samples, sr)
    energy_mean = float(np.mean(rms)) if len(rms) else 0.0
    energy_peak = float(np.max(rms)) if len(rms) else 0.0
    return {
        "sample_rate": sr,
        "duration": round(len(samples)/sr, 3),
        "onsets": onsets,
        "onset_count": len(onsets),
        "beats": beats["beats"],
        "bpm": beats["bpm"],
        "silence": silence,
        "clipping": clip,
        "energy_mean": round(energy_mean, 5),
        "energy_peak": round(energy_peak, 5),
    }
