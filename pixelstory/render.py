"""Assemblage : timeline, HUD, sous-titres, transitions glitch et encodage ffmpeg."""
from __future__ import annotations

import random
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from . import audio
from .gfx import (BG, DIM, FPS, H, MAUVE, MID, PINK, SHADOW, W, WHITE, background, caption_font,
                  draw_text, frame_box, mix, text_size, ui_font, vignette)
from .scenes import SCENES, SceneContext, scene_end
from .voice import Word

CAP_Y = 618        # ligne des sous-titres
END_CARD = 2.2     # durée du carton de fin (s)
PUNCT = re.compile(r"[.,!?:;…]$")


@dataclass
class Beat:
    index: int
    text: str
    scene: dict
    highlight: set
    start: float = 0.0
    end: float = 0.0
    clock: str | None = None
    image: Image.Image | None = None
    words: list = field(default_factory=list)


def _norm(w: str) -> str:
    return re.sub(r"[^\wÀ-ÿ'’-]", "", w.lower())


def build_beats(story: dict, words: list[Word], total: float) -> list[Beat]:
    beats = []
    for i, b in enumerate(story["beats"]):
        hl = set()
        for h in b.get("highlight", []) or []:
            hl.update(_norm(x) for x in str(h).split())
        beats.append(Beat(i, b["text"], b.get("scene") or {"type": "title", "text": ""}, hl, clock=b.get("clock")))
    for w in words:
        beats[w.beat].words.append(w)
    for i, b in enumerate(beats):
        b.start = 0.0 if i == 0 else (b.words[0].start if b.words else beats[i - 1].start + 1)
    for i, b in enumerate(beats):
        b.end = beats[i + 1].start if i + 1 < len(beats) else total
    return beats


def build_chunks(beats: list[Beat]):
    """Groupe les mots en morceaux de 1 à 3 mots, coupés à la ponctuation."""
    chunks = []
    for b in beats:
        cur = []
        for w in b.words:
            cur.append(w)
            chars = sum(len(x.text) for x in cur)
            if len(cur) >= 3 or chars >= 13 or PUNCT.search(w.text):
                chunks.append((b, cur))
                cur = []
        if cur:
            chunks.append((b, cur))
    out = []
    for i, (b, ws) in enumerate(chunks):
        nxt = chunks[i + 1][1][0].start if i + 1 < len(chunks) else ws[-1].end + 0.8
        out.append({"beat": b, "words": ws, "start": ws[0].start - 0.02, "end": min(nxt, ws[-1].end + 1.2)})
    return out


def _is_highlight(word: str, beat: Beat) -> bool:
    n = _norm(word)
    return bool(n) and (n in beat.highlight or any(c.isdigit() for c in n))


def draw_caption(img, d, chunk, t):
    ws = [w for w in chunk["words"] if t >= w.start - 0.03]
    if not ws:
        return
    size = 42
    parts = [(w.text.upper(), _is_highlight(w.text, chunk["beat"]), w) for w in ws]
    while True:
        f = caption_font(size)
        space = text_size("A", f)[0] * 0.6
        widths = [text_size(p[0], f)[0] for p in parts]
        total = sum(widths) + space * (len(parts) - 1)
        if total <= W - 70 or size <= 26:
            break
        size -= 2
    x = W / 2 - total / 2
    for (txt, hl, w), wd in zip(parts, widths):
        pop = 3 if t - w.start < 0.07 else 0
        col = PINK if hl else WHITE
        d.text((x + 3, CAP_Y + 3 - pop), txt, font=f, fill=SHADOW, anchor="ls")
        d.text((x, CAP_Y - pop), txt, font=f, fill=col, anchor="ls")
        x += wd + space


def _clock_seconds(s: str) -> int:
    nums = [int(x) for x in re.findall(r"\d+", s)] or [0]
    sec = 0
    for n in nums[:3]:
        sec = sec * 60 + n
    return sec


def draw_hud(d, story, beat: Beat, beats, t, total):
    brand = story.get("label", "HISTOIRE VRAIE").upper()
    num = int(story.get("number", 1))
    # coins
    frame_box(d, (14, 84, W - 14, H - 84), PINK, 2, corners_only=True, clen=12)
    # étiquette
    f = ui_font(12)
    tw, _ = text_size(brand, f)
    d.rectangle([26, 100, 26 + tw + 14, 118], fill=PINK)
    d.text((33, 109), brand, font=f, fill=SHADOW, anchor="lm")
    nt = f"N°{num:02d}"
    nw, _ = text_size(nt, f)
    x0 = 26 + tw + 20
    d.rectangle([x0, 100, x0 + nw + 12, 118], outline=PINK, width=2)
    d.text((x0 + 6, 109), nt, font=f, fill=PINK, anchor="lm")
    # progression
    d.text((26, 132), f"{beat.index + 1:02d}", font=ui_font(10), fill=MAUVE, anchor="lm")
    d.rectangle([46, 127, 186, 137], outline=PINK, width=1)
    d.rectangle([48, 129, 48 + int(136 * min(1, t / max(total, 0.1))), 135], fill=PINK)
    # horloge (saute quand un beat définit 'clock', sinon tourne en temps réel)
    base_s, base_t = _clock_seconds(story.get("clock_start", "00:00:00")), 0.0
    for b in beats:
        if b.start > t:
            break
        if b.clock:
            base_s, base_t = _clock_seconds(b.clock), b.start
    sec = int(base_s + (t - base_t))
    clock = f"{(sec // 3600) % 100:02d}:{(sec // 60) % 60:02d}:{sec % 60:02d}"
    d.text((W - 26, 109), clock, font=ui_font(14), fill=WHITE, anchor="rm")
    if story.get("location"):
        d.text((W - 26, 126), story["location"].upper(), font=ui_font(8), fill=MID, anchor="rm")
    if (t * 1.2) % 1 < 0.5:
        d.rectangle([W - 30 - text_size(clock, ui_font(14))[0] - 10, 106, W - 30 - text_size(clock, ui_font(14))[0] - 6, 110], fill=PINK)
    handle = story.get("handle")
    if handle:
        d.text((W - 26, H - 100), handle, font=ui_font(8), fill=DIM, anchor="rm")


