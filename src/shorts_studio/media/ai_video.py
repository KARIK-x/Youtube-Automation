"""AI video generation: Kling AI and Higgsfield.

Both providers are async (submit job -> poll -> download). This module wraps
their REST APIs so generated clips can feed straight into the Shorts pipeline.

Credentials are read from (in order): environment variables, then config.yaml:
  env:  KLING_ACCESS_KEY, KLING_SECRET_KEY, HIGGSFIELD_API_KEY
  cfg:  ai_video.kling.access_key / .secret_key
        ai_video.higgsfield.api_key

Nothing is hardcoded; if credentials are missing the functions raise a clear
error instead of silently failing.
"""
import os, time, json, base64, hashlib, hmac
from pathlib import Path

try:
    import requests
except Exception:
    requests = None


# ---------- credential resolution ----------
def _cfg(cfg, *keys, default=None):
    cur = cfg or {}
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur if cur is not None else default


def kling_creds(cfg=None):
    ak = os.environ.get("KLING_ACCESS_KEY") or _cfg(cfg, "ai_video", "kling", "access_key")
    sk = os.environ.get("KLING_SECRET_KEY") or _cfg(cfg, "ai_video", "kling", "secret_key")
    if not ak or not sk:
        raise RuntimeError("Kling credentials missing. Set KLING_ACCESS_KEY/KLING_SECRET_KEY "
                           "or ai_video.kling.access_key/secret_key in config.yaml")
    return ak, sk


def higgsfield_creds(cfg=None):
    key = os.environ.get("HIGGSFIELD_API_KEY") or _cfg(cfg, "ai_video", "higgsfield", "api_key")
    if not key:
        raise RuntimeError("Higgsfield credentials missing. Set HIGGSFIELD_API_KEY "
                           "or ai_video.higgsfield.api_key in config.yaml")
    return key


# ---------- Kling AI ----------
KLING_BASE = "https://api.klingai.com"


def _kling_jwt(ak, sk):
    """Build a short-lived JWT for Kling (HS256) without external deps."""
    import json, base64, hmac, hashlib
    def b64url(b):
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    now = int(time.time())
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"iss": ak, "exp": now + 1800, "nbf": now - 5}).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(sk.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64url(sig)}"


