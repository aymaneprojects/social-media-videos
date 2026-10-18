"""Bibliothèque paramétrique : personnages et objets dessinés en pixel art.

Les coordonnées (x, y) d'un personnage désignent le point au sol, entre ses
pieds ; celles d'un objet, son centre. 'px' = taille d'un pixel logique.
"""
from __future__ import annotations

import math

from PIL import ImageDraw

from .engine import color, darker, lighter

INK = "ink"


# --------------------------------------------------------------------------
# Personnage : grille de 14 x 30 unités, ancrée aux pieds
# --------------------------------------------------------------------------
def person(d: ImageDraw.ImageDraw, el: dict, x: float, y: float):
    px = int(el.get("px", 2))
    facing = el.get("facing", "right")
    ox = int(x - 7 * px)
    oy = int(y - 30 * px)
    gt = el.get("_gt", 0.0)

    def R(c0, r0, w, h, col):
        if col is None:
            return
        if facing == "left":
            c0 = 14 - c0 - w
        d.rectangle([ox + c0 * px, oy + r0 * px, ox + (c0 + w) * px - 1, oy + (r0 + h) * px - 1], fill=color(col))

    skin = el.get("skin", "skin")
    hair = el.get("hair", "hair")
    top = el.get("top", "accent")
    pants = el.get("pants", "grey2")
    shoes = el.get("shoes", "black")
    style = el.get("outfit", "shirt")
    pose = el.get("pose", "stand")
    topd = darker(color(top), 0.3)

    # jambes
    if style != "dress":
        if pose == "sit":
            R(4, 20, 7, 3, pants)
            R(9, 23, 2, 5, pants)
            R(9, 28, 3, 2, shoes)
        else:
            step = int(math.sin(gt * 10) * 1.5) if pose == "walk" else 0
            R(4, 20, 3, 8 - max(0, step), pants)
            R(7, 20, 3, 8 - max(0, -step), pants)
            R(3 - step, 28 - max(0, step), 4, 2, shoes)
            R(7 + step, 28 - max(0, -step), 4, 2, shoes)
    else:
        R(5, 25, 2, 3, skin)
        R(7, 25, 2, 3, skin)
        R(4, 28, 3, 2, shoes)
        R(7, 28, 3, 2, shoes)
    # torse
    long_ = style in ("labcoat", "coat", "dress")
    R(3, 11, 8, 13 if long_ else 9, top)
    R(10, 11, 1, 13 if long_ else 9, topd)
    if style == "dress":
        R(2, 20, 10, 5, top)
    if style in ("suit", "coat"):
        R(6, 11, 2, 5, "white")
        R(6, 12, 2, 4, el.get("tie", "red"))
    if style == "labcoat":
        R(6, 11, 2, 12, "grey")
    if style == "uniform":
        R(3, 15, 8, 1, "black")
        R(4, 12, 1, 1, "yellow")
        R(9, 12, 1, 1, "yellow")
    if el.get("build") == "large":  # silhouette corpulente : torse et ventre élargis
        R(1, 12, 12, 10 if not long_ else 12, top)
        R(12, 12, 1, 10, topd)
        R(2, 20, 10, 2, top)
    # bras
    if pose == "arms_up":
        R(1, 4, 2, 8, top)
        R(11, 4, 2, 8, top)
        R(1, 2, 2, 2, skin)
        R(11, 2, 2, 2, skin)
    elif pose == "point":
        R(1, 11, 2, 8, top)
        R(1, 19, 2, 2, skin)
        R(11, 12, 5, 2, top)
        R(16, 12, 2, 2, skin)
    elif pose == "hold":  # bras tendus devant (tient un objet)
        R(1, 11, 2, 6, top)
        R(11, 14, 4, 2, top)
        R(15, 14, 2, 2, skin)
        R(2, 16, 1, 2, skin)
    elif pose == "think":
        R(1, 11, 2, 8, top)
        R(1, 19, 2, 2, skin)
        R(10, 11, 2, 4, top)
        R(9, 8, 2, 3, skin)
    elif pose == "sit":
        R(1, 11, 2, 7, top)
        R(11, 11, 2, 7, top)
        R(1, 18, 2, 2, skin)
        R(11, 18, 2, 2, skin)
    else:
        swing = int(math.sin(gt * 10) * 1) if pose == "walk" else 0
        R(1, 11 + swing, 2, 8, top)
        R(11, 11 - swing, 2, 8, top)
        R(1, 19 + swing, 2, 2, skin)
        R(11, 19 - swing, 2, 2, skin)
    # cou + tête
    R(6, 10, 2, 1, skin)
    R(4, 2, 6, 8, skin)
    R(9, 3, 1, 6, darker(color(skin), 0.15))
    expr = el.get("face", "neutral")
    eye = INK
    if expr == "closed":
        R(5, 5, 1, 1, darker(color(skin), 0.4))
        R(8, 5, 1, 1, darker(color(skin), 0.4))
    else:
        R(5, 5, 1, 1, eye)
        R(8, 5, 1, 1, eye)
    if expr == "surprised":
        R(6, 7, 2, 2, INK)
    elif expr == "happy":
        R(5, 7, 4, 1, darker(color(skin), 0.45))
        R(6, 8, 2, 1, darker(color(skin), 0.45))
    elif expr == "sad":
        R(6, 7, 2, 1, darker(color(skin), 0.45))
        R(5, 8, 1, 1, darker(color(skin), 0.45))
        R(8, 8, 1, 1, darker(color(skin), 0.45))
    else:
        R(6, 8, 2, 1, darker(color(skin), 0.45))
    # cheveux
    hs = el.get("hair_style", "short")
    if hs == "short":
        R(4, 1, 6, 2, hair)
        R(4, 3, 1, 2, hair)
    elif hs == "long":
        R(4, 1, 6, 2, hair)
        R(3, 2, 2, 9, hair)
        R(9, 2, 2, 9, hair)
    elif hs == "bun":
        R(4, 1, 6, 2, hair)
        R(5, -1, 4, 2, hair)
    elif hs == "curly":
        R(3, 0, 8, 3, hair)
        R(3, 3, 1, 3, hair)
        R(10, 3, 1, 3, hair)
    elif hs == "bald":
        R(4, 4, 1, 2, hair)
        R(9, 4, 1, 2, hair)
    if el.get("glasses"):
        R(4, 5, 6, 1, INK)
        R(5, 4, 1, 1, INK)
        R(8, 4, 1, 1, INK)
    b = el.get("beard")
    if b == "mustache":
        R(5, 7, 4, 1, hair)
    elif b:
        R(4, 7, 6, 3, hair)
        R(6, 7, 2, 1, darker(color(skin), 0.45))
    hat = el.get("hat")
    hc = el.get("hat_color", "black")
    if hat == "fedora":
        R(2, 1, 10, 1, hc)
        R(4, -2, 6, 3, hc)
        R(4, 0, 6, 1, "red2")
    elif hat == "top":
        R(2, 1, 10, 1, hc)
        R(4, -5, 6, 6, hc)
    elif hat == "cap":
        R(4, 0, 6, 2, hc)
        R(9, 1, 4, 1, hc)
    elif hat == "helmet":
        R(3, -1, 8, 3, hc)
        R(2, 2, 10, 1, hc)
    elif hat == "bicorne":
        R(2, 0, 10, 2, hc)
        R(4, -2, 6, 2, hc)
        R(6, -1, 2, 1, "yellow")