def glitch(img: Image.Image, strength: float, seed: int) -> Image.Image:
    rnd = random.Random(seed)
    out = img.copy()
    for _ in range(int(6 + 10 * strength)):
        y = rnd.randint(0, H - 20)
        h = rnd.randint(4, 28)
        dx = int(rnd.randint(-40, 40) * strength)
        band = img.crop((0, y, W, y + h))
        out.paste(band, (dx, y))
        if rnd.random() < 0.4:
            tint = Image.new("RGB", (W, h), PINK)
            out.paste(Image.blend(band, tint, 0.35), (dx, y))
    return out


_OVERLAY = None


def overlay() -> Image.Image:
    """Vignette + scanlines, appliqués en multiplication sur chaque image."""
    global _OVERLAY
    if _OVERLAY is None:
        v = vignette()
        scan = Image.new("L", (W, H), 255)
        sd = ImageDraw.Draw(scan)
        for y in range(0, H, 3):
            sd.line([(0, y), (W, y)], fill=214)
        m = ImageChops.multiply(v, scan)
        _OVERLAY = Image.merge("RGB", (m, m, m))
    return _OVERLAY


def render_video(story: dict, voice_path: Path, words: list[Word], duration: float,
                 images: dict[int, Image.Image], out_path: Path, music: Path | None = None,
                 preview_every: int = 0):
    total = duration + 0.5
    beats = build_beats(story, words, total)
    for b in beats:
        b.image = images.get(b.index)
    chunks = build_chunks(beats)
    full = total + END_CARD
    nframes = int(full * FPS)

    work = out_path.parent / f".{out_path.stem}_work"
    work.mkdir(parents=True, exist_ok=True)
    mix_wav = work / "mix.wav"
    audio.build_mix(voice_path, mix_wav, full, [b.start for b in beats],
                    accents=[b.start + (b.end - b.start) * 0.45 for b in beats if b.scene.get("type") == "dossier"]
                    + [b.start for b in beats if b.scene.get("type") == "alert"],
                    music=music)

    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(mix_wav),
           "-vf", "scale=1080:1920:flags=neighbor", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           "-shortest", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    ov = overlay()
    seed = abs(hash(story.get("id", "x"))) % 10000
    ci = 0
    try:
        for fi in range(nframes):
            t = fi / FPS
            if t >= total:
                img = background("dots").copy()
                d = ImageDraw.Draw(img)
                d.fontmode = "1"
                scene_end(img, d, {}, t - total, END_CARD, SceneContext(),
                          brand=story.get("label", "HISTOIRE VRAIE"), number=int(story.get("number", 1)))
                img = ImageChops.multiply(img, ov)
                proc.stdin.write(img.tobytes())
                continue
            beat = next((b for b in reversed(beats) if b.start <= t), beats[0])
            st = beat.scene
            img = background(st.get("bg", "grid" if st.get("type") in ("checklist", "ecg") else "dots")).copy()
            d = ImageDraw.Draw(img)
            d.fontmode = "1"
            fn = SCENES.get(st.get("type"), SCENES["title"])
            ctx = SceneContext(image=beat.image, seed=seed + beat.index, frame=fi)
            try:
                fn(img, d, st, t - beat.start, beat.end - beat.start, ctx)
            except Exception as e:  # une scène mal paramétrée ne doit pas casser la vidéo
                print(f"[scene {beat.index} {st.get('type')}] {e}")
            draw_hud(d, story, beat, beats, t, total)
            while ci + 1 < len(chunks) and chunks[ci + 1]["start"] <= t:
                ci += 1
            if chunks and chunks[ci]["start"] <= t < chunks[ci]["end"]:
                draw_caption(img, d, chunks[ci], t)
            lt = t - beat.start
            if beat.index > 0 and lt < 3 / FPS:
                img = glitch(img, 1.0 - lt * FPS / 3, seed + fi)
            elif random.Random(seed * 7 + fi // 3).random() < 0.012:
                img = glitch(img, 0.3, fi)
            img = ImageChops.multiply(img, ov)
            if preview_every and fi % preview_every == 0:
                img.save(work / f"preview_{fi:05d}.png")
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg a échoué")
    return out_path
