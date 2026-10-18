"""Logos de profil des pages (avatars Instagram, TikTok, YouTube, Facebook).

Dessinés en basse résolution (120x120) puis agrandis x9 en nearest neighbour :
les pixels restent nets. Le contenu tient dans le cercle central, car les
plateformes découpent les avatars en rond.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .anim.engine import draw_sprite_rows
from .gfx import font, text_size
from .theme import T, Theme, _mix, apply_theme

LS = 120  # taille logique


def _base() -> Image.Image:
    img = Image.new("RGB", (LS, LS), T.BG)
    d = ImageDraw.Draw(img)
    c = LS / 2
    for i in range(9, 0, -1):  # halo tramé en anneaux
        r = 10 + i * 6
        d.ellipse([c - r, c - r, c + r, c + r], fill=_mix(T.BG, T.ACCENT, 0.018 * (10 - i)))
    return img


def render_logo(brand: dict, accent: str, bg: str, with_name: bool) -> Image.Image:
    apply_theme(Theme.from_colors(bg, accent))
    img = _base()
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    rows = brand["logo"]
    w, h = max(len(r) for r in rows), len(rows)
    colors = {"#": "accent", "+": "accent2"}
    if with_name:
        px = 5
        draw_sprite_rows(d, rows, colors, (LS - w * px) // 2, 22, px)
        name = brand["name"]
        size = 16 if len(name) <= 8 else 12
        f = font("pixelify-bold", size)
        tw, _ = text_size(name, f)
        y = 22 + h * px + 8
        d.text(((LS - tw) // 2 + 1, y + 1), name, font=f, fill=T.SHADOW)
        d.text(((LS - tw) // 2, y), name, font=f, fill=T.WHITE)
    else:
        px = 6
        draw_sprite_rows(d, rows, colors, (LS - w * px) // 2, (LS - h * px) // 2, px)
    return img.resize((LS * 9, LS * 9), Image.NEAREST)


def make_logos(brand: dict) -> list[Path]:
    out_dir = Path(brand["dir"]) / "logo"
    out_dir.mkdir(exist_ok=True)
    doms = brand["domains"]
    first = next(iter(doms.values()))
    made = []
    variants = [("", first)] + ([(k, v) for k, v in doms.items()] if len(doms) > 1 else [])
    for suffix, dom in variants:
        for with_name in (True, False):
            img = render_logo(brand, dom["accent"], dom["bg"], with_name)
            name = f"logo{'-' + suffix if suffix else ''}{'' if with_name else '-icone'}"
            p = out_dir / f"{name}.png"
            img.save(p)
            img.resize((400, 400), Image.NEAREST).save(out_dir / f"{name}-400.png")
            made.append(p)
    return made
