"""Voix off.

Moteurs :
- elevenlabs (défaut si ELEVENLABS_API_KEY) : API ElevenLabs directe, voix de la
  Voice Library choisie par nom (Benjamin, Yarik...), horodatage natif par caractère.
- openrouter : voix ElevenLabs par défaut servie par OpenRouter (/api/v1/audio/speech).
  L'API renvoie l'audio brut sans horodatage : on aligne ensuite chaque mot du
  script sur l'audio avec Whisper (en local).
- edge : secours gratuit (Edge TTS), pour tester sans clé.

Tous renvoient la liste des mots avec début/fin, ce qui synchronise sous-titres
et changements de scène au mot près.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import Config


@dataclass
class Word:
    text: str
    start: float
    end: float
    beat: int


def duration_of(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def _word_spans(texts: list[str]):
    """Découpe le texte complet en mots avec leurs positions (début, fin, index du beat)."""
    full, spans = "", []
    for bi, t in enumerate(texts):
        if full:
            full += " "
        base = len(full)
        full += t
        for m in re.finditer(r"\S+", t):
            spans.append((m.group(), base + m.start(), base + m.end() - 1, bi))
    return full, spans


EL_API = "https://api.elevenlabs.io"


def resolve_voice(cfg: Config) -> str:
    """Trouve le voice_id à partir d'un nom (« Benjamin », « Yarik »...).

    1. voix déjà dans « My Voices » du compte ;
    2. sinon recherche dans la Voice Library (voix françaises en priorité)
       puis ajout au compte (nécessaire pour l'utiliser via l'API).
    """
    h = {"xi-api-key": cfg.elevenlabs_key}
    for cand in [c.strip() for c in cfg.voice_id.split(",") if c.strip()]:
        if re.fullmatch(r"[A-Za-z0-9]{20}", cand):
            return cand
        r = requests.get(f"{EL_API}/v2/voices", params={"search": cand, "page_size": 50}, headers=h, timeout=30)
        r.raise_for_status()
        mine = [v for v in r.json().get("voices", []) if v["name"].lower().startswith(cand.lower())]
        if mine:
            print(f"  🎙️  voix « {mine[0]['name']} » ({mine[0]['voice_id']})")
            return mine[0]["voice_id"]
        for params in ({"search": cand, "language": "fr", "page_size": 30}, {"search": cand, "page_size": 30}):
            r = requests.get(f"{EL_API}/v1/shared-voices", params=params, headers=h, timeout=30)
            if r.status_code != 200:
                continue
            lib = [v for v in r.json().get("voices", []) if v["name"].lower().startswith(cand.lower())]
            lib.sort(key=lambda v: (v.get("language") != "fr", -(v.get("cloned_by_count") or 0)))
            if lib:
                v = lib[0]
                a = requests.post(f"{EL_API}/v1/voices/add/{v['public_owner_id']}/{v['voice_id']}",
                                  json={"new_name": v["name"]}, headers=h, timeout=30)
                a.raise_for_status()
                vid = a.json().get("voice_id", v["voice_id"])
                print(f"  🎙️  voix « {v['name']} » ajoutée depuis la Voice Library ({vid})")
                return vid
        print(f"  ⚠️  voix « {cand} » introuvable, on essaie la suivante")
    raise RuntimeError(f"Aucune voix trouvée parmi : {cfg.voice_id} (mets directement un voice_id dans ELEVENLABS_VOICE)")


def elevenlabs(texts: list[str], out: Path, cfg: Config) -> list[Word]:
    full, spans = _word_spans(texts)
    vid = resolve_voice(cfg)
    url = f"{EL_API}/v1/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128"
    body = {
        "text": full,
        "model_id": cfg.voice_model,
        "voice_settings": {"stability": cfg.voice_stability, "similarity_boost": 0.8,
                           "style": cfg.voice_style, "use_speaker_boost": True, "speed": cfg.voice_speed},
    }
    for attempt in range(4):
        r = requests.post(url, json=body, headers={"xi-api-key": cfg.elevenlabs_key}, timeout=180)
        if r.status_code == 200:
            break
        if r.status_code in (429, 500, 502, 503) and attempt < 3:
            time.sleep(2 ** (attempt + 1))
            continue
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    data = r.json()
    out.write_bytes(base64.b64decode(data["audio_base64"]))
    al = data["alignment"]
    starts, ends = al["character_start_times_seconds"], al["character_end_times_seconds"]
    n = len(starts)
    words = []
    for txt, a, b, bi in spans:
        a, b = min(a, n - 1), min(b, n - 1)
        words.append(Word(txt, float(starts[a]), float(ends[b]), bi))
    return words


def _norm(w: str) -> str:
    return re.sub(r"[^0-9a-zà-ÿœæ]", "", w.lower())


def align(audio: Path, texts: list[str]) -> list[Word]:
    """Aligne les mots du script sur l'audio (Whisper, timestamps par mot).

    Whisper transcrit avec le script comme contexte ; on apparie ensuite les
    deux suites de mots (difflib) et on interpole les mots non reconnus.
    """
    import difflib

    import numpy as np
    from faster_whisper import WhisperModel

    _, spans = _word_spans(texts)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    pcm = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), compute_type="int8")
    segs, _ = model.transcribe(pcm, language="fr", word_timestamps=True,
                               initial_prompt=" ".join(texts)[:800], vad_filter=False)
    heard = [w for s in segs for w in (s.words or [])]
    a = [_norm(t) for t, *_ in spans]
    b = [_norm(w.word) for w in heard]
    times: list[tuple[float, float] | None] = [None] * len(spans)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        tag, i1, i2, j1, j2 = blk
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (heard[j1 + k].start, heard[j1 + k].end)
        elif tag == "replace" and j2 > j1:  # même passage, découpé autrement : on répartit
            t0, t1 = heard[j1].start, heard[j2 - 1].end
            tot = sum(max(1, len(x)) for x in a[i1:i2])
            acc = 0
            for k in range(i1, i2):
                s0 = t0 + (t1 - t0) * acc / tot
                acc += max(1, len(a[k]))
                times[k] = (s0, t0 + (t1 - t0) * acc / tot)
    dur = len(pcm) / 16000
    # interpolation des trous
    for i in range(len(times)):
        if times[i] is None:
            prev = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0.0)
            nj = next((j for j in range(i + 1, len(times)) if times[j]), None)
            nxt = times[nj][0] if nj is not None else dur
            gap = (nj - i + 1) if nj is not None else (len(times) - i + 1)
            step = (nxt - prev) / gap
            times[i] = (prev + step * 0.2, prev + step)
    matched = sum(1 for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks() for _ in range(blk.size))
    print(f"  🎯 alignement : {matched}/{len(a)} mots reconnus directement")
    return [Word(t, float(s), float(e), bi) for (t, _, _, bi), (s, e) in zip(spans, times)]


def openrouter(texts: list[str], out: Path, cfg: Config) -> list[Word]:
    """Voix ElevenLabs via OpenRouter, puis alignement Whisper."""
    full, _ = _word_spans(texts)
    body = {
        "model": cfg.tts_model,
        "input": full,
        "voice": cfg.tts_voice,
        "response_format": "mp3",
        # transmis tel quel au fournisseur ElevenLabs (ignoré s'il n'est pas reconnu)
        "provider": {"options": {"elevenlabs": {
            "voice_settings": {"stability": cfg.voice_stability, "similarity_boost": 0.75,
                               "style": cfg.voice_style, "use_speaker_boost": True},
        }}},
    }
    if not any(v in cfg.tts_model for v in ("v3", "v4")):  # v3/v4 n'acceptent pas le réglage de vitesse
        body["provider"]["options"]["elevenlabs"]["voice_settings"]["speed"] = cfg.voice_speed
    for attempt in range(4):
        r = requests.post("https://openrouter.ai/api/v1/audio/speech", json=body, timeout=300,
                          headers={"Authorization": f"Bearer {cfg.openrouter_key}", "X-Title": "pixel-stories"})
        if r.status_code == 200 and r.content:
            break
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            time.sleep(2 ** (attempt + 1))
            continue
        raise RuntimeError(f"OpenRouter TTS {r.status_code}: {r.text[:300]}")
    out.write_bytes(r.content)
    return align(out, texts)


def _edge_one(text: str, voice: str, mp3: Path):
    if os.environ.get("SSL_CERT_FILE"):
        import certifi
        certifi.where = lambda: os.environ["SSL_CERT_FILE"]
    import asyncio

    import edge_tts

    bounds = []

    async def run():
        c = edge_tts.Communicate(text, voice, rate="+8%", boundary="WordBoundary")
        with open(mp3, "wb") as f:
            async for ch in c.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    bounds.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7))

    asyncio.run(run())
    return bounds


def edge(texts: list[str], out: Path, cfg: Config, gap: float = 0.22) -> list[Word]:
    """Secours gratuit (qualité inférieure) : synthèse beat par beat puis concaténation."""
    import numpy as np

    sr = 24000
    tmp = out.parent / ".edge"
    tmp.mkdir(exist_ok=True)
    pcm, words, t0 = [], [], 0.0
    for bi, text in enumerate(texts):
        mp3 = tmp / f"{bi}.mp3"
        bounds = _edge_one(text, cfg.edge_voice, mp3)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        a = np.frombuffer(raw, np.int16)
        dur = len(a) / sr
        toks = text.split()
        if len(bounds) == len(toks):
            times = bounds
        else:  # répartition proportionnelle au nombre de caractères
            s0 = bounds[0][0] if bounds else 0.05
            s1 = bounds[-1][1] if bounds else dur - 0.05
            tot = sum(len(x) for x in toks)
            acc, times = 0, []
            for x in toks:
                a0 = s0 + (s1 - s0) * acc / tot
                acc += len(x)
                times.append((a0, s0 + (s1 - s0) * acc / tot))
        for tok, (s, e) in zip(toks, times):
            words.append(Word(tok, t0 + s, t0 + e, bi))
        pcm.append(a)
        pcm.append(np.zeros(int(gap * sr), np.int16))
        t0 += dur + gap
    wav = out.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.concatenate(pcm).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "160k", str(out)], check=True)
    wav.unlink()
    return words


def synthesize(texts: list[str], out: Path, cfg: Config, engine: str = "auto") -> tuple[list[Word], float]:
    if engine == "auto":
        # Les voix de la Voice Library (Benjamin, Yarik...) ne sont accessibles que par l'API ElevenLabs ;
        # OpenRouter ne sert que les voix ElevenLabs par défaut (daniel, george...).
        engine = "elevenlabs" if cfg.elevenlabs_key else ("openrouter" if cfg.openrouter_key else "edge")
    if engine == "openrouter":
        if not cfg.openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY manquante (voir .env.example)")
        print(f"  🎙️  {cfg.tts_model} · voix « {cfg.tts_voice} » via OpenRouter")
        words = openrouter(texts, out, cfg)
    elif engine == "elevenlabs":
        if not cfg.elevenlabs_key:
            raise RuntimeError("ELEVENLABS_API_KEY manquante (voir .env.example)")
        words = elevenlabs(texts, out, cfg)
    else:
        print("⚠️  Voix de secours Edge TTS (ajoute OPENROUTER_API_KEY pour la voix ElevenLabs)")
        words = edge(texts, out, cfg)
    (out.with_suffix(".words.json")).write_text(json.dumps([w.__dict__ for w in words], ensure_ascii=False, indent=1))
    return words, duration_of(out)
