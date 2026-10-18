"""Moteur d'animation pixel art « storyboard ».

Chaque plan (shot) est une liste d'éléments décrits en JSON : formes, sprites
ASCII, personnages et objets paramétriques, textes, compteurs, particules,
halos. Chaque élément a une entrée (in), des déplacements (move), une boucle
(loop) et une sortie (out), calés en secondes ou sur un mot de la voix ("w3").

Le rendu se fait en vraie basse résolution (180x320) puis est agrandi x6 en
nearest neighbour : tout ce qui est dessiné devient naturellement du pixel art.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

from ..gfx import font, text_size
from ..theme import T, _mix

LW, LH = 180, 320
SCALE = 6

FIXED = {
    "black": (6, 5, 4), "white": (250, 246, 236), "red": (226, 54, 54), "red2": (150, 28, 34),
    "blue": (64, 136, 230), "blue2": (28, 62, 120), "green": (88, 200, 92), "green2": (36, 110, 52),
    "skin": (240, 196, 150), "skin2": (198, 140, 96), "skin3": (140, 90, 60), "hair": (70, 44, 28),
    "hair2": (200, 170, 110), "grey": (150, 146, 140), "grey2": (88, 86, 82), "brown": (128, 82, 44),
    "brown2": (82, 50, 26), "purple": (150, 90, 200), "yellow": (250, 220, 80), "orange": (250, 140, 40),
    "paper": (238, 226, 200), "paper2": (200, 186, 156), "steel": (180, 190, 200), "water": (40, 90, 150),
}


def color(name, alpha=255):
    """Nom de couleur → RGBA. Couleurs du thème (accent...) + couleurs fixes."""
    if name is None:
        return None
    if isinstance(name, (list, tuple)):
        c = tuple(name)
        return c if len(c) == 4 else c + (alpha,)
    n = str(name)
    theme = {
        "bg": T.BG, "ink": T.SHADOW, "dark": T.DIM, "dim": T.DIM, "mid": T.MID, "soft": T.SOFT,
        "accent": T.ACCENT, "accent2": T.ACCENT2, "pale": T.PALE,
        "accent_d": _mix(T.ACCENT, (0, 0, 0), 0.35), "accent_dd": _mix(T.ACCENT, (0, 0, 0), 0.62),
    }
    if n in theme:
        return theme[n] + (alpha,)
    if n in FIXED:
        return FIXED[n] + (alpha,)
    if n.startswith("#") and len(n) == 7:
        return tuple(int(n[i:i + 2], 16) for i in (1, 3, 5)) + (alpha,)
    return T.ACCENT + (alpha,)


def darker(c, k=0.35):
    return tuple(int(v * (1 - k)) for v in c[:3]) + (c[3] if len(c) > 3 else 255,)


def lighter(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c[:3]) + (c[3] if len(c) > 3 else 255,)


# --- easing ------------------------------------------------------------------
def ease(name, t):
    t = max(0.0, min(1.0, t))
    if name == "linear":
        return t
    if name == "in":
        return t * t * t
    if name == "inout":
        return 3 * t * t - 2 * t * t * t
    if name == "back":
        s = 1.70158
        t -= 1
        return t * t * ((s + 1) * t + s) + 1
    if name == "bounce":
        n, dd = 7.5625, 2.75
        if t < 1 / dd:
            return n * t * t
        if t < 2 / dd:
            t -= 1.5 / dd
            return n * t * t + 0.75
        if t < 2.5 / dd:
            t -= 2.25 / dd
            return n * t * t + 0.9375
        t -= 2.625 / dd
        return n * t * t + 0.984375
    return 1 - (1 - t) ** 3  # out


# --- dithering ---------------------------------------------------------------
@lru_cache(maxsize=8)
def checker(w, h, phase=0):
    m = Image.new("1", (w, h), 0)
    px = m.load()
    for y in range(h):
        for x in range(w):
            if (x + y + phase) % 2 == 0:
                px[x, y] = 1
    return m


def dither_fill(img, mask, col):
    """Remplit 1 pixel sur 2 de la zone 'mask' (L) avec col : ombrage pixel art."""
    m = Image.new("L", img.size, 0)
    m.paste(mask, (0, 0))
    ck = checker(img.size[0], img.size[1]).convert("L")
    from PIL import ImageChops
    m = ImageChops.multiply(m, ck)
    img.paste(Image.new("RGBA", img.size, col), (0, 0), m)


# --- temps -------------------------------------------------------------------
def resolve_time(v, ctx, default=0.0):
    """'w3' → début du 4e mot du beat (relatif au plan), nombre → secondes, 'end-0.5'."""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s.startswith("w"):
        try:
            i = int(s[1:])
        except ValueError:
            return default
        ws = ctx["words"]
        if not ws:
            return default
        return ws[max(0, min(i, len(ws) - 1))] - ctx["t0"]
    if s.startswith("end"):
        off = float(s[3:] or 0)
        return ctx["dur"] + off
    try:
        return float(s)
    except ValueError:
        return default


# --- état animé d'un élément -------------------------------------------------
IN_DUR = {"pop": 0.35, "fade": 0.4, "fall": 0.6, "rise": 0.5, "slide_l": 0.45, "slide_r": 0.45,
          "slide_u": 0.45, "slide_d": 0.45, "draw": 0.8, "type": 0.6, "stamp": 0.3, "grow": 0.5,
          "grow_up": 0.5, "zoom": 0.45, "none": 0.0, "flash": 0.25}


def element_state(el, t, ctx):
    """Calcule (visible, x, y, scale, alpha, reveal, angle) à l'instant t du plan."""
    at = resolve_time(el.get("at", 0), ctx)
    if el.get("_carried"):
        at = -100.0
    lt = t - at
    if lt < 0:
        return None
    x, y = float(el.get("x", LW / 2)), float(el.get("y", LH / 2))
    sx = sy = float(el.get("s", 1))
    a = float(el.get("alpha", 1))
    reveal = 1.0
    # entrée
    pre = el.get("in", "pop")
    idur = float(el.get("in_dur", IN_DUR.get(pre, 0.4)))
    k = 1.0 if idur <= 0 else min(1.0, lt / idur)
    if pre == "pop":
        sx = sy = sx * max(0.0, ease("back", k))
    elif pre == "zoom":
        sx = sy = sx * (0.2 + 0.8 * ease("out", k))
        a *= k
    elif pre == "fade":
        a *= ease("inout", k)
    elif pre == "fall":
        y = y - (1 - ease("bounce", k)) * (y + 40)
    elif pre == "rise":
        y = y + (1 - ease("out", k)) * 60
        a *= min(1, k * 2)
    elif pre == "slide_l":
        x = x - (1 - ease("out", k)) * (x + 60)
    elif pre == "slide_r":
        x = x + (1 - ease("out", k)) * (LW - x + 60)
    elif pre == "slide_u":
        y = y - (1 - ease("out", k)) * 80
    elif pre == "slide_d":
        y = y + (1 - ease("out", k)) * 80
    elif pre in ("draw", "type"):
        reveal = ease("linear" if pre == "type" else "inout", k)
    elif pre == "stamp":
        sx = sy = sx * (1 + 1.6 * (1 - ease("out", k)))
        a *= min(1, k * 3)
    elif pre == "grow":
        sx = sy = sx * ease("out", k)
    elif pre == "grow_up":
        sy = sy * ease("out", k)
    elif pre == "flash":
        a *= 1.0 if int(lt * 16) % 2 == 0 or k >= 1 else 0.0
    # déplacements
    moves = el.get("move") or []
    if isinstance(moves, dict):
        moves = [moves]
    for m in moves:
        ms = resolve_time(m.get("at", 0), ctx)
        if el.get("_carried"):
            ms = -50.0
        md = float(m.get("dur", 1.0))
        if t < ms:
            break
        kk = ease(m.get("ease", "inout"), (t - ms) / max(md, 0.01))
        tx, ty = m.get("to", [x, y])
        x, y = x + (tx - x) * kk, y + (ty - y) * kk
        if "s" in m:
            sx = sy = sx + (float(m["s"]) - sx) * kk
        if "alpha" in m:
            a = a + (float(m["alpha"]) - a) * kk
    # boucle
    loop = el.get("loop")
    gt = ctx["gt"]
    amp = float(el.get("loop_amp", 1))
    if loop == "float":
        y += math.sin(gt * 2.4 + x * 0.1) * 2 * amp
    elif loop == "pulse":
        sx = sy = sx * (1 + 0.06 * amp * (1 if (gt * 2) % 1 < 0.25 else 0))
    elif loop == "blink":
        if (gt * 2) % 1 > 0.6:
            a *= 0.0
    elif loop == "shake":
        r = random.Random(int(gt * 30) + int(x))
        x += r.randint(-1, 1) * amp
        y += r.randint(-1, 1) * amp
    elif loop == "sway":
        x += math.sin(gt * 1.8) * 2 * amp
    elif loop == "bob":
        y += (1 if int(gt * 4) % 2 else 0) * amp
    # sortie
    out = el.get("out")
    if out:
        os_ = resolve_time(out.get("at", "end-0.3"), ctx)
        if t >= os_:
            ko = min(1.0, (t - os_) / float(out.get("dur", 0.3)))
            p = out.get("preset", "fade")
            if p == "fade":
                a *= 1 - ko
            elif p == "fall":
                y += ease("in", ko) * (LH - y + 60)
            elif p == "shrink":
                sx = sy = sx * (1 - ko)
            elif p == "up":
                y -= ease("in", ko) * (y + 60)
    return {"x": x, "y": y, "sx": sx, "sy": sy, "a": max(0.0, min(1.0, a)), "reveal": reveal, "lt": lt}


