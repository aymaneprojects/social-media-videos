"""Mixage audio : voix + nappe d'ambiance synthétique + bruitages de coupe."""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100


def load(path: Path, duration: float) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).copy()
    n = int(duration * SR)
    return np.pad(a, (0, max(0, n - len(a))))[:n]


def drone(duration: float, seed=1) -> np.ndarray:
    t = np.arange(int(duration * SR)) / SR
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    x = (0.5 * np.sin(2 * np.pi * 55 * t) + 0.35 * np.sin(2 * np.pi * 55.4 * t + 1)
         + 0.25 * np.sin(2 * np.pi * 82.4 * t) + 0.12 * np.sin(2 * np.pi * 110.3 * t)) * lfo
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(len(t)).astype(np.float32)
    # bruit "vent" : moyenne glissante = passe-bas grossier
    k = 400
    noise = np.convolve(noise, np.ones(k) / k, mode="same") * 6
    x = x + noise * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t + 2))
    fade = np.minimum(1, np.minimum(t / 1.5, (duration - t) / 1.5))
    return (x * fade * 0.06).astype(np.float32)


def blip(seed: int) -> np.ndarray:
    """Petit glitch numérique (bruit + bip descendant)."""
    rng = np.random.default_rng(seed)
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 35)
    f = 1400 * np.exp(-t * 18) + 300
    tone = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25
    nz = rng.standard_normal(n) * 0.35
    crush = np.round((tone + nz) * 6) / 6
    return (crush * env * 0.18).astype(np.float32)


def boom() -> np.ndarray:
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    f = 70 * np.exp(-t * 2.5) + 35
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    return (x * 0.55).astype(np.float32)


def _env(n, decay):
    t = np.arange(n) / SR
    return t, np.exp(-t * decay)


def sfx_sound(kind: str, seed: int = 0) -> np.ndarray:
    """Petits bruitages synthétiques (aucun fichier externe)."""
    rng = np.random.default_rng(seed)
    if kind == "pop":
        t, e = _env(int(0.07 * SR), 60)
        f = 500 + 900 * np.exp(-t * 50)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * e * 0.10).astype(np.float32)
    if kind == "whoosh":
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        nz = np.convolve(rng.standard_normal(n), np.ones(30) / 30, mode="same")
        e = np.sin(np.pi * t / t[-1]) ** 2
        return (nz * e * 0.5).astype(np.float32)
    if kind in ("thud", "stamp"):
        t, e = _env(int(0.4 * SR), 14 if kind == "thud" else 22)
        f = 90 * np.exp(-t * 6) + 45
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * e * 0.5
        if kind == "stamp":
            x[: int(0.03 * SR)] += rng.standard_normal(int(0.03 * SR)) * 0.25
        return x.astype(np.float32)
    if kind == "ding":
        t, e = _env(int(0.8 * SR), 5)
        return ((np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t)) * e * 0.08).astype(np.float32)
    if kind == "ticks":
        out = np.zeros(int(1.0 * SR), np.float32)
        for i in range(12):
            t, e = _env(int(0.015 * SR), 300)
            k = int(i * 0.08 * SR)
            out[k:k + len(t)] += (np.sin(2 * np.pi * 2400 * t) * e * 0.06).astype(np.float32)
        return out
    if kind == "splash":
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        nz = np.convolve(rng.standard_normal(n), np.ones(8) / 8, mode="same")
        return (nz * np.exp(-t * 6) * 0.35).astype(np.float32)
    if kind == "boom":
        return boom()
    return blip(seed)


def _add(dst, src, at):
    i = int(at * SR)
    if i >= len(dst):
        return
    j = min(len(dst), i + len(src))
    dst[i:j] += src[: j - i]


def build_mix(voice: Path, out: Path, duration: float, cuts: list[float],
              accents: list[float] = (), music: Path | None = None, sfx: list = ()):
    sfx_list = list(sfx)
    v = load(voice, duration)
    bed = load(music, duration) * 0.12 if music else drone(duration)
    sfx = np.zeros_like(v)
    for i, c in enumerate(cuts[1:], 1):
        _add(sfx, blip(i), max(0, c - 0.02))
    _add(sfx, boom(), 0.0)
    for a in accents:
        _add(sfx, boom() * 0.8, a)
    for i, (at, kind) in enumerate(sfx_list):
        _add(sfx, sfx_sound(kind, i), max(0.0, at))
    m = v + bed + sfx
    peak = np.max(np.abs(m)) or 1
    m = m / max(1.0, peak / 0.95)
    pcm = (np.clip(m, -1, 1) * 32767).astype(np.int16)
    raw = out.with_suffix(".raw.wav")
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    # normalisation loudness pour les réseaux (~ -14 LUFS)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", str(SR), "-ac", "2", str(out)], check=True)
    raw.unlink(missing_ok=True)
    return out
