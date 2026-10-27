"""Ken Burns effect: slow zoom/pan on still images for professional motion.

Uses FFmpeg's zoompan filter — no new dependencies, deterministic, testable.
Supports zoom-in, zoom-out, pan-left, pan-right, and combined motions.
"""
import os, subprocess
from pathlib import Path


def ken_burns(input_img, output_video, *, duration=5.0, fps=30, w=1080, h=1920,
              zoom_type="zoom_in", start_scale=1.0, end_scale=1.15,
              pan_x=0.0, pan_y=0.0, easing="linear", crf=24, preset="fast"):
    """Render a still image into a video with Ken Burns motion.

    zoom_type: zoom_in | zoom_out | pan_left | pan_right | pan_up | pan_down | zoom_pan
    easing: linear | ease_in | ease_out | ease_in_out
    Returns output path.
    """
    # Build zoom expression based on type and easing
    n_frames = int(duration * fps)
    if n_frames < 1:
        n_frames = 1

    # zoom factor over time (0..1 progress)
    # z(t) goes from start_scale to end_scale
    if zoom_type == "zoom_in":
        zs, ze = start_scale, end_scale
    elif zoom_type == "zoom_out":
        zs, ze = end_scale, start_scale
    elif zoom_type.startswith("pan_"):
        zs, ze = 1.1, 1.1  # slight zoom for pan
    else:
        zs, ze = start_scale, end_scale

    # easing function for progress p in [0,1]
    if easing == "ease_in":
        ez = "p*p"
    elif easing == "ease_out":
        ez = "1-(1-p)*(1-p)"
    elif easing == "ease_in_out":
        ez = "p*p*(3-2*p)"
    else:
        ez = "p"

    # zoompan filter expressions
    # p = on/frames (progress 0..1)
    # z = zs + (ze-zs)*easing(p)
    zoom_expr = f"{zs}+({ze}-{zs})*({ez.replace('p','on/{n_frames}').replace('on/{n_frames}','on/{n_frames}')})" if False else None

    # Simpler: use on/n_frames for progress
    progress = f"on/{n_frames}"
    if easing == "ease_in":
        prog_eased = f"({progress})*({progress})"
    elif easing == "ease_out":
        prog_eased = f"1-(1-({progress}))*(1-({progress}))"
    elif easing == "ease_in_out":
        prog_eased = f"({progress})*({progress})*(3-2*({progress}))"
    else:
        prog_eased = progress

    z_expr = f"{zs}+({ze}-{zs})*{prog_eased}"

    # pan offsets
    if zoom_type == "pan_left":
        x_expr = f"iw-(iw/zoom)-(on/{n_frames})*iw*0.1"
        y_expr = "ih/2-(ih/zoom/2)"
    elif zoom_type == "pan_right":
        x_expr = f"0+(on/{n_frames})*iw*0.1"
        y_expr = "ih/2-(ih/zoom/2)"
    elif zoom_type == "pan_up":
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"ih-(ih/zoom)-(on/{n_frames})*ih*0.1"
    elif zoom_type == "pan_down":
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"0+(on/{n_frames})*ih*0.1"
    else:
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"

    # Add small pan for zoom_pan type
    if zoom_type == "zoom_pan":
        x_expr = f"iw/2-(iw/zoom/2)+(on/{n_frames})*iw*0.05"
        y_expr = f"ih/2-(ih/zoom/2)+(on/{n_frames})*ih*0.05"

    zoompan = (f"zoompan=z='{z_expr}':"
               f"x='{x_expr}':y='{y_expr}':"
               f"d={n_frames}:s={w}x{h}:fps={fps}")

    # Also apply a subtle fade-in at start
    vf = f"{zoompan},fade=t=in:st=0:d=0.5"

    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(input_img),
           "-t", str(duration),
           "-vf", vf,
           "-r", str(fps), "-an",
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           str(output_video)]
    subprocess.run(cmd, capture_output=True, check=True, timeout=300)
    return str(output_video)


def apply_ken_burns_to_scene(scene_img, out_video, cfg, duration, zoom_type=None):
    """Apply Ken Burns to a scene image. Picks zoom_type from config or auto."""
    w = cfg["video"]["width"]
    h = cfg["video"]["height"]
    fps = cfg["video"].get("fps", 30)
    kb = cfg.get("editing", {}).get("ken_burns", {})
    if not kb.get("enabled", False):
        # fallback: static loop
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", scene_img,
                       "-t", str(duration), "-vf", f"scale={w}:{h}",
                       "-r", str(fps), "-an", "-c:v", "libx264", "-preset", "fast",
                       "-crf", "24", out_video], capture_output=True, check=True, timeout=300)
        return out_video
    if zoom_type is None:
        import random
        zoom_type = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "zoom_pan"])
    return ken_burns(scene_img, out_video, duration=duration, fps=fps, w=w, h=h,
                     zoom_type=zoom_type, start_scale=kb.get("start_scale", 1.0),
                     end_scale=kb.get("end_scale", 1.12), easing=kb.get("easing", "ease_in_out"))