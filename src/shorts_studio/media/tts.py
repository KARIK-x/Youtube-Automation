"""Text-to-speech. Free default: edge-tts."""
import os, asyncio

async def _edge(text, voice, out):
    import edge_tts
    comm = edge_tts.Communicate(text, voice)
    await comm.save(out)

def synthesize(text, out_path, cfg):
    provider = cfg["tts"]["provider"]
    if provider == "edge-tts":
        voice = cfg["tts"]["voice"]
        asyncio.run(_edge(text, voice, out_path))
        return out_path
    if provider == "openai":
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        r = client.audio.speech.create(model="tts-1", voice="alloy", input=text)
        with open(out_path,"wb") as f:
            f.write(r.content)
        return out_path
    if provider == "elevenlabs":
        import requests
        vid = cfg["tts"].get("voice_id","21m00Tcm4TlvDq8ikWAM")
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
            headers={"xi-api-key": os.getenv("ELEVENLABS_API_KEY")},
            json={"text": text, "model_id": "eleven_monolingual_v1"})
        with open(out_path,"wb") as f:
            f.write(r.content)
        return out_path
    raise ValueError("unknown tts provider")