# --------------------------------------------------------------------------
# Objets
# --------------------------------------------------------------------------
def obj(d: ImageDraw.ImageDraw, layer, el: dict, x: float, y: float, st: dict, ctx):
    name = el.get("name", "box")
    s = float(el.get("size", 1))
    gt = ctx.get("gt", 0)
    c = color(el.get("color", "accent"))
    cd, cl = darker(c, 0.4), lighter(c, 0.4)
    ink = color(INK)
    fn = OBJECTS.get(name)
    if fn:
        fn(d, x, y, s, c, cd, cl, ink, el, gt)
    else:
        d.rectangle([x - 10 * s, y - 10 * s, x + 10 * s, y + 10 * s], fill=c)


def _ship(d, x, y, s, c, cd, cl, ink, el, gt):
    hull = color(el.get("hull", "brown"))
    sail = color(el.get("sail", "paper"))
    rock = math.sin(gt * 1.5) * 1.5 * s
    y = y + rock
    d.polygon([(x - 32 * s, y), (x + 32 * s, y), (x + 24 * s, y + 12 * s), (x - 26 * s, y + 12 * s)], fill=hull)
    d.line([(x - 30 * s, y + 4 * s), (x + 30 * s, y + 4 * s)], fill=darker(hull, 0.4))
    for i in range(-3, 4):
        d.point((x + i * 7 * s, y + 7 * s), fill=ink)
    for mx, h in ((-12, 34), (6, 42), (22, 28)):
        d.line([(x + mx * s, y), (x + mx * s, y - h * s)], fill=darker(hull, 0.3), width=max(1, int(s)))
        d.polygon([(x + (mx - 9) * s, y - (h - 4) * s), (x + (mx + 9) * s, y - (h - 4) * s),
                   (x + (mx + 8) * s, y - 8 * s), (x + (mx - 8) * s, y - 8 * s)], fill=sail)
        d.line([(x + (mx + 2) * s, y - (h - 6) * s), (x + (mx + 2) * s, y - 9 * s)], fill=darker(sail, 0.2))
    d.polygon([(x + 6 * s, y - 46 * s), (x + 14 * s, y - 44 * s), (x + 6 * s, y - 42 * s)], fill=color("red"))


