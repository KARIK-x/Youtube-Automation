"""Thumbnail generation with PIL."""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def make_thumbnail(video_path, title, out_path, cfg):
    # extract a frame mid-video via ffmpeg
    import subprocess, json
    info = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",video_path],
                          capture_output=True, text=True)
    dur = float(json.loads(info.stdout)["format"]["duration"])
    t = min(max(dur*0.3, 1), dur-1)
    frame = out_path + ".frame.jpg"
    subprocess.run(["ffmpeg","-y","-ss",str(t),"-i",video_path,"-frames:v","1","-q:v","2",frame],
                   capture_output=True)
    if not os.path.exists(frame):
        # blank
        img = Image.new("RGB",(cfg["thumbnail"]["width"],cfg["thumbnail"]["height"]),(20,20,20))
    else:
        img = Image.open(frame).convert("RGB")
    tw, th = cfg["thumbnail"]["width"], cfg["thumbnail"]["height"]
    # crop to 16:9
    img = img.resize((tw, th), Image.LANCZOS)
    draw = ImageDraw.Draw(img)
    font_path = cfg["thumbnail"].get("font","")
    size = cfg["thumbnail"].get("font_size",96)
    try:
        font = ImageFont.truetype(font_path, size)
    except Exception:
        font = ImageFont.load_default()
    # text with outline
    text = (title or "").upper()[:40]
    # wrap
    lines = []
    words = text.split()
    cur = ""
    for w in words:
        if len(cur)+len(w)+1 <= 18:
            cur = (cur+" "+w).strip()
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    y = th//2 - len(lines)*size//2
    for line in lines:
        # outline
        for dx in (-3,0,3):
            for dy in (-3,0,3):
                draw.text((tw//2+dx, y+dy), line, font=font, fill=(0,0,0), anchor="mm")
        draw.text((tw//2, y), line, font=font, fill=(255,230,0), anchor="mm")
        y += size + 8
    img.save(out_path, "JPEG", quality=92)
    if os.path.exists(frame):
        os.remove(frame)
    return out_path