# --- dessin des éléments -------------------------------------------------------
def _font(kind, size):
    return font({"bold": "pixelify-bold", "mono": "vt323", "small": "silkscreen",
                 "smallb": "silkscreen-bold"}.get(kind, "pixelify-bold"), size)


def draw_sprite_rows(d, rows, colors, x0, y0, px=1):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in (".", " "):
                continue
            c = color(colors.get(ch, "accent" if ch == "#" else ch))
            d.rectangle([x0 + i * px, y0 + j * px, x0 + (i + 1) * px - 1, y0 + (j + 1) * px - 1], fill=c)


def render_element(layer: Image.Image, el: dict, st: dict, ctx):
    """Dessine l'élément à l'échelle 1, centré sur (x, y), dans 'layer' (RGBA)."""
    from . import library
    d = ImageDraw.Draw(layer)
    d.fontmode = "1"
    typ = el.get("type", "rect")
    x, y = st["x"], st["y"]
    rv = st["reveal"]
    if typ in ("rect", "ellipse"):
        w, h = float(el.get("w", 20)), float(el.get("h", 20))
        box = [x - w / 2, y - h / 2, x + w / 2 - 1, y + h / 2 - 1]
        if rv < 1:  # balayage gauche → droite
            box[2] = box[0] + (box[2] - box[0]) * rv
        fill, out = color(el.get("fill", "accent")), color(el.get("outline"))
        ow = int(el.get("width", 1))
        if typ == "rect":
            d.rectangle(box, fill=fill, outline=out, width=ow)
        else:
            d.ellipse(box, fill=fill, outline=out, width=ow)
        if el.get("shade") and fill:
            m = Image.new("L", layer.size, 0)
            md = ImageDraw.Draw(m)
            sb = [box[0] + w * 0.45, box[1] + h * 0.4, box[2], box[3]]
            (md.rectangle if typ == "rect" else md.ellipse)(box, fill=255)
            cut = Image.new("L", layer.size, 0)
            ImageDraw.Draw(cut).ellipse([sb[0] - w * 0.2, sb[1] - h * 0.2, sb[2] + w, sb[3] + h], fill=255)
            from PIL import ImageChops
            dither_fill(layer, ImageChops.multiply(m, cut), darker(fill, 0.45))
    elif typ == "poly":
        pts = [(x + px_, y + py_) for px_, py_ in el.get("pts", [])]
        if len(pts) >= 3:
            d.polygon(pts, fill=color(el.get("fill", "accent")), outline=color(el.get("outline")))
    elif typ == "line":
        pts = [(x + px_, y + py_) for px_, py_ in el.get("pts", [[0, 0], [20, 0]])]
        if rv < 1:
            pts = _partial(pts, rv)
        col, wd = color(el.get("color", "accent")), int(el.get("width", 1))
        if el.get("dash"):
            for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
                n = int(max(abs(a1 - a0), abs(b1 - b0)) / 3) + 1
                for i in range(0, n, 2):
                    p0 = (a0 + (a1 - a0) * i / n, b0 + (b1 - b0) * i / n)
                    p1 = (a0 + (a1 - a0) * (i + 1) / n, b0 + (b1 - b0) * (i + 1) / n)
                    d.line([p0, p1], fill=col, width=wd)
        elif len(pts) >= 2:
            d.line(pts, fill=col, width=wd)
        if el.get("arrow") and len(pts) >= 2 and rv >= 1:
            (a0, b0), (a1, b1) = pts[-2], pts[-1]
            ang = math.atan2(b1 - b0, a1 - a0)
            for s_ in (2.5, -2.5):
                d.line([(a1, b1), (a1 - 5 * math.cos(ang + s_ * 0.3), b1 - 5 * math.sin(ang + s_ * 0.3))], fill=col, width=wd)
    elif typ == "sprite":
        if el.get("icon"):
            from ..gfx import ICONS
            el = dict(el, art=ICONS.get(el["icon"], ICONS["bolt"]),
                      colors=el.get("colors") or {"#": el.get("color", "accent"), "+": "pale"})
        rows = el.get("art", [])
        px = int(el.get("px", 1))
        w = max(len(r) for r in rows) * px if rows else 0
        h = len(rows) * px
        draw_sprite_rows(d, rows, el.get("colors", {}), int(x - w / 2), int(y - h / 2), px)
    elif typ in ("text", "counter"):
        if typ == "counter":
            k = ease("out", min(1.0, st["lt"] / float(el.get("dur", 1.2))))
            v = float(el.get("from", 0)) + (float(el.get("to", 0)) - float(el.get("from", 0))) * k
            dec = int(el.get("decimals", 0))
            sep = el.get("sep", " ")
            num = f"{v:,.{dec}f}".replace(",", sep).replace(".", ",") if dec else f"{int(round(v)):,}".replace(",", sep)
            txt = f"{el.get('prefix', '')}{num}{el.get('suffix', '')}"
        else:
            txt = str(el.get("text", ""))
            if el.get("in") == "type":
                txt = txt[: int(round(len(txt) * rv))]
        size = int(el.get("size", 16))
        f = _font(el.get("font", "bold" if size >= 14 else "small"), size)
        col = color(el.get("color", "accent"))
        anchor = {"left": "lm", "right": "rm"}.get(el.get("align"), "mm")
        lines = txt.split("\n")
        lh = int(size * 1.1)
        for i, ln in enumerate(lines):
            yy = y + (i - (len(lines) - 1) / 2) * lh
            if el.get("box"):
                tw, th = text_size(ln, f)
                pad = 3
                bx = x - tw / 2 - pad if anchor == "mm" else (x - pad if anchor == "lm" else x - tw - pad)
                d.rectangle([bx, yy - th / 2 - pad, bx + tw + 2 * pad, yy + th / 2 + pad],
                            fill=color(el.get("box_fill")) if el.get("box_fill") else None,
                            outline=color(el.get("box", "accent")) if isinstance(el.get("box"), str) else col)
            if el.get("shadow", size >= 14):
                d.text((x + 1, yy + 1), ln, font=f, fill=color("ink"), anchor=anchor)
            d.text((x, yy), ln, font=f, fill=col, anchor=anchor)
    elif typ == "glow":
        r = float(el.get("r", 40))
        c = color(el.get("color", "accent"))
        for i in range(6, 0, -1):
            rr = r * i / 6
            m = Image.new("L", layer.size, 0)
            ImageDraw.Draw(m).ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
            k = (7 - i) / 6
            ck = checker(layer.size[0], layer.size[1], i % 2).convert("L")
            from PIL import ImageChops
            m = ImageChops.multiply(m, ck) if i > 3 else m
            layer.paste(Image.new("RGBA", layer.size, c[:3] + (int(float(el.get("strength", 0.25)) * 255 * k),)),
                        (0, 0), m)
    elif typ == "particles":
        _particles(d, el, st, ctx)
    elif typ == "person":
        library.person(d, dict(el, _gt=ctx["gt"]), x, y)
    elif typ == "obj":
        library.obj(d, layer, el, x, y, st, ctx)


