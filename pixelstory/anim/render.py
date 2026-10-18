"""Rendu d'une histoire au format « anim » (storyboard plan par plan)."""
from __future__ import annotations

import copy
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from .. import audio
from ..gfx import ICONS, font, text_size
from ..theme import T, _mix
from ..voice import Word
from .engine import LH, LW, SCALE, color, compose, draw_sprite_rows, element_state, resolve_time

FPS = 30
END_CARD = 2.4


def _bake(el: dict, ctx_end: dict) -> dict:
    """Fige un élément dans son état final pour le reporter au plan suivant."""
    e = copy.deepcopy(el)
    st = element_state(dict(e, out=None), 1e4, ctx_end)
    if st:
        e["x"], e["y"] = st["x"], st["y"]
        if e.get("in") not in ("pop", "grow", "zoom", "stamp"):
            pass
    for m in (e.get("move") or []) if isinstance(e.get("move"), list) else [e.get("move")] if e.get("move") else []:
        if "s" in m:
            e["s"] = m["s"]
        if "alpha" in m:
            e["alpha"] = m["alpha"]
    e.pop("move", None)
    e.pop("out", None)
    e["in"] = "none"
    e["at"] = 0
    if e.get("type") == "counter":
        e["from"] = e.get("to", 0)
    return e


class Shot:
    def __init__(self, idx, spec, beats_idx, t0, t1, words):
        self.idx = idx
        self.spec = spec
        self.beats = beats_idx
        self.t0, self.t1 = t0, t1
        self.words = words  # temps absolus des mots du premier beat du plan
        self.els: list[dict] = []

    def ctx(self, t, gt):
        return {"t0": self.t0, "dur": self.t1 - self.t0, "words": self.words, "gt": gt}


def build_shots(story: dict, words: list[Word], total: float) -> list[Shot]:
    beats = story["beats"]
    starts = []
    for i in range(len(beats)):
        ws = [w for w in words if w.beat == i]
        starts.append(ws[0].start if ws else (starts[-1] + 1 if starts else 0))
    starts[0] = 0.0
    shots: list[Shot] = []
    for i, b in enumerate(beats):
        bw = [w.start for w in words if w.beat == i]
        if "shot" in b or not shots:
            shots.append(Shot(len(shots), b.get("shot", {}), [i], starts[i], total, bw))
        else:
            shots[-1].beats.append(i)
            shots[-1].words += bw  # "w" indexe aussi les mots des beats suivants du même plan
    for a, b in zip(shots, shots[1:]):
        a.t1 = b.t0
    # éléments (avec report d'un plan à l'autre)
    prev: list[dict] = []
    uid = 0
    for sh in shots:
        sp = sh.spec
        carried = []
        if sp.get("keep"):
            drop = set(sp.get("drop", []))
            pctx = shots[sh.idx - 1].ctx(0, 0)
            for e in prev:
                if e.get("id") in drop:
                    continue
                be = _bake(e, pctx)
                upd = (sp.get("update") or {}).get(e.get("id"))
                if upd:
                    be.update(copy.deepcopy(upd))
                carried.append(be)
        new = []
        for e in sp.get("els", []):
            e = copy.deepcopy(e)
            if "id" not in e:
                uid += 1
                e["id"] = f"_e{uid}"
            new.append(e)
        sh.els = carried + new
        prev = sh.els
    return shots


def collect_sfx(shots: list[Shot]) -> list[tuple[float, str]]:
    out = []
    for sh in shots:
        c = sh.ctx(0, 0)
        for e in sh.els:
            if e.get("in") == "none":
                continue
            t = sh.t0 + resolve_time(e.get("at", 0), c)
            kind = e.get("sfx") or {"stamp": "stamp", "fall": "thud", "pop": "pop", "slide_l": "whoosh",
                                    "slide_r": "whoosh", "zoom": "whoosh", "flash": "ding"}.get(e.get("in", "pop"))
            if e.get("type") == "counter" and not e.get("sfx"):
                kind = "ticks"
            if kind and kind != "none":
                out.append((t, kind))
        for s in sh.spec.get("sfx", []):
            out.append((sh.t0 + resolve_time(s.get("at", 0), c), s.get("kind", "pop")))
    out.sort()
    # pas plus d'un « pop » toutes les 0,12 s
    res, last = [], {}
    for t, k in out:
        if t - last.get(k, -9) >= 0.12:
            res.append((t, k))
            last[k] = t
    return res