def _wave(d, x, y, s, c, cd, cl, ink, el, gt):
    w = float(el.get("w", 180))
    col = color(el.get("color", "water"))
    pts = [(xx, y + math.sin(xx * 0.12 + gt * 2) * 2 * s) for xx in range(int(x - w / 2), int(x + w / 2) + 3, 3)]
    d.polygon(pts + [(x + w / 2, y + 40 * s), (x - w / 2, y + 40 * s)], fill=col)
    d.line(pts, fill=lighter(col, 0.45))
    for i in range(int(w / 12)):
        xx = x - w / 2 + (i * 12 + gt * 6) % w
        d.line([(xx, y + 8 * s + (i % 3) * 6), (xx + 4, y + 8 * s + (i % 3) * 6)], fill=lighter(col, 0.2))


def _fruit(d, x, y, s, c, cd, cl, ink, el, gt, kind="lemon"):
    col = color(el.get("color", "yellow" if kind == "lemon" else "orange"))
    if kind == "lemon":
        d.ellipse([x - 9 * s, y - 6 * s, x + 9 * s, y + 6 * s], fill=col)
        d.polygon([(x + 8 * s, y - 2 * s), (x + 12 * s, y), (x + 8 * s, y + 2 * s)], fill=col)
        d.polygon([(x - 8 * s, y - 2 * s), (x - 12 * s, y), (x - 8 * s, y + 2 * s)], fill=col)
    else:
        d.ellipse([x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s], fill=col)
    d.ellipse([x + 1 * s, y + 1 * s, x + 7 * s, y + 6 * s], fill=darker(col, 0.25))
    d.rectangle([x - 5 * s, y - 4 * s, x - 3 * s, y - 3 * s], fill=lighter(col, 0.6))
    d.polygon([(x, y - 7 * s), (x + 6 * s, y - 11 * s), (x + 3 * s, y - 6 * s)], fill=color("green"))


def _barrel(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "brown"))
    d.rounded_rectangle([x - 10 * s, y - 13 * s, x + 10 * s, y + 13 * s], radius=int(4 * s), fill=col)
    for yy in (-8, 8):
        d.rectangle([x - 10 * s, y + yy * s - s, x + 10 * s, y + yy * s], fill=color("grey2"))
    d.rectangle([x + 4 * s, y - 12 * s, x + 7 * s, y + 12 * s], fill=darker(col, 0.25))
    if el.get("label"):
        from ..gfx import font
        d.text((x, y), el["label"], font=font("silkscreen", 8), fill=color("paper"), anchor="mm")


def _bottle(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "green2"))
    d.rectangle([x - 2 * s, y - 16 * s, x + 2 * s, y - 9 * s], fill=col)
    d.rectangle([x - 2 * s, y - 18 * s, x + 2 * s, y - 16 * s], fill=color(el.get("cap", "brown")))
    d.rounded_rectangle([x - 6 * s, y - 9 * s, x + 6 * s, y + 12 * s], radius=int(3 * s), fill=col)
    d.rectangle([x - 4 * s, y - 6 * s, x - 3 * s, y + 8 * s], fill=lighter(col, 0.4))
    if el.get("liquid"):
        lv = float(el.get("level", 0.6))
        d.rectangle([x - 5 * s, y + 11 * s - 19 * s * lv, x + 5 * s, y + 11 * s], fill=color(el["liquid"]))
    if el.get("label"):
        d.rectangle([x - 6 * s, y - 1 * s, x + 6 * s, y + 5 * s], fill=color("paper"))
        from ..gfx import font
        d.text((x, y + 2 * s), el["label"], font=font("silkscreen", 8), fill=ink, anchor="mm")


def _paper(d, x, y, s, c, cd, cl, ink, el, gt):
    w, h = float(el.get("w", 44)) * s, float(el.get("h", 56)) * s
    pap = color(el.get("color", "paper"))
    d.rectangle([x - w / 2 + 2, y - h / 2 + 2, x + w / 2 + 2, y + h / 2 + 2], fill=color("ink"))
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=pap)
    from ..gfx import font
    yy = y - h / 2 + 6
    if el.get("title"):
        d.text((x, yy + 2), el["title"], font=font("silkscreen", 8), fill=ink, anchor="mt")
        yy += 12
    for i in range(int(el.get("lines", 5))):
        lw = w - 10 - (i * 7 % 13)
        d.line([(x - w / 2 + 5, yy + i * 5), (x - w / 2 + 5 + lw, yy + i * 5)], fill=darker(pap, 0.3))
    if el.get("check"):
        for i in range(int(el.get("lines", 5))):
            d.rectangle([x + w / 2 - 9, yy + i * 5 - 2, x + w / 2 - 6, yy + i * 5 + 1], outline=darker(pap, 0.5))
    if el.get("sign"):
        d.line([(x, y + h / 2 - 8), (x + 6, y + h / 2 - 11), (x + 10, y + h / 2 - 7), (x + 16, y + h / 2 - 10)], fill=color("blue2"))


