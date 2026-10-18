"""Illustrations : génération via OpenRouter puis conversion au style maison
(pixelisation + tramage ordonné + recoloration dans la rampe magenta)."""
from __future__ import annotations

import base64
import hashlib
import io
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageOps

from .config import Config
from .gfx import RAMP
from .scenes import PX0, PX1, PY0, PY1

PANEL = (PX1 - PX0, PY1 - PY0)
BLOCK = 3  # 1 « gros pixel » = 3 px internes = 6 px en 1080p

STYLE = ("Pixel art illustration, retro 16-bit video game style, dramatic chiaroscuro lighting, "
         "very high contrast, dark background, simple bold shapes, cinematic composition, "
         "no text, no letters, no watermark, no border. Subject: ")

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5


def stylize(im: Image.Image, size=PANEL, block=BLOCK) -> Image.Image:
    """Renvoie l'image en basse résolution (1 px = 1 gros pixel), déjà recolorée."""
    small = (size[0] // block, size[1] // block)
    g = ImageOps.fit(im.convert("L"), small, Image.LANCZOS, centering=(0.5, 0.45))
    g = ImageOps.autocontrast(g, cutoff=2)
    a = np.asarray(g, dtype=np.float32) / 255.0
    n = len(RAMP)
    by = np.tile(BAYER, (small[1] // 4 + 1, small[0] // 4 + 1))[: small[1], : small[0]]
    lvl = np.clip(np.floor(a * (n - 1) + 0.5 + by * 0.9), 0, n - 1).astype(np.int32)
    pal = np.array(RAMP, dtype=np.uint8)
    return Image.fromarray(pal[lvl], "RGB")


def generate(prompt: str, cfg: Config, cache: Path) -> Image.Image | None:
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{cfg.image_model}|{prompt}".encode()).hexdigest()[:16]
    raw_path = cache / f"{key}.png"
    if not raw_path.exists():
        if not cfg.openrouter_key:
            return None
        body = {
            "model": cfg.image_model,
            "messages": [{"role": "user", "content": STYLE + prompt}],
            "modalities": ["image", "text"],
            "image_config": {"aspect_ratio": "1:1"},
        }
        for attempt in range(3):
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=180,
                                  headers={"Authorization": f"Bearer {cfg.openrouter_key}"})
                r.raise_for_status()
                msg = r.json()["choices"][0]["message"]
                url = msg["images"][0]["image_url"]["url"]
                raw_path.write_bytes(base64.b64decode(url.split(",", 1)[1]))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  image: tentative {attempt + 1} échouée ({e})")
                time.sleep(2 * (attempt + 1))
        else:
            return None
    return stylize(Image.open(io.BytesIO(raw_path.read_bytes())))


def generate_all(story: dict, cfg: Config, cache: Path) -> dict[int, Image.Image]:
    out = {}
    for i, b in enumerate(story["beats"]):
        prompt = b.get("image")
        if not prompt:
            continue
        print(f"  🎨 image beat {i + 1}: {prompt[:70]}")
        im = generate(prompt, cfg, cache)
        if im is not None:
            out[i] = im
    return out
