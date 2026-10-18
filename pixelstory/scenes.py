"""Catalogue de scènes animées.

Chaque scène dessine la zone visuelle (au-dessus des sous-titres) pour un
« beat » de l'histoire. Signature commune :

    fn(img, d, p, t, dur, ctx)

- p   : paramètres de la scène (dict venant du JSON de l'histoire)
- t   : temps écoulé depuis le début du beat (s)
- dur : durée du beat (s)
- ctx : SceneContext (illustration éventuelle, graine aléatoire...)
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass

from PIL import Image, ImageDraw

from .gfx import (ICONS, H, W, big_font, blink, caption_font, draw_icon, draw_text, ease_in_out, ease_out, frame_box, icon_size, mix, text_size, typed, ui_font, wave_points, wrap)
from .theme import T

PX0, PY0, PX1, PY1 = 40, 120, 500, 565   # zone visuelle
CX = W // 2
CY = (PY0 + PY1) // 2


@dataclass
class SceneContext:
    image: Image.Image | None = None   # illustration pixelisée (taille panneau)
    seed: int = 0
    frame: int = 0


def _s(p, k, default=""):
    v = p.get(k, default)
    return default if v is None else v


def paste_image(img, ctx, t, dur, box=(PX0, PY0, PX1, PY1), zoom=0.06, dim=1.0):
    if ctx.image is None:
        return False
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    src = ctx.image
    z = 1.0 + zoom * ease_in_out(t / max(dur, 0.01))
    sw, sh = src.size
    cw, ch = int(sw / z), int(sh / z)
    # garder le ratio de la boîte
    r = bw / bh
    if cw / ch > r:
        cw = int(ch * r)
    else:
        ch = int(cw / r)
    ox, oy = (sw - cw) // 2, (sh - ch) // 2
    crop = src.crop((ox, oy, ox + cw, oy + ch)).resize((bw, bh), Image.NEAREST)
    if dim < 1.0:
        crop = Image.blend(Image.new("RGB", crop.size, T.BG), crop, dim)
    img.paste(crop, (x0, y0))
    return True


# --------------------------------------------------------------------------
def scene_title(img, d, p, t, dur, ctx):
    txt = str(_s(p, "text", "")).upper()
    size = 260 if len(txt) <= 2 else (110 if len(txt) <= 8 else 76)
    fnt = big_font(size)
    lines = wrap(txt, fnt, PX1 - PX0 - 20)
    lh = int(size * 0.95)
    y = CY - len(lines) * lh // 2
    prog = ease_out(t / 0.6)
    col = T.ACCENT if len(txt) <= 2 else T.WHITE
    for i, ln in enumerate(lines):
        if len(txt) <= 2 and not blink(t, 1.6) and t > 0.5:
            continue
        draw_text(d, (CX, y + i * lh), typed(ln, prog * 1.2 - i * 0.2), fnt, fill=col, anchor="mt", offset=4)
    sub = str(_s(p, "sub", "")).upper()
    if sub:
        draw_text(d, (CX, y + len(lines) * lh + 10), typed(sub, (t - 0.4) / 0.5), ui_font(16), fill=T.ACCENT, anchor="mt")


def scene_date(img, d, p, t, dur, ctx):
    paste_image(img, ctx, t, dur, dim=0.45)
    date = str(_s(p, "date", "01.01.2000"))
    rnd = random.Random(int(t * 20) + ctx.seed)
    lock = ease_out(t / 0.9) * len(date)
    shown = "".join(c if (i < lock or not c.isdigit()) else str(rnd.randint(0, 9)) for i, c in enumerate(date))
    fnt = big_font(92)
    draw_text(d, (CX, CY - 60), shown, fnt, fill=T.WHITE, anchor="mm", offset=3)
    sub = str(_s(p, "sub", "")).upper()
    if sub:
        draw_text(d, (CX, CY + 8), typed(sub, (t - 0.5) / 0.6), ui_font(16), fill=T.ACCENT, anchor="mm")
    w = int((PX1 - PX0 - 80) * ease_out(t / 0.8))
    d.line([(CX - w // 2, CY + 34), (CX + w // 2, CY + 34)], fill=T.DIM, width=2)


def scene_profile(img, d, p, t, dur, ctx):
    k = ease_out(t / 0.45)
    bx0, by0, bx1, by1 = 58, 160, 482, 470
    cxm, cym = (bx0 + bx1) // 2, (by0 + by1) // 2
    box = (int(cxm - (cxm - bx0) * k), int(cym - (cym - by0) * k), int(cxm + (bx1 - cxm) * k), int(cym + (by1 - cym) * k))
    d.rectangle(box, fill=mix(T.BG, T.BG2, 0.6))
    frame_box(d, box, T.ACCENT, 2)
    if k < 0.98:
        return
    # portrait
    pb = (78, 180, 238, 340)
    d.rectangle(pb, fill=T.GRID)
    if not paste_image(img, ctx, t, dur, box=pb, zoom=0.03):
        bob = int(math.sin(t * 3) * 2)
        draw_icon(d, _s(p, "icon", "person"), (pb[0] + pb[2]) // 2, (pb[1] + pb[3]) // 2 + 6 + bob, scale=11, col=T.SOFT, accent=T.ACCENT)
    frame_box(d, pb, T.SOFT, 1)
    for yy in range(pb[1], pb[3], 4):  # scanlines
        d.line([(pb[0], yy), (pb[2], yy)], fill=T.SHADOW)
    name = str(_s(p, "name", "")).upper().split()
    fx = 256
    fn = caption_font(26)
    for i, part in enumerate(name[:3]):
        draw_text(d, (fx, 190 + i * 30), typed(part, (t - 0.45 - i * 0.15) / 0.4), fn, fill=T.WHITE if i == 0 else T.ACCENT)
    yy = 190 + min(len(name), 3) * 30 + 14
    if _s(p, "age", ""):
        draw_text(d, (fx, yy), typed(f"ÂGE : {p['age']} ANS", (t - 0.9) / 0.4), ui_font(14), fill=T.SOFT)
        yy += 24
    role = str(_s(p, "role", "")).upper()
    for ln in wrap(role, ui_font(14), bx1 - fx - 14)[:3]:
        draw_text(d, (fx, yy), typed(ln, (t - 1.1) / 0.5), ui_font(14), fill=T.PALE)
        yy += 20
    extras = p.get("fields") or []
    ey = 360
    for i, (kk, vv) in enumerate(extras[:4]):
        prog = (t - 1.2 - i * 0.2) / 0.4
        draw_text(d, (78, ey), typed(str(kk).upper(), prog), ui_font(12), fill=T.MID, shadow=False)
        draw_text(d, (200, ey), typed(str(vv).upper(), prog), ui_font(12), fill=T.PALE, shadow=False)
        ey += 22
    draw_text(d, (bx1 - 12, by1 - 10), f"{(int(t*7)%9)+1}/9", ui_font(10), fill=T.MID, anchor="rb", shadow=False)


def _fmt_num(v, decimals, sep=" "):
    s = f"{v:,.{decimals}f}".replace(",", " " if sep == "nbsp" else sep)
    return s.replace(".", ",") if decimals else s


def scene_number(img, d, p, t, dur, ctx):
    paste_image(img, ctx, t, dur, dim=0.35)
    value = float(_s(p, "value", 0) or 0)
    dec = int(_s(p, "decimals", 0) or 0)
    start = float(_s(p, "from", 0) or 0)
    cur = start + (value - start) * ease_out(t / max(0.4, min(1.4, dur * 0.6)))
    txt = f"{_s(p, 'prefix', '')}{_fmt_num(cur, dec)}{_s(p, 'suffix', '')}"
    size = 128 if len(txt) <= 6 else (96 if len(txt) <= 9 else 72)
    fnt = big_font(size)
    col = T.ACCENT if p.get("color", "pink") == "pink" else T.WHITE
    label = str(_s(p, "label", "")).upper()
    if label:
        draw_text(d, (CX, CY - size // 2 - 30), label, ui_font(16), fill=T.SOFT, anchor="mm")
    draw_text(d, (CX, CY - 10), txt, fnt, fill=col, anchor="mm", offset=4)
    sub = str(_s(p, "sub", "")).upper()
    if sub:
        draw_text(d, (CX, CY + size // 2 + 4), typed(sub, (t - 0.3) / 0.5), ui_font(14), fill=T.PALE, anchor="mm")
    # barre de segments
    n = 14
    fill_n = int(n * ease_out(t / max(0.4, dur * 0.6)))
    bw = 14
    x0 = CX - n * (bw + 4) // 2
    y0 = CY + size // 2 + 26
    for i in range(n):
        c = T.ACCENT if i < fill_n else T.DIM
        d.rectangle([x0 + i * (bw + 4), y0, x0 + i * (bw + 4) + bw, y0 + 8], fill=c)


def scene_grid(img, d, p, t, dur, ctx):
    total = max(1, min(60, int(_s(p, "total", 12) or 12)))
    hl = max(0, min(total, int(_s(p, "highlight", 0) or 0)))
    icon = _s(p, "icon", "person")
    cols = int(_s(p, "cols", 0) or 0) or (4 if total <= 12 else (6 if total <= 36 else 8))
    rows = math.ceil(total / cols)
    scale = 6 if total <= 8 else (5 if cols <= 4 else (4 if cols <= 6 else 3))
    iw, ih = icon_size(icon, scale)
    gx, gy = (PX1 - PX0 - 20) / cols, min(80, (PY1 - PY0 - 120) / rows)
    ox = PX0 + 10 + gx / 2
    oy = PY0 + 30 + gy / 2
    appear = min(1.2, dur * 0.4)
    split_t = min(dur * 0.5, appear + 0.4)
    mode = _s(p, "mode", "survivors")  # survivors: les 'highlight' restent roses
    for i in range(total):
        r, c = divmod(i, cols)
        ti = appear * i / total
        if t < ti:
            continue
        x, y = ox + c * gx, oy + r * gy
        pop = ease_out((t - ti) / 0.15)
        is_hl = i < hl if mode == "survivors" else i >= total - hl
        col = T.ACCENT
        if t > split_t and hl:
            k = ease_out((t - split_t) / 0.4)
            col = mix(T.ACCENT, T.ACCENT2, k) if is_hl else mix(T.ACCENT, T.DIM, k)
        draw_icon(d, icon, int(x), int(y + (1 - pop) * 8), scale=scale, col=col)
    label = str(_s(p, "label", "")).upper()
    yy = oy + rows * gy + 10
    if hl and t > split_t:
        draw_text(d, (CX, yy), f"{hl} / {total}", big_font(48), fill=T.ACCENT, anchor="mt")
        yy += 46
    if label:
        draw_text(d, (CX, yy), typed(label, (t - 0.3) / 0.5), ui_font(14), fill=T.SOFT, anchor="mt")


def scene_checklist(img, d, p, t, dur, ctx):
    items = [str(x).upper() for x in (p.get("items") or ["ÉTAPE 1", "ÉTAPE 2", "ÉTAPE 3"])][:5]
    title = str(_s(p, "title", "PROTOCOLE")).upper()
    checked = p.get("checked", len(items))
    checked = len(items) if checked in (None, True) else int(checked)
    bx0, by0, bx1 = 50, 175, 490
    rh = 52
    by1 = by0 + 40 + rh * len(items) + 50
    k = ease_out(t / 0.35)
    d.rectangle([bx0, by0, bx1, by0 + int((by1 - by0) * k)], fill=T.SHADOW)
    frame_box(d, (bx0, by0, bx1, by0 + int((by1 - by0) * k)), T.ACCENT, 2)
    if k < 0.98:
        return
    d.rectangle([bx0 + 8, by0 + 8, bx1 - 8, by0 + 32], fill=T.ACCENT)
    draw_text(d, (CX, by0 + 20), title, ui_font(14), fill=T.SHADOW, anchor="mm", shadow=False)
    span = max(0.6, dur - 0.8)
    for i, it in enumerate(items):
        y = by0 + 44 + i * rh
        ti = 0.35 + span * (i + 1) / (len(items) + 1)
        active = (i == min(len(items) - 1, int((t - 0.35) / (span / (len(items) + 1)))))
        done = i < checked and t > ti
        if active and not done:
            d.rectangle([bx0 + 10, y, bx1 - 10, y + rh - 8], fill=mix(T.SHADOW, T.ACCENT, 0.25))
        num_col = T.ACCENT if (done or active) else T.DIM
        txt_col = T.WHITE if (done or active) else T.MID
        draw_text(d, (bx0 + 24, y + 8), str(i + 1), caption_font(28), fill=num_col, shadow=False)
        f = caption_font(26)
        txt = it
        while text_size(txt, f)[0] > bx1 - bx0 - 120 and len(txt) > 4:
            txt = txt[:-2]
        draw_text(d, (bx0 + 56, y + 8), txt, f, fill=txt_col, shadow=False)
        cb = (bx1 - 50, y + 8, bx1 - 22, y + 36)
        d.rectangle(cb, outline=num_col, width=2)
        if done:
            pts = [(cb[0] + 5, cb[1] + 14), (cb[0] + 12, cb[1] + 21), (cb[2] - 4, cb[1] + 5)]
            d.line(pts, fill=T.ACCENT, width=4)
    status = str(_s(p, "status", "")).upper()
    if status:
        y = by1 - 34
        draw_text(d, (bx0 + 24, y), "STATUT :", ui_font(12), fill=T.SOFT, shadow=False)
        if blink(t, 1.5) or t < 0.8:
            draw_text(d, (bx0 + 120, y), status, ui_font(12), fill=T.ACCENT, shadow=False)


def scene_gauge(img, d, p, t, dur, ctx):
    value = float(_s(p, "value", 50) or 50)
    vmax = float(_s(p, "max", 100) or 100)
    vmin = float(_s(p, "min", 0) or 0)
    unit = str(_s(p, "unit", ""))
    label = str(_s(p, "label", "")).upper()
    frac = max(0.0, min(1.0, (value - vmin) / max(1e-6, vmax - vmin)))
    k = ease_out(t / max(0.5, dur * 0.65)) * frac
    x0, x1 = CX - 34, CX + 34
    y0, y1 = PY0 + 40, PY1 - 70
    d.rectangle([x0, y0, x1, y1], outline=T.SOFT, width=2)
    for i in range(11):
        yy = y1 - (y1 - y0) * i / 10
        d.line([(x1 + 6, yy), (x1 + (16 if i % 5 == 0 else 10), yy)], fill=T.SOFT, width=2)
        if i % 5 == 0:
            v = vmin + (vmax - vmin) * i / 10
            draw_text(d, (x1 + 22, yy), f"{v:g}", ui_font(10), fill=T.MID, anchor="lm", shadow=False)
    fy = y1 - (y1 - y0) * k
    hot = k > 0.8 * 1.0
    col = T.ACCENT if not hot or blink(t, 3) else T.ACCENT2
    if fy < y1 - 5:
        d.rectangle([x0 + 5, int(fy), x1 - 5, y1 - 5], fill=col)
    for yy in range(int(fy), y1 - 5, 6):
        d.line([(x0 + 5, yy), (x1 - 5, yy)], fill=mix(col, T.SHADOW, 0.25))
    cur = vmin + (vmax - vmin) * k
    dec = int(_s(p, "decimals", 0) or 0)
    draw_text(d, (x0 - 16, int(fy)), f"{_fmt_num(cur, dec)}{unit}", big_font(46), fill=T.WHITE, anchor="rm")
    icon = _s(p, "icon", "")
    if icon:
        draw_icon(d, icon, CX, y1 + 34, scale=4, col=T.ACCENT)
    if label:
        draw_text(d, (CX, y0 - 20), label, ui_font(14), fill=T.SOFT, anchor="mm")


def scene_route(img, d, p, t, dur, ctx):
    total = float(_s(p, "total", 42) or 42)
    unit = str(_s(p, "unit", "KM")).upper()
    a = float(_s(p, "from", 0) or 0)
    b = float(_s(p, "to", total) if p.get("to") is not None else total)
    k = ease_in_out(t / max(0.6, dur * 0.85))
    pos = a + (b - a) * k
    x0, x1, y = PX0 + 20, PX1 - 20, CY + 30
    # route ondulée
    pts = wave_points(x0, x1, y, 6, 0.035, 0.0, step=4)
    d.line(pts, fill=T.SOFT, width=3)
    for i in range(0, 11):
        xx = x0 + (x1 - x0) * i / 10
        d.line([(xx, y + 16), (xx, y + 22)], fill=T.MID, width=2)
    draw_text(d, (x0, y + 34), "0", ui_font(12), fill=T.MID, anchor="mt", shadow=False)
    draw_text(d, (x1, y + 34), f"{total:g} {unit}", ui_font(12), fill=T.MID, anchor="mt", shadow=False)
    for m in (p.get("markers") or [])[:6]:
        mx = x0 + (x1 - x0) * float(m.get("at", 0)) / total
        my = y + 6 * math.sin(mx * 0.035)
        draw_icon(d, m.get("icon", "drop"), int(mx), int(my - 30), scale=2, col=T.ACCENT2)
        draw_text(d, (int(mx), int(my - 52)), str(m.get("label", "")).upper(), ui_font(10), fill=T.ACCENT2, anchor="mb", shadow=False)
    rx = x0 + (x1 - x0) * pos / total
    ry = y + 6 * math.sin(rx * 0.035)
    d.line([(x0, y), (rx, ry)], fill=T.ACCENT, width=3)
    ic = "runner" if int(t * 8) % 2 == 0 else "runner2"
    draw_icon(d, _s(p, "icon", ic) if p.get("icon") else ic, int(rx), int(ry - 4), scale=4, col=T.WHITE, anchor="mb")
    draw_text(d, (CX, PY0 + 70), f"{pos:.1f}".replace(".", ",") + f" {unit}", big_font(80), fill=T.ACCENT, anchor="mm")
    label = str(_s(p, "label", "")).upper()
    if label:
        draw_text(d, (CX, PY0 + 120), label, ui_font(14), fill=T.SOFT, anchor="mm")


def scene_alert(img, d, p, t, dur, ctx):
    on = blink(t, 2.5)
    k = ease_out(t / 0.25)
    bx0, by0, bx1, by1 = 70, 170, 470, 500
    if on:
        d.rectangle([bx0 - 6, by0 - 6, bx1 + 6, by1 + 6], outline=mix(T.ACCENT, T.BG, 0.5), width=2)
    d.rectangle([bx0, by0, bx1, by1], fill=mix(T.SHADOW, T.ACCENT, 0.12 if on else 0.05))
    frame_box(d, (bx0, by0, bx1, by1), T.ACCENT, 3)
    # bandes de danger
    for x in range(bx0, bx1, 24):
        d.polygon([(x, by0), (x + 12, by0), (x + 2, by0 + 22), (x - 10, by0 + 22)], fill=T.ACCENT)
    d.rectangle([bx0, by0 + 22, bx1, by0 + 24], fill=T.ACCENT)
    s = 12 + (1 if on else 0)
    draw_icon(d, _s(p, "icon", "skull"), CX, int(CY - 20 + (1 - k) * 30), scale=s, col=T.ACCENT if on else T.ACCENT2, accent=T.WHITE)
    title = str(_s(p, "title", "ALERTE")).upper()
    draw_text(d, (CX, by1 - 66), title, caption_font(34), fill=T.WHITE, anchor="mm")
    sub = str(_s(p, "sub", "")).upper()
    if sub:
        draw_text(d, (CX, by1 - 30), typed(sub, (t - 0.3) / 0.4), ui_font(14), fill=T.ACCENT, anchor="mm")


def scene_icon(img, d, p, t, dur, ctx):
    if paste_image(img, ctx, t, dur, dim=0.4):
        pass
    name = _s(p, "icon", "heart")
    anim = _s(p, "anim", "pulse")
    count = max(1, min(5, int(_s(p, "count", 1) or 1)))
    scale = int(_s(p, "scale", 0) or 0) or (18 if count == 1 else 10)
    iw, _ = icon_size(name, scale)
    gap = 18
    tot = count * iw + (count - 1) * gap
    for i in range(count):
        ti = i * 0.18
        if t < ti:
            continue
        x = CX - tot // 2 + iw // 2 + i * (iw + gap)
        y = CY - 10
        s = scale
        if anim == "pulse":
            s = scale + (1 if (t * 2.2) % 1 < 0.2 else 0)
        elif anim == "bob":
            y += int(math.sin(t * 4 + i) * 6)
        elif anim == "shake":
            x += random.Random(int(t * 30) + i).randint(-3, 3)
        elif anim == "drive":
            x = int(PX0 - 80 + (PX1 - PX0 + 160) * ((t / max(dur, 0.1)) % 1.0))
            y += int((t * 12) % 2)
        elif anim == "drop":
            y = int(CY - 200 + 190 * ease_out((t - ti) / 0.5))
        draw_icon(d, name, x, y, scale=s, col=T.ACCENT, accent=T.PALE)
    label = str(_s(p, "label", "")).upper()
    if label:
        draw_text(d, (CX, PY1 - 40), typed(label, (t - 0.2) / 0.4), ui_font(16), fill=T.SOFT, anchor="mm")


def _parse_hms(s):
    parts = [int(x) for x in re.findall(r"\d+", str(s))] or [0]
    sec = 0
    for x in parts:
        sec = sec * 60 + x
    return sec, len(parts)


def _fmt_hms(sec, n):
    sec = int(sec)
    h, m, s = sec // 3600, (sec // 60) % 60, sec % 60
    if n >= 3:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{sec // 60:02d}:{s:02d}"


def scene_clock(img, d, p, t, dur, ctx):
    a, na = _parse_hms(_s(p, "from", "00:00:00"))
    b, nb = _parse_hms(_s(p, "to", "01:00:00"))
    n = max(na, nb)
    k = ease_in_out(t / max(0.6, dur * 0.8))
    cur = a + (b - a) * k
    r = 120
    cy = CY - 50
    d.ellipse([CX - r, cy - r, CX + r, cy + r], fill=mix(T.BG, T.SOFT, 0.18), outline=T.SOFT, width=3)
    for i in range(60):
        ang = i / 60 * 2 * math.pi
        l = 14 if i % 5 == 0 else 6
        c = T.PALE if i % 5 == 0 else T.MID
        d.line([(CX + (r - 8) * math.sin(ang), cy - (r - 8) * math.cos(ang)),
                (CX + (r - 8 - l) * math.sin(ang), cy - (r - 8 - l) * math.cos(ang))], fill=c, width=2)
    am = (cur / 60) % 60 / 60 * 2 * math.pi
    ah = (cur / 3600) % 12 / 12 * 2 * math.pi
    d.line([(CX, cy), (CX + 60 * math.sin(ah), cy - 60 * math.cos(ah))], fill=T.WHITE, width=6)
    d.line([(CX, cy), (CX + 95 * math.sin(am), cy - 95 * math.cos(am))], fill=T.ACCENT, width=4)
    d.ellipse([CX - 6, cy - 6, CX + 6, cy + 6], fill=T.ACCENT)
    draw_text(d, (CX, cy + r + 50), _fmt_hms(cur, n), big_font(78), fill=T.WHITE, anchor="mm")
    label = str(_s(p, "label", "")).upper()
    if label:
        draw_text(d, (CX, cy + r + 96), label, ui_font(14), fill=T.ACCENT, anchor="mm")


def scene_dossier(img, d, p, t, dur, ctx):
    k = ease_out(t / 0.35)
    bx0, by0, bx1, by1 = 80, 150 + int((1 - k) * 60), 460, 520 + int((1 - k) * 60)
    paper = mix(T.PALE, T.SOFT, 0.25)
    d.rectangle([bx0 + 6, by0 + 6, bx1 + 6, by1 + 6], fill=T.SHADOW)
    d.rectangle([bx0, by0, bx1, by1], fill=paper)
    for yy in range(by0, by1, 3):
        if (yy // 3) % 7 == 0:
            d.line([(bx0, yy), (bx1, yy)], fill=mix(paper, T.SOFT, 0.35))
    ink = T.INK
    draw_text(d, (bx0 + 18, by0 + 16), str(_s(p, "title", "DOSSIER")).upper(), caption_font(26), fill=ink, shadow=False)
    draw_text(d, (bx1 - 18, by0 + 22), str(_s(p, "ref", "N° 1904")).upper(), ui_font(10), fill=T.MID, anchor="ra", shadow=False)
    pb = (bx0 + 18, by0 + 60, bx0 + 128, by0 + 170)
    d.rectangle(pb, fill=T.MID)
    if not paste_image(img, ctx, t, dur, box=pb, zoom=0.0):
        draw_icon(d, _s(p, "icon", "person"), (pb[0] + pb[2]) // 2, (pb[1] + pb[3]) // 2 + 4, scale=8, col=paper)
    y = by0 + 64
    for kk, vv in (p.get("fields") or [])[:7]:
        draw_text(d, (bx0 + 142, y), str(kk).upper(), ui_font(10), fill=T.MID, shadow=False)
        draw_text(d, (bx0 + 142, y + 13), str(vv).upper()[:20], ui_font(12), fill=ink, shadow=False)
        y += 34
    stamp = str(_s(p, "stamp", "")).upper()
    ts = dur * 0.45
    if stamp and t > ts:
        sk = ease_out((t - ts) / 0.15)
        f = caption_font(int(40 + (1 - sk) * 30))
        tw, th = text_size(stamp, f)
        st = Image.new("RGBA", (tw + 40, th + 34), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.fontmode = "1"
        sd.rectangle([2, 2, st.width - 3, st.height - 3], outline=T.ACCENT, width=4)
        sd.text((20, 12), stamp, font=f, fill=T.ACCENT)
        st = st.rotate(-8, expand=True, resample=Image.NEAREST)
        img.paste(st, (CX - st.width // 2, by1 - 150 - st.height // 2), st)


def scene_ecg(img, d, p, t, dur, ctx):
    bpm = float(_s(p, "bpm", 72) or 72)
    y0 = CY + 10
    period = 60.0 / bpm
    for x in range(PX0, PX1, 20):
        d.line([(x, PY0 + 60), (x, PY1 - 60)], fill=T.GRID)
    pts = []
    for x in range(PX0, PX1, 2):
        tt = t * 1.0 - (PX1 - x) / 260.0
        ph = (tt % period) / period
        yv = 0
        if 0.10 < ph < 0.14:
            yv = -10
        elif 0.18 < ph < 0.20:
            yv = 14
        elif 0.20 <= ph < 0.23:
            yv = -70
        elif 0.23 <= ph < 0.26:
            yv = 26
        elif 0.40 < ph < 0.48:
            yv = -14 * math.sin((ph - 0.40) / 0.08 * math.pi)
        pts.append((x, y0 + yv))
    if p.get("flat_after") is not None and t > float(p["flat_after"]):
        pts = [(x, y0) for x, _ in pts]
    d.line(pts, fill=T.ACCENT, width=3)
    beat = (t % period) / period < 0.15
    draw_icon(d, "heart", PX0 + 50, PY0 + 60, scale=4 + (1 if beat else 0), col=T.ACCENT)
    draw_text(d, (PX0 + 90, PY0 + 60), f"{int(bpm)} BPM", big_font(44), fill=T.WHITE, anchor="lm")
    label = str(_s(p, "label", "")).upper()
    if label:
        draw_text(d, (CX, PY1 - 40), label, ui_font(14), fill=T.SOFT, anchor="mm")


def scene_bars(img, d, p, t, dur, ctx):
    items = (p.get("items") or [])[:5]
    if not items:
        return
    unit = str(_s(p, "unit", ""))
    vmax = max(float(it.get("value", 0) or 0) for it in items) or 1
    title = str(_s(p, "title", "")).upper()
    if title:
        draw_text(d, (CX, PY0 + 40), title, ui_font(16), fill=T.SOFT, anchor="mm")
    rh = min(80, (PY1 - PY0 - 100) / len(items))
    for i, it in enumerate(items):
        y = PY0 + 80 + i * rh
        ti = i * 0.25
        k = ease_out((t - ti) / 0.7)
        v = float(it.get("value", 0) or 0)
        bw = int((PX1 - PX0 - 40) * (v / vmax) * k)
        draw_text(d, (PX0 + 10, y), str(it.get("label", "")).upper(), ui_font(12), fill=T.PALE, shadow=False)
        col = T.ACCENT if it.get("highlight") else T.SOFT
        d.rectangle([PX0 + 10, y + 20, PX0 + 10 + max(2, bw), y + 44], fill=col)
        dec = 0 if v == int(v) else 1
        draw_text(d, (PX0 + 18 + bw, y + 32), f"{_fmt_num(v * k, dec)}{unit}", ui_font(14), fill=T.WHITE, anchor="lm")


def scene_image(img, d, p, t, dur, ctx):
    box = (PX0, PY0, PX1, PY1)
    if not paste_image(img, ctx, t, dur, box=box, zoom=0.08):
        scene_icon(img, d, {"icon": p.get("icon", "runner"), "anim": "bob", "label": p.get("label", "")}, t, dur, ctx)
        return
    frame_box(d, box, T.ACCENT, 2, corners_only=True, clen=14)
    label = str(_s(p, "label", "")).upper()
    if label:
        draw_text(d, (PX0 + 10, PY1 - 22), label, ui_font(12), fill=T.ACCENT)


def scene_end(img, d, story, t, dur, ctx):
    """Carton de fin : logo pixel de la marque, nom, domaine, @handle."""
    brand = str(story.get("brand_name", "NOURLIO")).upper()
    logo = f"logo_{story.get('brand', '')}"
    k = ease_out(t / 0.45)
    lw, lh = icon_size(logo, 10) if logo in ICONS else (120, 120)
    if k < 1:
        draw_icon(d, logo if logo in ICONS else "coin", CX, CY - 120, scale=max(1, int(10 * k)), col=T.ACCENT, accent=T.ACCENT2)
        return
    bob = int(math.sin(t * 3) * 3)
    draw_icon(d, logo if logo in ICONS else "coin", CX, CY - 120 + bob, scale=10, col=T.ACCENT, accent=T.ACCENT2)
    draw_text(d, (CX, CY + 10), brand, big_font(72), fill=T.WHITE, anchor="mm", offset=3)
    tag = str(story.get("tagline", "")).upper()
    if tag:
        draw_text(d, (CX, CY + 52), typed(tag, (t - 0.45) / 0.4), ui_font(12), fill=T.SOFT, anchor="mm", shadow=False)
    dom = str(story.get("domain_label", "")).upper()
    if dom:
        f = ui_font(12)
        dw, _ = text_size(dom, f)
        d.rectangle([CX - dw // 2 - 8, CY + 72, CX + dw // 2 + 8, CY + 92], fill=T.ACCENT)
        d.text((CX, CY + 82), dom, font=f, fill=T.INK, anchor="mm")
    handle = story.get("handle", "")
    if handle and t > 0.7:
        draw_text(d, (CX, CY + 130), handle, caption_font(26), fill=T.ACCENT, anchor="mm")
        if blink(t, 1.2):
            draw_text(d, (CX, CY + 172), "ABONNE-TOI POUR LA SUITE", ui_font(10), fill=T.MID, anchor="mm", shadow=False)


SCENES = {
    "title": scene_title,
    "date": scene_date,
    "profile": scene_profile,
    "number": scene_number,
    "grid": scene_grid,
    "checklist": scene_checklist,
    "gauge": scene_gauge,
    "route": scene_route,
    "alert": scene_alert,
    "icon": scene_icon,
    "clock": scene_clock,
    "dossier": scene_dossier,
    "ecg": scene_ecg,
    "bars": scene_bars,
    "image": scene_image,
}

# Utilisé par le prompt du scénariste pour décrire les scènes disponibles
SCENE_DOCS = """
- title    {text, sub}                      gros texte centré
- date     {date:"30.08.1904", sub}          date qui se « verrouille » chiffre par chiffre
- profile  {name, age, role, icon, fields:[[clé,valeur],...]}  fiche personnage (portrait = image générée si 'image' fourni)
- number   {value, from, prefix, suffix, decimals, label, sub}  compteur qui défile jusqu'à la valeur
- grid     {total, highlight, icon, label, mode:"survivors"}   N icônes, 'highlight' restent roses, les autres s'éteignent
- checklist{title, items:[...], checked, status}   liste qui se coche (protocole, recette, étapes)
- gauge    {value, min, max, unit, label, icon}     jauge verticale (température, poids, %)
- route    {total, unit, from, to, markers:[{at,label,icon}], label}  parcours avec coureur qui avance
- alert    {title, sub, icon}                       alerte clignotante (danger, poison, record)
- icon     {icon, anim:"pulse|bob|shake|drive|drop", count, label}  grosse icône animée
- clock    {from:"00:00:00", to:"03:28:53", label}  horloge + chrono qui défile
- dossier  {title, ref, fields:[[clé,valeur]...], stamp, icon}   fiche papier + tampon (verdict, sanction)
- ecg      {bpm, label, flat_after}                 électrocardiogramme qui défile
- bars     {title, unit, items:[{label,value,highlight}]}   barres comparatives (calories, temps...)
- image    {label}                                  illustration pixel art générée (nécessite 'image')
Icônes disponibles : person, runner, skull, drop, car, heart, medal, flask, egg, glass, apple,
dumbbell, bolt, flame, trophy, syringe, flag, pill, plate, bread, fish, scale, bike, clock, brain
"""