def _card(d, x, y, s, c, cd, cl, ink, el, gt):
    from ..gfx import font, text_size
    longest = max([text_size(str(t).upper(), font("silkscreen", 8))[0] for t in (el.get("lines_text") or [el.get("name", "")])] or [0])
    w, h = max(70 * s, 24 * s + longest + 14), 42 * s
    pap = color(el.get("color", "accent2"))
    d.rectangle([x - w / 2 + 2, y - h / 2 + 2, x + w / 2 + 2, y + h / 2 + 2], fill=color("ink"))
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=pap)
    pb = [x - w / 2 + 4, y - h / 2 + 5, x - w / 2 + 24 * s, y + h / 2 - 5]
    d.rectangle(pb, fill=darker(pap, 0.25))
    cx = (pb[0] + pb[2]) / 2
    d.ellipse([cx - 5 * s, pb[1] + 4 * s, cx + 5 * s, pb[1] + 15 * s], fill=color(el.get("skin", "skin")))
    d.rectangle([cx - 7 * s, pb[1] + 17 * s, cx + 7 * s, pb[3]], fill=color(el.get("top", "grey2")))
    d.rectangle([cx - 5 * s, pb[1] + 3 * s, cx + 5 * s, pb[1] + 6 * s], fill=color(el.get("hair", "hair")))
    from ..gfx import font
    ty = y - h / 2 + 8
    for ln in (el.get("lines_text") or [el.get("name", "")])[:4]:
        d.text((pb[2] + 4, ty), str(ln).upper(), font=font("silkscreen", 8), fill=ink, anchor="lm")
        ty += 9


def _tower(d, x, y, s, c, cd, cl, ink, el, gt):
    """Tour Eiffel stylisée, base en (x, y + 60s)."""
    col = color(el.get("color", "accent"))
    b = y + 60 * s
    d.polygon([(x - 30 * s, b), (x - 4 * s, y - 20 * s), (x + 4 * s, y - 20 * s), (x + 30 * s, b),
               (x + 18 * s, b), (x, b - 22 * s), (x - 18 * s, b)], fill=col)
    d.polygon([(x - 4 * s, y - 20 * s), (x - 1.5 * s, y - 60 * s), (x + 1.5 * s, y - 60 * s), (x + 4 * s, y - 20 * s)], fill=col)
    d.line([(x, y - 60 * s), (x, y - 68 * s)], fill=col)
    for yy, ww in ((b - 22 * s, 20), (y + 5 * s, 12), (y - 20 * s, 7)):
        d.rectangle([x - ww * s, yy - 2 * s, x + ww * s, yy], fill=darker(col, 0.2))
    for i in range(6):  # croisillons
        yy = b - i * 9 * s
        hw = 30 * s * (1 - i / 7.5)
        d.line([(x - hw, yy), (x + hw * 0.6, yy - 8 * s)], fill=darker(col, 0.35))


def _building(d, x, y, s, c, cd, cl, ink, el, gt):
    w, h = float(el.get("w", 50)) * s, float(el.get("h", 70)) * s
    col = color(el.get("color", "dark"))
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=col)
    d.rectangle([x + w / 2 - 5, y - h / 2, x + w / 2, y + h / 2], fill=darker(col, 0.3))
    win = color(el.get("windows", "accent"))
    for r in range(int(h / 12)):
        for k in range(int(w / 11)):
            lit = (r * 7 + k * 3) % 5 != 0
            d.rectangle([x - w / 2 + 4 + k * 11, y - h / 2 + 6 + r * 12, x - w / 2 + 9 + k * 11, y - h / 2 + 12 + r * 12],
                        fill=win if lit else darker(col, 0.4))
    if el.get("sign"):
        from ..gfx import font
        d.rectangle([x - w / 2 + 2, y - h / 2 - 11, x + w / 2 - 2, y - h / 2 - 2], fill=color("ink"), outline=win)
        d.text((x, y - h / 2 - 6), el["sign"], font=font("silkscreen", 8), fill=win, anchor="mm")


