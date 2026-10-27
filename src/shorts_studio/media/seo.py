"""SEO metadata generation: title, description, tags from transcript/content.

Uses LLM REST APIs if a key is available (OpenAI/Anthropic/Gemini), otherwise
falls back to a deterministic template. No SDK dependencies — only requests.
"""
import os, json, re
from pathlib import Path

try:
    import requests
except Exception:
    requests = None


def _llm_key(cfg, *envs):
    for e in envs:
        v = os.environ.get(e)
        if v:
            return v, e
    if cfg:
        for path in (("ai_video", "openai", "api_key"), ("ai_video", "anthropic", "api_key"),
                     ("ai_video", "gemini", "api_key")):
            cur = cfg
            for k in path:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    cur = None
                    break
            if cur:
                return cur, path[1].upper() + "_API_KEY"
    return None, None


def _call_openai(prompt, key, model="gpt-4o-mini"):
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      json={"model": model, "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.7, "max_tokens": 500}, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_anthropic(prompt, key, model="claude-3-5-haiku-20241022"):
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                               "Content-Type": "application/json"},
                      json={"model": model, "max_tokens": 500,
                            "messages": [{"role": "user", "content": prompt}]}, timeout=60)
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def _call_gemini(prompt, key, model="gemini-1.5-flash"):
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                      headers={"Content-Type": "application/json"},
                      json={"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500}}, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _llm(prompt, cfg=None):
    # try openai
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        try:
            return _call_openai(prompt, key), "openai"
        except Exception as e:
            pass
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            return _call_anthropic(prompt, key), "anthropic"
        except Exception:
            pass
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            return _call_gemini(prompt, key), "gemini"
        except Exception:
            pass
    # config-based
    for env, fn in (("OPENAI_API_KEY", _call_openai), ("ANTHROPIC_API_KEY", _call_anthropic),
                    ("GEMINI_API_KEY", _call_gemini)):
        k = _llm_key(cfg)[0] if cfg else None
        if k:
            try:
                return fn(prompt, k), env.lower().replace("_api_key", "")
            except Exception:
                pass
    return None, None


def generate_metadata(transcript_text, *, cfg=None, source_name=None, profile="chaos"):
    """Return dict: title, description, tags (list), hashtags (list)."""
    transcript_text = (transcript_text or "")[:3000]
    # template fallback
    base_title = (source_name or "Viral Clip").replace("_", " ").replace("-", " ").title()[:90]
    tags = ["shorts", "viral", "clips", profile, "trending"]
    desc = f"{base_title}\n\n#shorts #viral #trending"
    hashtags = ["#shorts", "#viral", "#trending", f"#{profile}"]

    prompt = f"""You are a YouTube Shorts SEO expert. Given this transcript, generate:
1. A catchy, SEO-optimized title (max 90 chars, include a hook, use caps for emphasis words)
2. A description (2-3 sentences, engaging, with a call to action)
3. 10 relevant tags (comma separated)
4. 5 hashtags

Transcript:
{transcript_text}

Respond in JSON format:
{{"title": "...", "description": "...", "tags": ["tag1", ...], "hashtags": ["#tag1", ...]}}"""

    text, provider = _llm(prompt, cfg)
    if text:
        # parse JSON
        try:
            # extract json block
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                title = (data.get("title") or base_title)[:100]
                description = data.get("description") or desc
                tags = data.get("tags") or tags
                hashtags = data.get("hashtags") or hashtags
                return {"title": title, "description": description, "tags": tags,
                        "hashtags": hashtags, "provider": provider}
        except Exception:
            pass
    # fallback
    return {"title": base_title, "description": desc, "tags": tags,
            "hashtags": hashtags, "provider": "template"}


def transcript_from_srt(srt_path):
    try:
        lines = Path(srt_path).read_text().splitlines()
    except Exception:
        return ""
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.isdigit() or "-->" in ln:
            continue
        out.append(ln)
    return " ".join(out)