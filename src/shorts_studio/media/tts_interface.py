"""TTS interface abstraction. Providers: edge-tts (online), openai, elevenlabs."""
import os, asyncio, json
from pathlib import Path

PROVIDERS = ("edge-tts", "openai", "elevenlabs")

VOICE_PROFILES = {
    "warm_documentary": {"provider": "edge-tts", "voice": "en-US-GuyNeural", "rate": "+0%", "pitch": "+0Hz"},
    "conversational_storyteller": {"provider": "edge-tts", "voice": "en-US-AriaNeural", "rate": "+0%", "pitch": "+0Hz"},
    "energetic_shorts": {"provider": "edge-tts", "voice": "en-US-ChristopherNeural", "rate": "+10%", "pitch": "+0Hz"},
    "calm_explainer": {"provider": "edge-tts", "voice": "en-US-DavisNeural", "rate": "-5%", "pitch": "-2Hz"},
    "natural_female": {"provider": "edge-tts", "voice": "en-US-JennyNeural", "rate": "+0%", "pitch": "+0Hz"},
    "natural_male": {"provider": "edge-tts", "voice": "en-US-GuyNeural", "rate": "+0%", "pitch": "+0Hz"},
}

def list_voices(provider="edge-tts"):
    if provider == "edge-tts":
        import edge_tts
        return asyncio.run(edge_tts.list_voices())
    return []

def validate_voice(provider, voice_id):
    if provider == "edge-tts":
        voices = list_voices(provider)
        names = [v["ShortName"] for v in voices]
        return voice_id in names
    return True

def synthesize(text, out_path, cfg, profile=None):
    """Generate TTS audio. Returns (path, metadata dict)."""
    if profile and profile in VOICE_PROFILES:
        p = VOICE_PROFILES[profile]
        provider = p["provider"]
        voice = p["voice"]
        rate = p.get("rate", "+0%")
        pitch = p.get("pitch", "+0Hz")
    else:
        provider = cfg.get("tts", {}).get("provider", "edge-tts")
        voice = cfg.get("tts", {}).get("voice", "en-US-GuyNeural")
        rate = "+0%"
        pitch = "+0Hz"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    meta = {"provider": provider, "voice": voice, "rate": rate, "pitch": pitch,
            "chars": len(text), "online": provider == "edge-tts"}
    if provider == "edge-tts":
        import edge_tts
        async def _gen():
            comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await comm.save(out_path)
        asyncio.run(_gen())
    elif provider == "openai":
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        r = client.audio.speech.create(model="tts-1", voice="alloy", input=text)
        with open(out_path, "wb") as f:
            f.write(r.content)
    else:
        raise ValueError(f"unknown provider {provider}")
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("TTS produced empty output")
    meta["size_bytes"] = os.path.getsize(out_path)
    return out_path, meta