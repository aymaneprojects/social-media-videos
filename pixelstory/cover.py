"""Miniature (couverture Reels / vignette YouTube) : image forte de l'accroche + titre."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from .gfx import font, text_size, wrap
from .theme import T


def make_cover(video: Path, story: dict, at: float = 1.6) -> Path:
    frame = video.parent / ".cover_frame.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", str(video), "-frames:v", "1", str(frame)],
                   check=True)
    img = Image.open(frame).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    title = (story.get("post", {}).get("cover_text") or story.get("post", {}).get("youtube_title")
             or story.get("title", "")).upper()
    f = font("pixelify-bold", 96)
    lines = wrap(title, f, W - 120)[:4]
    lh = 108
    band_h = 120 + lh * len(lines)
    y0 = int(H * 0.62)
    band = Image.new("RGBA", (W, band_h), T.SHADOW + (225,))
    img.paste(band, (0, y0), band)
    for i, ln in enumerate(lines):
        tw, _ = text_size(ln, f)
        y = y0 + 60 + i * lh
        d.text(((W - tw) // 2 + 6, y + 6), ln, font=f, fill=T.SHADOW)
        d.text(((W - tw) // 2, y), ln, font=f, fill=T.ACCENT if i == 0 else T.WHITE)
    tag = f"{story.get('brand_name', '')} · {story.get('domain_label', '')}"
    tf = font("silkscreen", 40)
    tw, th = text_size(tag, tf)
    d.rectangle([(W - tw) // 2 - 20, y0 - 70, (W + tw) // 2 + 20, y0 - 10], fill=T.ACCENT)
    d.text(((W - tw) // 2, y0 - 66), tag, font=tf, fill=T.INK)
    out = video.parent / "cover.jpg"
    img.save(out, quality=86)
    frame.unlink(missing_ok=True)
    return out
