import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shorts_studio.media.tts_interface import synthesize, validate_voice, list_voices, VOICE_PROFILES

def test_tts_smoke():
    text = "At first, nobody noticed anything unusual. But when the engineer checked the final readings, one number did not make sense."
    out = str(ROOT / "data" / "work" / "tts_test.mp3")
    path, meta = synthesize(text, out, {}, profile="natural_male")
    assert os.path.exists(path) and os.path.getsize(path) > 0
    assert meta["provider"] == "edge-tts"
    assert meta["voice"] == "en-US-GuyNeural"
    print("TTS smoke OK, duration meta:", meta)

def test_validate_voice():
    assert validate_voice("edge-tts", "en-US-GuyNeural") is True
    assert validate_voice("edge-tts", "NONEXISTENT_VOICE") is False
    print("voice validation OK")

def test_voice_profiles():
    assert len(VOICE_PROFILES) >= 6
    for name, p in VOICE_PROFILES.items():
        assert "provider" in p and "voice" in p
    print("profiles OK:", list(VOICE_PROFILES.keys()))

def test_list_voices():
    voices = list_voices("edge-tts")
    assert len(voices) > 100
    print("list voices OK:", len(voices))

if __name__ == "__main__":
    test_tts_smoke()
    test_validate_voice()
    test_voice_profiles()
    test_list_voices()
    print("TTS TESTS PASS")