def _partial(pts, k):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg) * k
    out = [pts[0]]
    for (a, b), l in zip(zip(pts, pts[1:]), seg):
        if total >= l:
            out.append(b)
            total -= l
        else:
            f = total / l if l else 0
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            break
    return out


def _particles(d, el, st, ctx):
    kind = el.get("kind", "dust")
    x, y = st["x"], st["y"]
    w, h = float(el.get("w", 60)), float(el.get("h", 40))
    n = int(el.get("n", 14))
    col = color(el.get("color", "pale"))
    gt = st["lt"]
    rnd = random.Random(el.get("seed", 7))
    for i in range(n):
        ox, oy = rnd.random(), rnd.random()
        sp = 0.4 + rnd.random()
        if kind == "bubbles":   # montent
            yy = y + h / 2 - ((oy * h + gt * 18 * sp) % h)
            xx = x - w / 2 + ox * w + math.sin(gt * 3 + i) * 1.5
            d.point((xx, yy), fill=col) if i % 3 else d.rectangle([xx, yy, xx + 1, yy + 1], outline=col)
        elif kind == "smoke":   # monte et s'élargit
            p = (oy + gt * 0.35 * sp) % 1
            xx = x + (ox - 0.5) * w * (0.3 + p) + math.sin(gt * 2 + i) * 2
            yy = y - p * h
            r = 1 + p * 3
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=col[:3] + (int(200 * (1 - p)),))
        elif kind == "rain":
            yy = y - h / 2 + ((oy * h + gt * 90 * sp) % h)
            xx = x - w / 2 + ox * w
            d.line([(xx, yy), (xx - 1, yy + 3)], fill=col)
        elif kind == "snow":
            yy = y - h / 2 + ((oy * h + gt * 14 * sp) % h)
            xx = x - w / 2 + ox * w + math.sin(gt * 1.5 + i) * 3
            d.point((xx, yy), fill=col)
        elif kind == "sparks":
            p = (oy + gt * 0.8 * sp) % 1
            ang = ox * math.tau
            xx, yy = x + math.cos(ang) * p * w / 2, y + math.sin(ang) * p * h / 2
            d.point((xx, yy), fill=col if p < 0.7 else darker(col))
        elif kind == "stars":
            if (gt * sp + ox) % 1.6 < 1.3:
                d.point((x - w / 2 + ox * w, y - h / 2 + oy * h), fill=col)
        elif kind == "stink":   # vapeurs ondulées (odeur)
            p = (oy + gt * 0.4 * sp) % 1
            xx = x + (ox - 0.5) * w + math.sin(p * 9 + i) * 3
            yy = y - p * h
            d.line([(xx, yy), (xx + 1, yy - 2), (xx, yy - 4)], fill=col[:3] + (int(255 * (1 - p)),))
        elif kind == "confetti":
            yy = y - h / 2 + ((oy * h + gt * 40 * sp) % h)
            xx = x - w / 2 + ox * w + math.sin(gt * 4 + i) * 3
            cc = color(["accent", "red", "blue", "green", "yellow"][i % 5])
            d.rectangle([xx, yy, xx + 1, yy], fill=cc)
        else:  # dust : points qui dérivent
            xx = x - w / 2 + ((ox * w + gt * 4 * sp) % w)
            yy = y - h / 2 + oy * h + math.sin(gt + i) * 2
            d.point((xx, yy), fill=col[:3] + (120,))


def compose(canvas: Image.Image, el: dict, st: dict, ctx):
    """Dessine l'élément puis applique échelle / opacité autour de son ancre."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    base = dict(st, sx=1, sy=1)
    render_element(layer, el, base, ctx)
    sx, sy, a = st["sx"], st["sy"], st["a"]
    if sx <= 0.01 or sy <= 0.01 or a <= 0.01:
        return
    if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
        bbox = layer.getbbox()
        if not bbox:
            return
        crop = layer.crop(bbox)
        ax, ay = st["x"], st["y"]
        if el.get("anchor") == "bottom":
            ay = bbox[3]
        nw, nh = max(1, int(crop.width * sx)), max(1, int(crop.height * sy))
        crop = crop.resize((nw, nh), Image.NEAREST)
        nx = int(ax + (bbox[0] - ax) * sx)
        ny = int(ay + (bbox[1] - ay) * sy)
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        layer.paste(crop, (nx, ny), crop)
    if a < 0.99:
        al = layer.getchannel("A").point(lambda v: int(v * a))
        layer.putalpha(al)
    canvas.alpha_composite(layer)
