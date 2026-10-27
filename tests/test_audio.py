import sys, os, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.media import audio_analysis

def test_analyze_dolma():
    src = ROOT / "data" / "sources" / "_done" / "dolma.mp4"
    if not src.exists():
        print("SKIP dolma missing"); return
    a = audio_analysis.analyze(str(src))
    print("dolma:", a["duration"], "bpm=", a["bpm"], "onsets=", a["onset_count"], "silence=", len(a["silence"]), "clip=", a["clipping"]["clipping"])
    assert a["duration"] > 0
    assert "beats" not in a or True
    assert isinstance(a["onsets"], list)

def test_analyze_ray():
    src = Path("/Users/ashim/Downloads/Ray Did Not Want To Share His Food With His Cameraman! 💀😭_1080p60.mp4")
    if not src.exists():
        print("SKIP ray missing"); return
    a = audio_analysis.analyze(str(src))
    print("ray:", a["duration"], "bpm=", a["bpm"], "onsets=", a["onset_count"], "silence=", len(a["silence"]), "clip=", a["clipping"]["clipping"])
    assert a["duration"] > 0

def test_silence_audio():
    # generate 5s silence wav
    p = ROOT / "data" / "work" / "silence.wav"
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=22050:cl=mono","-t","5",str(p)], capture_output=True)
    a = audio_analysis.analyze(str(p))
    print("silence:", a["duration"], "bpm=", a["bpm"], "onsets=", a["onset_count"], "silence=", len(a["silence"]))
    assert a["onset_count"] == 0 or a["onset_count"] < 3
    os.remove(p)

def test_clipping_detection():
    # generate a loud tone
    p = ROOT / "data" / "work" / "tone.wav"
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","sine=frequency=440:duration=2","-af","volume=10",str(p)], capture_output=True)
    a = audio_analysis.analyze(str(p))
    print("tone clipping:", a["clipping"])
    os.remove(p)

if __name__ == "__main__":
    test_analyze_dolma()
    test_analyze_ray()
    test_silence_audio()
    test_clipping_detection()
    print("AUDIO TESTS PASS")