# --- surcouches ----------------------------------------------------------------
def draw_chip(d, text):
    f = font("silkscreen", 8)
    tw, th = text_size(text, f)
    d.rectangle([8, 10, 8 + tw + 7, 22], outline=color("accent"))
    d.text((12, 16), text, font=f, fill=color("accent"), anchor="lm")


def draw_clues(d, clues: list[str], total_slots: int):
    f = font("silkscreen", 8)
    d.text((8, 8), "INDICES", font=f, fill=color("soft"), anchor="lt")
    for i in range(total_slots):
        x0 = 8 + i * 13
        d.rectangle([x0, 19, x0 + 10, 29], outline=color("accent" if i < len(clues) else "dim"))
        if i < len(clues):
            rows = ICONS.get(clues[i], ICONS["bolt"])
            w = max(len(r) for r in rows)
            px = 1
            draw_sprite_rows(d, rows, {"#": "accent", "+": "pale"}, x0 + 5 - w // 2, 24 - len(rows) // 2, px)


def draw_caption(d, words: list[Word], t: float):
    cur = [w for w in words if w.start <= t <= w.end + 0.6]
    if not cur:
        return
    w = cur[-1]
    i = words.index(w)
    chunk = words[max(0, i - 2): i + 1]
    txt = " ".join(x.text for x in chunk).upper()
    f = font("silkscreen", 8)
    d.text((LW // 2 + 1, LH - 46 + 1), txt, font=f, fill=color("ink"), anchor="mm")
    d.text((LW // 2, LH - 46), txt, font=f, fill=color("white"), anchor="mm")


def end_card(img, d, story, t):
    k = min(1.0, t / 0.4)
    logo = ICONS.get(f"logo_{story.get('brand', '')}")
    if logo:
        px = max(1, int(5 * k))
        w = max(len(r) for r in logo) * px
        draw_sprite_rows(d, logo, {"#": "accent", "+": "accent2"}, LW // 2 - w // 2, 92 - len(logo) * px // 2, px)
    if k < 1:
        return
    d.text((LW // 2 + 1, 151), story.get("brand_name", ""), font=font("pixelify-bold", 24), fill=color("ink"), anchor="mm")
    d.text((LW // 2, 150), story.get("brand_name", ""), font=font("pixelify-bold", 24), fill=color("white"), anchor="mm")
    dom = story.get("domain_label", "")
    if dom:
        f = font("silkscreen", 8)
        tw, _ = text_size(dom, f)
        d.rectangle([LW // 2 - tw // 2 - 4, 168, LW // 2 + tw // 2 + 4, 179], fill=color("accent"))
        d.text((LW // 2, 174), dom, font=f, fill=color("ink"), anchor="mm")
    if story.get("handle") and t > 0.6:
        d.text((LW // 2, 200), story["handle"], font=font("pixelify-bold", 16), fill=color("accent"), anchor="mm")
        if int(t * 2) % 2 == 0:
            d.text((LW // 2, 220), "ABONNE-TOI POUR LA SUITE", font=font("silkscreen", 8), fill=color("mid"), anchor="mm")


_BG = {}


def background(kind: str) -> Image.Image:
    key = (kind, T.BG, T.ACCENT)
    if key in _BG:
        return _BG[key]
    img = Image.new("RGBA", (LW, LH), T.BG + (255,))
    d = ImageDraw.Draw(img)
    if kind in ("glow", "stars"):
        cx, cy = LW / 2, LH * 0.42
        for i in range(10, 0, -1):
            r = 18 + i * 9
            c = _mix(T.BG, T.ACCENT, 0.012 * (11 - i))
            d.ellipse([cx - r, cy - r * 1.1, cx + r, cy + r * 1.1], fill=c + (255,))
    if kind == "stars":
        rnd = random.Random(3)
        for _ in range(40):
            d.point((rnd.randrange(LW), rnd.randrange(LH)), fill=_mix(T.BG, T.PALE, 0.35) + (255,))
    _BG[key] = img
    return img


def vignette_mask():
    if "vig" not in _BG:
        m = Image.new("L", (LW, LH), 0)
        px = m.load()
        for y in range(LH):
            for x in range(LW):
                dx, dy = (x - LW / 2) / (LW * 0.62), (y - LH * 0.45) / (LH * 0.6)
                px[x, y] = int(255 * max(0.0, min(1.0, (dx * dx + dy * dy) - 0.35)))
        _BG["vig"] = m
    return _BG["vig"]


def render_anim(story: dict, voice_path: Path, words: list[Word], duration: float, out_path: Path,
                music: Path | None = None, preview_every: int = 0):
    total = duration + 0.6
    shots = build_shots(story, words, total)
    full = total + END_CARD
    nframes = int(full * FPS)
    work = out_path.parent / f".{out_path.stem}_work"
    work.mkdir(parents=True, exist_ok=True)
    mix_wav = work / "mix.wav"
    sfx = collect_sfx(shots)
    audio.build_mix(voice_path, mix_wav, full, [s.t0 for s in shots], sfx=sfx, music=music)

    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{LW}x{LH}",
           "-r", str(FPS), "-i", "-", "-i", str(mix_wav),
           "-vf", f"scale={LW * SCALE}:{LH * SCALE}:flags=neighbor", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           "-shortest", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    clue_slots = sum(1 for b in story["beats"] if b.get("clue"))
    clue_times = []
    for i, b in enumerate(story["beats"]):
        if b.get("clue"):
            ws = [w for w in words if w.beat == i]
            clue_times.append((ws[0].start if ws else 0, b["clue"]))
    vig = vignette_mask()
    shade = Image.new("RGBA", (LW, LH), T.SHADOW + (255,))
    si = 0
    try:
        for fi in range(nframes):
            t = fi / FPS
            if t >= total:
                img = background("glow").copy()
                d = ImageDraw.Draw(img)
                d.fontmode = "1"
                end_card(img, d, story, t - total)
            else:
                while si + 1 < len(shots) and shots[si + 1].t0 <= t:
                    si += 1
                sh = shots[si]
                lt = t - sh.t0
                img = background(sh.spec.get("bg", story.get("bg", "glow"))).copy()
                c = sh.ctx(lt, t)
                shake = 0
                for e in sh.els:
                    st = element_state(e, lt, c)
                    if st is None:
                        continue
                    try:
                        compose(img, e, st, c)
                    except Exception as ex:  # un élément mal décrit ne casse pas la vidéo
                        print(f"[plan {sh.idx} {e.get('type')}/{e.get('name', '')}] {ex}")
                    if e.get("in") == "stamp" and st["lt"] < 0.25:
                        shake = max(shake, 3)
                    if e.get("in") == "fall" and 0.45 < st["lt"] < 0.6:
                        shake = max(shake, 2)
                # caméra
                cam = sh.spec.get("camera")
                if cam or shake:
                    z0, z1 = (cam or {}).get("zoom", [1, 1])
                    k = min(1.0, lt / max(0.1, sh.t1 - sh.t0))
                    z = z0 + (z1 - z0) * (3 * k * k - 2 * k * k * k)
                    fx, fy = (cam or {}).get("focus", [LW / 2, LH / 2])
                    if shake:
                        r = random.Random(fi)
                        fx += r.randint(-shake, shake)
                        fy += r.randint(-shake, shake)
                    cw, ch = LW / z, LH / z
                    x0 = max(0, min(LW - cw, fx - cw / 2))
                    y0 = max(0, min(LH - ch, fy - ch / 2))
                    img = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((LW, LH), Image.NEAREST)
                img.paste(shade, (0, 0), vig)
                d = ImageDraw.Draw(img)
                d.fontmode = "1"
                got = [k for tt, k in clue_times if tt <= t]
                if clue_slots:
                    draw_clues(d, got, clue_slots)
                elif sh.spec.get("chip") or story.get("chip"):
                    draw_chip(d, str(sh.spec.get("chip") or story.get("chip")))
                if story.get("captions"):
                    draw_caption(d, words, t)
            frame = img.convert("RGB")
            if preview_every and fi % preview_every == 0:
                frame.resize((LW * 2, LH * 2), Image.NEAREST).save(work / f"preview_{fi:05d}.png")
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg a échoué")
    return out_path