def _house(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "brown"))
    roof = color(el.get("roof", "red2"))
    d.rectangle([x - 14 * s, y - 8 * s, x + 14 * s, y + 12 * s], fill=col)
    d.polygon([(x - 18 * s, y - 8 * s), (x, y - 22 * s), (x + 18 * s, y - 8 * s)], fill=roof)
    d.rectangle([x - 3 * s, y + 2 * s, x + 3 * s, y + 12 * s], fill=darker(col, 0.5))
    d.rectangle([x + 6 * s, y - 3 * s, x + 11 * s, y + 2 * s], fill=color(el.get("window", "accent")))


def _hut(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "brown"))
    d.rectangle([x - 8 * s, y - 4 * s, x + 8 * s, y + 7 * s], fill=col)
    d.polygon([(x - 12 * s, y - 3 * s), (x, y - 15 * s), (x + 12 * s, y - 3 * s)], fill=color(el.get("roof", "accent_d")))
    d.rectangle([x - 2 * s, y + 1 * s, x + 2 * s, y + 7 * s], fill=color("ink"))


def _tree(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "green2"))
    d.rectangle([x - 2 * s, y, x + 2 * s, y + 14 * s], fill=color("brown2"))
    sway = math.sin(gt * 1.3 + x) * s
    d.ellipse([x - 12 * s + sway, y - 20 * s, x + 12 * s + sway, y + 4 * s], fill=col)
    d.ellipse([x - 4 * s + sway, y - 18 * s, x + 10 * s + sway, y - 6 * s], fill=lighter(col, 0.2))


def _table(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "brown"))
    w = float(el.get("w", 60)) * s
    d.rectangle([x - w / 2, y - 3 * s, x + w / 2, y], fill=col)
    d.rectangle([x - w / 2, y, x + w / 2, y + 1 * s], fill=darker(col, 0.35))
    for lx in (x - w / 2 + 3 * s, x + w / 2 - 6 * s):
        d.rectangle([lx, y + 1 * s, lx + 3 * s, y + 18 * s], fill=darker(col, 0.2))


def _bed(d, x, y, s, c, cd, cl, ink, el, gt):
    d.rectangle([x - 24 * s, y - 4 * s, x + 24 * s, y + 6 * s], fill=color(el.get("color", "white")))
    d.rectangle([x - 24 * s, y + 6 * s, x + 24 * s, y + 9 * s], fill=color("brown"))
    d.rectangle([x - 26 * s, y - 14 * s, x - 22 * s, y + 14 * s], fill=color("brown"))
    d.rectangle([x - 21 * s, y - 8 * s, x - 13 * s, y - 3 * s], fill=color("paper"))
    for lx in (x - 24 * s, x + 21 * s):
        d.rectangle([lx, y + 9 * s, lx + 3 * s, y + 14 * s], fill=color("brown2"))


def _lamp(d, x, y, s, c, cd, cl, ink, el, gt):
    on = el.get("on", True)
    d.rectangle([x - 7 * s, y + 8 * s, x + 7 * s, y + 12 * s], fill=color("grey2"))
    d.rectangle([x - 6 * s, y - 8 * s, x + 6 * s, y + 8 * s], outline=color("steel"))
    if on:
        fl = 1 + (1 if int(gt * 12) % 3 == 0 else 0)
        d.ellipse([x - 2 * s, y - (2 + fl) * s, x + 2 * s, y + 4 * s], fill=color("yellow"))
        d.ellipse([x - 1 * s, y, x + 1 * s, y + 3 * s], fill=color("white"))
    d.rectangle([x - 2 * s, y - 13 * s, x + 2 * s, y - 8 * s], fill=color("grey2"))


def _coin(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "yellow"))
    sq = abs(math.cos(gt * 3)) if el.get("spin") else 1
    w = max(1.0, 9 * s * sq)
    d.ellipse([x - w, y - 9 * s, x + w, y + 9 * s], fill=col, outline=darker(col, 0.35))
    if sq > 0.4:
        from ..gfx import font
        d.text((x, y), el.get("symbol", "$"), font=font("silkscreen-bold", 8), fill=darker(col, 0.45), anchor="mm")


def _bills(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "green"))
    n = int(el.get("n", 4))
    for i in range(n):
        yy = y - i * 3 * s
        d.rectangle([x - 14 * s, yy - 5 * s, x + 14 * s, yy + 5 * s], fill=col, outline=darker(col, 0.4))
        d.ellipse([x - 3 * s, yy - 3 * s, x + 3 * s, yy + 3 * s], outline=darker(col, 0.4))


def _bag(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "brown"))
    d.ellipse([x - 13 * s, y - 8 * s, x + 13 * s, y + 14 * s], fill=col)
    d.polygon([(x - 5 * s, y - 8 * s), (x + 5 * s, y - 8 * s), (x + 8 * s, y - 15 * s), (x - 8 * s, y - 15 * s)], fill=col)
    d.rectangle([x - 6 * s, y - 9 * s, x + 6 * s, y - 7 * s], fill=darker(col, 0.4))
    from ..gfx import font
    d.text((x, y + 4 * s), el.get("symbol", "$"), font=font("pixelify-bold", int(14 * s)), fill=color("yellow"), anchor="mm")


