"""Palette, polices, icônes pixel et primitives de dessin.

Tout est dessiné à la résolution interne (540x960) puis agrandi x2 en
"nearest neighbour" par ffmpeg : chaque pixel logique devient un bloc 2x2,
ce qui donne le rendu pixel art net des vidéos de référence.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .theme import T

W, H = 540, 960
FPS = 30
ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

@lru_cache(maxsize=64)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"{name}.woff"), size)


def caption_font(size=40):
    # VT323 : la plus proche des vidéos de référence (traits fins, très lisible)
    return font("vt323", int(size * 1.35))


def ui_font(size=16):
    return font("silkscreen", size)


def big_font(size=72):
    return font("vt323", size)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return 3 * t * t - 2 * t * t * t


def blink(t, hz=2.0):
    return (t * hz) % 1.0 < 0.5


# --- Texte -----------------------------------------------------------------
def text_size(txt, fnt):
    if not txt:
        return 0, 0
    l, t, r, b = fnt.getbbox(txt)
    return r - l, b - t


def draw_text(d: ImageDraw.ImageDraw, xy, txt, fnt, fill=None, anchor="la",
              shadow=True, shadow_col=None, offset=2):
    fill = fill or T.WHITE
    shadow_col = shadow_col or T.SHADOW
    if shadow:
        d.text((xy[0] + offset, xy[1] + offset), txt, font=fnt, fill=shadow_col, anchor=anchor)
    d.text(xy, txt, font=fnt, fill=fill, anchor=anchor)


def typed(txt: str, progress: float) -> str:
    """Effet machine à écrire : renvoie le préfixe visible."""
    n = int(round(len(txt) * max(0.0, min(1.0, progress))))
    return txt[:n]


def wrap(txt, fnt, max_w):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if text_size(test, fnt)[0] <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# --- Formes ------------------------------------------------------------------
def frame_box(d, box, col=None, width=2, corners_only=False, clen=10):
    col = col or T.ACCENT
    x0, y0, x1, y1 = box
    if not corners_only:
        d.rectangle(box, outline=col, width=width)
        return
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.rectangle([min(cx, cx + sx * clen), cy - (width // 2), max(cx, cx + sx * clen), cy + (width - 1) // 2], fill=col)
        d.rectangle([cx - (width // 2), min(cy, cy + sy * clen), cx + (width - 1) // 2, max(cy, cy + sy * clen)], fill=col)


def dotted_hline(d, x0, x1, y, col=None, step=4):
    col = col or T.DIM
    for x in range(int(x0), int(x1), step):
        d.point((x, y), fill=col)


def wave_points(x0, x1, y, amp, freq, phase, step=3):
    pts = []
    for x in range(int(x0), int(x1) + step, step):
        pts.append((x, y + amp * math.sin(x * freq + phase)))
    return pts


# --- Icônes pixel (1 caractère '#' = 1 pixel, '+' = pixel accent) ------------
ICONS = {
    "person": [
        "....##....",
        "...####...",
        "...####...",
        "....##....",
        "..######..",
        ".#.####.#.",
        ".#.####.#.",
        "...#..#...",
        "...#..#...",
        "...#..#...",
    ],
    "runner": [
        "......##....",
        "......##....",
        "...#####....",
        "..#.###.##..",
        ".#..###...#.",
        "....####....",
        "...##..##...",
        "..##....#...",
        ".#.......#..",
        "#.........#.",
    ],
    "runner2": [
        "......##....",
        "......##....",
        "....####....",
        "...####.#...",
        "...###..#...",
        "....###.....",
        "....###.....",
        "....#.##....",
        "...#...#....",
        "...#....#...",
    ],
    "skull": [
        "..######..",
        ".########.",
        "##########",
        "##..##..##",
        "##..##..##",
        "##########",
        ".###..###.",
        "..######..",
        "..#.##.#..",
    ],
    "drop": [
        "....#....",
        "....#....",
        "...###...",
        "..#####..",
        ".#######.",
        ".##+####.",
        ".#+#####.",
        ".#######.",
        "..#####..",
        "...###...",
    ],
    "car": [
        "...######...",
        "..#..#...#..",
        ".#...#....#.",
        "############",
        "#+########+#",
        "############",
        "..##....##..",
        "..##....##..",
    ],
    "heart": [
        ".##...##.",
        "####.####",
        "#+#######",
        "#########",
        ".#######.",
        "..#####..",
        "...###...",
        "....#....",
    ],
    "medal": [
        "#........#",
        ".#......#.",
        "..#....#..",
        "...#..#...",
        "...####...",
        "..######..",
        ".###++###.",
        ".##+##+##.",
        ".###++###.",
        "..######..",
        "...####...",
    ],
    "flask": [
        "...##...",
        "...##...",
        "..####..",
        "..#..#..",
        ".#....#.",
        "#......#",
        "#.++++.#",
        "#.++++.#",
        "#......#",
        ".######.",
    ],
    "egg": [
        "...##...",
        "..####..",
        ".######.",
        ".#+####.",
        "##+#####",
        "########",
        ".######.",
        "..####..",
    ],
    "glass": [
        "#......#",
        "#......#",
        "#.++++.#",
        ".#++++#.",
        "..####..",
        "...##...",
        "...##...",
        "..####..",
    ],
    "apple": [
        ".....#..",
        "....#...",
        ".##.#.#.",
        "########",
        "#+######",
        "########",
        ".######.",
        "..##.##.",
    ],
    "dumbbell": [
        ".##......##.",
        "###......###",
        "############",
        "###......###",
        ".##......##.",
    ],
    "bolt": [
        "....###",
        "...###.",
        "..###..",
        ".######",
        "....##.",
        "...##..",
        "..##...",
        ".#.....",
    ],
    "flame": [
        "....#....",
        "...##....",
        "...###...",
        "..####.#.",
        ".#######.",
        ".###+####",
        "##++++###",
        "##+++###.",
        ".##++##..",
        "..#####..",
    ],
    "trophy": [
        "##########",
        "#.######.#",
        "#.######.#",
        ".#.####.#.",
        "...####...",
        "....##....",
        "....##....",
        "...####...",
        "..######..",
    ],
    "syringe": [
        ".........#",
        "........#.",
        ".......#..",
        "...#..#...",
        "....##....",
        "...####...",
        "..#+++.#..",
        ".#+++.#...",
        "#+++.#....",
        ".#.##.....",
    ],
    "flag": [
        "#.#.#.#",
        "##.#.#.",
        "#.#.#.#",
        "##.#.#.",
        "#......",
        "#......",
        "#......",
        "#......",
    ],
    "pill": [
        "...####...",
        "..#++++#..",
        ".#++++++#.",
        ".#++++++#.",
        ".########.",
        ".#......#.",
        ".#......#.",
        "..######..",
    ],
    "plate": [
        "#..######..#",
        "#.#......#.#",
        "##..####..##",
        "##.#++++#.##",
        "##.#++++#.##",
        "##..####..##",
        "#.#......#.#",
        "#..######..#",
    ],
    "bread": [
        "..######..",
        ".#++++++#.",
        "#+#+#+#++#",
        "#++++++++#",
        "#++++++++#",
        ".########.",
    ],
    "fish": [
        "....####...#",
        "..########.#",
        ".#+########.",
        "############",
        ".##########.",
        "..########.#",
        "....####...#",
    ],
    "scale": [
        "....##....",
        "##########",
        "#...##...#",
        "#...##...#",
        "##..##..##",
        "....##....",
        "....##....",
        "..######..",
    ],
    "bike": [
        "......##....",
        ".....#......",
        "..##.####...",
        ".#..#..#.##.",
        "#..#.#.##..#",
        "#...#..#...#",
        ".#..#...#..#",
        "..##.....##.",
    ],
    "clock": [
        "..######..",
        ".#......#.",
        "#....#...#",
        "#....#...#",
        "#....###.#",
        "#........#",
        ".#......#.",
        "..######..",
    ],
    "dollar": [
        "...#...",
        ".#####.",
        "#..#...",
        "#..#...",
        ".####..",
        "...#.#.",
        "...#..#",
        "...#..#",
        "#####..",
        "...#...",
    ],
    "chart": [
        "..........#",
        ".........##",
        "....#...#.#",
        "...#.#.#...",
        "..#...#....",
        ".#.........",
        "#..........",
        "###########",
    ],
    "coin": [
        "..####..",
        ".#++++#.",
        "#++##++#",
        "#+#++#+#",
        "#+#++#+#",
        "#++##++#",
        ".#++++#.",
        "..####..",
    ],
    "building": [
        "..######..",
        "..#+#+##..",
        "..######..",
        "..#+#+##..",
        "..######..",
        "..#+#+##..",
        "..######..",
        "##########",
    ],
    "dna": [
        "#.....#",
        ".#...#.",
        "..#+#..",
        "...#...",
        "..#+#..",
        ".#...#.",
        "#.....#",
        ".#...#.",
        "..#+#..",
        "...#...",
    ],
    "bed": [
        "#...........",
        "#.##........",
        "#.##.#######",
        "############",
        "#..........#",
        "#..........#",
    ],
    "brain": [
        "..##.##...",
        ".#..#..##.",
        "#..#..#..#",
        "#.#..#...#",
        "#..##..#.#",
        ".#...##.#.",
        "..#####...",
        "....#.....",
    ],
}


def icon_size(name, scale):
    rows = ICONS.get(name, ICONS["person"])
    return max(len(r) for r in rows) * scale, len(rows) * scale


def draw_icon(d, name, x, y, scale=4, col=None, accent=None, anchor="mm"):
    col = col or T.ACCENT
    rows = ICONS.get(name, ICONS["person"])
    w, h = icon_size(name, scale)
    if anchor == "mm":
        x, y = x - w // 2, y - h // 2
    elif anchor == "mb":
        x, y = x - w // 2, y - h
    accent = accent or mix(col, T.WHITE, 0.55)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == "#":
                c = col
            elif ch == "+":
                c = accent
            else:
                continue
            d.rectangle([x + i * scale, y + j * scale, x + (i + 1) * scale - 1, y + (j + 1) * scale - 1], fill=c)
    return w, h


# --- Fond --------------------------------------------------------------------
@lru_cache(maxsize=8)
def background(style: str = "dots") -> Image.Image:
    img = Image.new("RGB", (W, H), T.BG)
    d = ImageDraw.Draw(img)
    # dégradé vertical très léger
    for y in range(H):
        t = abs(y - H * 0.38) / H
        d.line([(0, y), (W, y)], fill=mix(T.BG2, T.BG, min(1, t * 2.2)))
    if style == "grid":
        for x in range(0, W, 30):
            d.line([(x, 0), (x, H)], fill=T.GRID)
        for y in range(0, H, 30):
            d.line([(0, y), (W, y)], fill=T.GRID)
    elif style == "dots":
        for y in range(0, H, 6):
            for x in range(0, W, 6):
                if ((x // 6) + (y // 6)) % 2 == 0:
                    d.point((x, y), fill=mix(T.GRID, T.BG, 0.4))
    return img


@lru_cache(maxsize=1)
def vignette() -> Image.Image:
    """Masque L : 255 au centre, plus sombre vers les bords."""
    m = Image.new("L", (W // 6, H // 6), 0)
    px = m.load()
    cx, cy = m.width / 2, m.height * 0.42
    for y in range(m.height):
        for x in range(m.width):
            dx, dy = (x - cx) / (m.width * 0.75), (y - cy) / (m.height * 0.62)
            px[x, y] = int(255 * max(0.0, min(1.0, 1.15 - (dx * dx + dy * dy))))
    return m.resize((W, H), Image.BILINEAR)