def kling_text2video(prompt, *, cfg=None, duration=5, aspect_ratio="9:16",
                     model="kling-v1", mode="std", cfg_scale=0.5, poll=True,
                     timeout=300, out_dir=None):
    ak, sk = kling_creds(cfg)
    token = _kling_jwt(ak, sk)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "model_name": model,
        "prompt": prompt,
        "cfg_scale": cfg_scale,
        "mode": mode,
        "duration": str(duration),
        "aspect_ratio": aspect_ratio,
    }
    r = requests.post(f"{KLING_BASE}/v1/videos/text2video", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get("code") not in (0, None):
        raise RuntimeError(f"Kling submit failed: {data}")
    task_id = data["data"]["task_id"]
    if not poll:
        return {"task_id": task_id, "status": "submitted"}
    return _kling_poll(task_id, token, timeout=timeout, out_dir=out_dir)


def kling_image2video(image_path, prompt="", *, cfg=None, duration=5, aspect_ratio="9:16",
                     model="kling-v1", mode="std", cfg_scale=0.5, poll=True,
                     timeout=300, out_dir=None):
    ak, sk = kling_creds(cfg)
    token = _kling_jwt(ak, sk)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # encode image as base64 data url
    import base64
    b = Path(image_path).read_bytes()
    b64 = base64.b64encode(b).decode()
    mime = "image/png" if str(image_path).lower().endswith(".png") else "image/jpeg"
    body = {
        "model_name": model,
        "image": f"data:{mime};base64,{b64}",
        "prompt": prompt,
        "cfg_scale": cfg_scale,
        "mode": mode,
        "duration": str(duration),
        "aspect_ratio": aspect_ratio,
    }
    r = requests.post(f"{KLING_BASE}/v1/videos/image2video", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get("code") not in (0, None):
        raise RuntimeError(f"Kling image2video submit failed: {data}")
    task_id = data["data"]["task_id"]
    if not poll:
        return {"task_id": task_id, "status": "submitted"}
    return _kling_poll(task_id, token, timeout=timeout, out_dir=out_dir, endpoint="image2video")


def _kling_poll(task_id, token, timeout=300, out_dir=None, endpoint="text2video"):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{KLING_BASE}/v1/videos/{endpoint}/{task_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        task = data.get("data", {})
        status = task.get("task_status")
        if status == "succeed":
            videos = task.get("task_result", {}).get("videos", [])
            if not videos:
                raise RuntimeError("Kling task succeeded but no video returned")
            video_url = videos[0].get("url")
            if out_dir:
                out_dir = Path(out_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                dst = out_dir / f"kling_{task_id}.mp4"
                _download(video_url, dst)
                return {"task_id": task_id, "status": "done", "path": str(dst), "url": video_url}
            return {"task_id": task_id, "status": "done", "url": video_url}
        if status in ("failed", "error"):
            raise RuntimeError(f"Kling task failed: {task.get('task_status_msg')}")
        time.sleep(5)
    raise TimeoutError(f"Kling task {task_id} did not finish within {timeout}s")


# ---------- Higgsfield ----------
HIGGSFIELD_BASE = "https://platform.higgsfield.ai"


def higgsfield_generate(prompt, *, cfg=None, model="higgsfield-1", duration=5,
                        aspect_ratio="9:16", image_path=None, poll=True,
                        timeout=300, out_dir=None):
    key = higgsfield_creds(cfg)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio}
    if model:
        body["model"] = model
    if image_path:
        import base64
        b = Path(image_path).read_bytes()
        mime = "image/png" if str(image_path).lower().endswith(".png") else "image/jpeg"
        body["image"] = f"data:{mime};base64,{base64.b64encode(b).decode()}"
    # Higgsfield uses a generic generations endpoint
    r = requests.post(f"{HIGGSFIELD_BASE}/v1/generations", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    gen_id = data.get("id") or data.get("generation_id") or data.get("task_id")
    if not gen_id:
        raise RuntimeError(f"Higgsfield submit failed: {data}")
    if not poll:
        return {"id": gen_id, "status": "submitted"}
    return _higgsfield_poll(gen_id, key, timeout=timeout, out_dir=out_dir)


def _higgsfield_poll(gen_id, key, timeout=300, out_dir=None):
    headers = {"Authorization": f"Bearer {key}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{HIGGSFIELD_BASE}/v1/generations/{gen_id}", headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = (data.get("status") or data.get("state") or "").lower()
        if status in ("completed", "succeeded", "done", "success"):
            video_url = (data.get("video_url") or data.get("url")
                         or (data.get("output") or {}).get("video_url")
                         or (data.get("result") or {}).get("url"))
            if not video_url:
                raise RuntimeError(f"Higgsfield completed but no video URL: {data}")
            if out_dir:
                out_dir = Path(out_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                dst = out_dir / f"higgsfield_{gen_id}.mp4"
                _download(video_url, dst)
                return {"id": gen_id, "status": "done", "path": str(dst), "url": video_url}
            return {"id": gen_id, "status": "done", "url": video_url}
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"Higgsfield generation failed: {data}")
        time.sleep(5)
    raise TimeoutError(f"Higgsfield generation {gen_id} did not finish within {timeout}s")


# ---------- helpers ----------
def _download(url, dst):
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return str(dst)


def generate(provider, prompt, *, cfg=None, **kw):
    """Unified entry point. provider: 'kling' or 'higgsfield'."""
    provider = provider.lower()
    if provider == "kling":
        image_path = kw.pop("image_path", None)
        mode = kw.pop("mode", "text2video")
        if image_path or mode == "image2video":
            return kling_image2video(image_path, prompt, cfg=cfg, **kw)
        return kling_text2video(prompt, cfg=cfg, **kw)
    if provider == "higgsfield":
        return higgsfield_generate(prompt, cfg=cfg, **kw)
    raise ValueError(f"unknown provider: {provider}")