def _calendar(d, x, y, s, c, cd, cl, ink, el, gt):
    w, h = 40 * s, 36 * s
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=color("paper"))
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y - h / 2 + 9 * s], fill=color(el.get("color", "red")))
    from ..gfx import font
    d.text((x, y + 4 * s), str(el.get("text", "1925")), font=font("pixelify-bold", int(14 * s)), fill=ink, anchor="mm")
    for k in (-10, 10):
        d.rectangle([x + k * s - 1, y - h / 2 - 3, x + k * s + 1, y - h / 2 + 3], fill=color("grey2"))


def _clock(d, x, y, s, c, cd, cl, ink, el, gt):
    r = 16 * s
    d.ellipse([x - r, y - r, x + r, y + r], fill=color("paper"), outline=color(el.get("color", "accent")), width=2)
    sp = float(el.get("speed", 1))
    am = gt * sp * 2
    d.line([(x, y), (x + math.sin(am) * r * 0.75, y - math.cos(am) * r * 0.75)], fill=ink, width=1)
    d.line([(x, y), (x + math.sin(am / 12) * r * 0.5, y - math.cos(am / 12) * r * 0.5)], fill=ink, width=2)


def _skull(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "paper"))
    d.ellipse([x - 10 * s, y - 11 * s, x + 10 * s, y + 7 * s], fill=col)
    d.rectangle([x - 6 * s, y + 4 * s, x + 6 * s, y + 11 * s], fill=col)
    for ex in (-5, 2):
        d.rectangle([x + ex * s, y - 3 * s, x + (ex + 3) * s, y + 1 * s], fill=ink)
    for tx in range(-4, 6, 3):
        d.line([(x + tx * s, y + 7 * s), (x + tx * s, y + 11 * s)], fill=darker(col, 0.4))


def _head(d, x, y, s, c, cd, cl, ink, el, gt):
    """Tête de profil (vers la droite) avec option cerveau visible et barre qui traverse."""
    skin = color(el.get("skin", "skin"))
    d.ellipse([x - 22 * s, y - 26 * s, x + 18 * s, y + 14 * s], fill=skin)
    d.polygon([(x + 14 * s, y - 2 * s), (x + 22 * s, y + 4 * s), (x + 15 * s, y + 8 * s)], fill=skin)
    d.rectangle([x - 10 * s, y + 10 * s, x + 6 * s, y + 30 * s], fill=skin)
    d.polygon([(x - 6 * s, y + 16 * s), (x + 14 * s, y + 10 * s), (x + 12 * s, y + 24 * s), (x - 6 * s, y + 26 * s)], fill=skin)
    d.ellipse([x + 4 * s, y - 8 * s, x + 7 * s, y - 5 * s], fill=ink)
    d.ellipse([x - 12 * s, y - 4 * s, x - 6 * s, y + 3 * s], fill=darker(skin, 0.2))
    d.chord([x - 23 * s, y - 28 * s, x + 18 * s, y - 2 * s], 180, 360, fill=color(el.get("hair", "hair")))
    if el.get("brain"):
        d.ellipse([x - 16 * s, y - 22 * s, x + 10 * s, y - 2 * s], fill=color("red"))
        for i in range(5):
            d.arc([x - 14 * s + i * 4 * s, y - 20 * s, x - 6 * s + i * 4 * s, y - 10 * s], 0, 180, fill=color("red2"))
        if el.get("zone"):
            d.ellipse([x + 0 * s, y - 20 * s, x + 10 * s, y - 8 * s], fill=color("yellow"))
    if el.get("rod"):
        k = float(el.get("rod_k", 1))  # avancée de la barre 0..1
        x0, y0 = x + 12 * s, y + 22 * s
        x1, y1 = x - 2 * s, y - 60 * s
        d.line([(x0, y0), (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)], fill=color("grey2"), width=max(2, int(3 * s)))


def _rod(d, x, y, s, c, cd, cl, ink, el, gt):
    l = float(el.get("l", 60)) * s
    ang = math.radians(float(el.get("angle", -70)))
    x1, y1 = x + math.cos(ang) * l / 2, y + math.sin(ang) * l / 2
    x0, y0 = x - math.cos(ang) * l / 2, y - math.sin(ang) * l / 2
    d.line([(x0, y0), (x1, y1)], fill=color(el.get("color", "grey2")), width=max(2, int(3 * s)))
    d.line([(x0 + 1, y0), (x1 + 1, y1)], fill=color("steel"), width=1)


def _cart(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "brown"))
    d.rectangle([x - 18 * s, y - 8 * s, x + 18 * s, y + 2 * s], fill=col)
    for wx in (-11, 11):
        d.ellipse([x + (wx - 5) * s, y - 1 * s, x + (wx + 5) * s, y + 9 * s], outline=darker(col, 0.5), width=2)
    d.line([(x + 18 * s, y - 4 * s), (x + 32 * s, y - 4 * s)], fill=darker(col, 0.3), width=2)


def _crowd(d, x, y, s, c, cd, cl, ink, el, gt):
    n = int(el.get("n", 7))
    w = float(el.get("w", 150))
    cols = ["hair", "hair2", "grey", "black", "brown", "hair"]
    tops = el.get("tops") or ["grey2", "brown2", "blue2", "accent_d", "green2", "red2"]
    for i in range(n):
        xx = x - w / 2 + (i + 0.5) * w / n
        bob = 1 if el.get("cheer") and int(gt * 6 + i) % 2 else 0
        d.rectangle([xx - 6 * s, y - 2 * s - bob, xx + 6 * s, y + 12 * s], fill=color(tops[i % len(tops)]))
        d.ellipse([xx - 4 * s, y - 12 * s - bob, xx + 4 * s, y - 2 * s - bob], fill=color(["skin", "skin2", "skin3"][i % 3]))
        d.chord([xx - 4 * s, y - 13 * s - bob, xx + 4 * s, y - 5 * s - bob], 180, 360, fill=color(cols[i % len(cols)]))


def _arrow(d, x, y, s, c, cd, cl, ink, el, gt):
    l = float(el.get("l", 40)) * s
    ang = math.radians(float(el.get("angle", 0)))
    x1, y1 = x + math.cos(ang) * l / 2, y + math.sin(ang) * l / 2
    x0, y0 = x - math.cos(ang) * l / 2, y - math.sin(ang) * l / 2
    d.line([(x0, y0), (x1, y1)], fill=c, width=max(2, int(2 * s)))
    for a in (2.5, -2.5):
        d.line([(x1, y1), (x1 - 7 * s * math.cos(ang + a * 0.3), y1 - 7 * s * math.sin(ang + a * 0.3))], fill=c, width=max(2, int(2 * s)))


def _check(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "green"))
    d.ellipse([x - 9 * s, y - 9 * s, x + 9 * s, y + 9 * s], fill=col)
    d.line([(x - 5 * s, y), (x - 1 * s, y + 4 * s), (x + 5 * s, y - 4 * s)], fill=color("white"), width=max(2, int(2 * s)))


def _cross(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "red"))
    w = max(2, int(3 * s))
    d.line([(x - 8 * s, y - 8 * s), (x + 8 * s, y + 8 * s)], fill=col, width=w)
    d.line([(x - 8 * s, y + 8 * s), (x + 8 * s, y - 8 * s)], fill=col, width=w)


def _magnifier(d, x, y, s, c, cd, cl, ink, el, gt):
    d.ellipse([x - 10 * s, y - 10 * s, x + 6 * s, y + 6 * s], outline=color("steel"), width=max(2, int(2 * s)))
    d.line([(x + 4 * s, y + 4 * s), (x + 13 * s, y + 13 * s)], fill=color("brown"), width=max(3, int(3 * s)))


def _sun(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "yellow"))
    for i in range(8):
        a = i * math.pi / 4 + gt * 0.3
        d.line([(x + math.cos(a) * 12 * s, y + math.sin(a) * 12 * s), (x + math.cos(a) * 17 * s, y + math.sin(a) * 17 * s)], fill=col, width=2)
    d.ellipse([x - 9 * s, y - 9 * s, x + 9 * s, y + 9 * s], fill=col)


def _moon(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "paper"))
    d.ellipse([x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s], fill=col)
    d.ellipse([x - 3 * s, y - 10 * s, x + 11 * s, y + 6 * s], fill=color("bg"))


def _mountain(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "dark"))
    w = float(el.get("w", 120)) * s
    h = float(el.get("h", 60)) * s
    d.polygon([(x - w / 2, y + h / 2), (x - w * 0.1, y - h / 2), (x + w * 0.05, y - h * 0.3), (x + w * 0.2, y - h * 0.45), (x + w / 2, y + h / 2)], fill=col)
    d.polygon([(x - w * 0.1, y - h / 2), (x - w * 0.18, y - h * 0.3), (x - w * 0.02, y - h * 0.32)], fill=color("white"))


def _train(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "red2"))
    d.rectangle([x - 30 * s, y - 14 * s, x + 10 * s, y + 4 * s], fill=col)
    d.rectangle([x + 10 * s, y - 22 * s, x + 26 * s, y + 4 * s], fill=darker(col, 0.2))
    d.rectangle([x - 26 * s, y - 24 * s, x - 20 * s, y - 14 * s], fill=color("black"))
    for wx in (-22, -6, 12):
        d.ellipse([x + (wx - 5) * s, y + 1 * s, x + (wx + 5) * s, y + 11 * s], fill=color("black"))
    d.rectangle([x + 14 * s, y - 18 * s, x + 22 * s, y - 12 * s], fill=color("accent"))


def _envelope(d, x, y, s, c, cd, cl, ink, el, gt):
    pap = color(el.get("color", "paper"))
    d.rectangle([x - 16 * s, y - 10 * s, x + 16 * s, y + 10 * s], fill=pap, outline=darker(pap, 0.4))
    d.line([(x - 16 * s, y - 10 * s), (x, y + 2 * s), (x + 16 * s, y - 10 * s)], fill=darker(pap, 0.4))
    if el.get("seal"):
        d.ellipse([x - 3 * s, y - 1 * s, x + 3 * s, y + 5 * s], fill=color("red"))


def _explosion(d, x, y, s, c, cd, cl, ink, el, gt):
    r = float(el.get("r", 20)) * s
    for k, col in ((1.0, "orange"), (0.65, "yellow"), (0.3, "white")):
        pts = []
        for i in range(16):
            a = i * math.tau / 16
            rr = r * k * (1 if i % 2 == 0 else 0.6)
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
        d.polygon(pts, fill=color(col))


def _screen(d, x, y, s, c, cd, cl, ink, el, gt):
    w, h = float(el.get("w", 60)) * s, float(el.get("h", 40)) * s
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=color("grey2"))
    d.rectangle([x - w / 2 + 3, y - h / 2 + 3, x + w / 2 - 3, y + h / 2 - 3], fill=color("ink"))
    from ..gfx import font
    d.text((x, y), str(el.get("text", "")), font=font("silkscreen", 8), fill=color(el.get("color", "accent")), anchor="mm")
    d.rectangle([x - 6 * s, y + h / 2, x + 6 * s, y + h / 2 + 5 * s], fill=color("grey2"))


def _dish(d, x, y, s, c, cd, cl, ink, el, gt):
    """Assiette / bol vu de profil avec contenu coloré."""
    d.ellipse([x - 20 * s, y - 4 * s, x + 20 * s, y + 6 * s], fill=color("white"))
    d.chord([x - 14 * s, y - 12 * s, x + 14 * s, y + 4 * s], 180, 360, fill=color(el.get("food", "orange")))
    d.ellipse([x - 20 * s, y - 4 * s, x + 20 * s, y + 6 * s], outline=color("grey"))


def _scale(d, x, y, s, c, cd, cl, ink, el, gt):
    """Pèse-personne avec cadran."""
    d.rounded_rectangle([x - 16 * s, y - 4 * s, x + 16 * s, y + 4 * s], radius=int(2 * s), fill=color("white"))
    d.ellipse([x - 6 * s, y - 14 * s, x + 6 * s, y - 2 * s], fill=color("paper"), outline=color("grey2"))
    a = float(el.get("needle", 0.3)) * math.tau
    d.line([(x, y - 8 * s), (x + math.sin(a) * 5 * s, y - 8 * s - math.cos(a) * 5 * s)], fill=color("red"))


def _test_tube(d, x, y, s, c, cd, cl, ink, el, gt):
    col = color(el.get("color", "accent"))
    d.rectangle([x - 4 * s, y - 16 * s, x + 4 * s, y + 10 * s], outline=color("steel"))
    d.ellipse([x - 4 * s, y + 6 * s, x + 4 * s, y + 14 * s], fill=col)
    d.rectangle([x - 3 * s, y - 2 * s, x + 3 * s, y + 10 * s], fill=col)


OBJECTS = {
    "ship": _ship, "wave": _wave, "lemon": lambda *a: _fruit(*a, kind="lemon"),
    "orange": lambda *a: _fruit(*a, kind="orange"), "barrel": _barrel, "bottle": _bottle, "paper": _paper,
    "card": _card, "tower": _tower, "building": _building, "house": _house, "hut": _hut, "tree": _tree,
    "table": _table, "bed": _bed, "lamp": _lamp, "coin": _coin, "bills": _bills, "bag": _bag,
    "calendar": _calendar, "clock": _clock, "skull": _skull, "head": _head, "rod": _rod, "cart": _cart,
    "crowd": _crowd, "arrow": _arrow, "check": _check, "cross": _cross, "magnifier": _magnifier,
    "sun": _sun, "moon": _moon, "mountain": _mountain, "train": _train, "envelope": _envelope,
    "explosion": _explosion, "screen": _screen, "dish": _dish, "scale": _scale, "tube": _test_tube,
}

OBJECT_DOCS = ", ".join(sorted(OBJECTS))
