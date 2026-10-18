#!/usr/bin/env python3
"""Génère une vidéo verticale « histoire vraie » en pixel art (nutrition & sport).

Exemples :
  python make_video.py --topic "Thomas Hicks, marathon olympique 1904"
  python make_video.py --story stories/hicks-1904.json
  python make_video.py --topic "..." --write-only      # script seul, à relire avant rendu
  python make_video.py --ideas 20                       # idées d'histoires
  python make_video.py --batch topics.txt               # une vidéo par ligne
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pixelstory import images, voice, writer
from pixelstory.config import ROOT, Config
from pixelstory.render import render_video

OUT = ROOT / "output"
STORIES = ROOT / "stories"


def slug(s: str) -> str:
    s = s.lower()
    for a, b in (("àâä", "a"), ("éèêë", "e"), ("îï", "i"), ("ôö", "o"), ("ùûü", "u"), ("ç", "c")):
        s = re.sub(f"[{a}]", b, s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "histoire"


def next_number() -> int:
    nums = []
    for p in OUT.glob("*/story.json"):
        try:
            nums.append(int(json.loads(p.read_text())["number"]))
        except Exception:  # noqa: BLE001
            pass
    return max(nums, default=0) + 1


def render_story(story: dict, cfg: Config, args) -> Path:
    story.setdefault("label", cfg.brand)
    story.setdefault("handle", cfg.handle)
    if args.number:
        story["number"] = args.number
    story.setdefault("number", next_number())
    sid = slug(story.get("id") or story.get("title", "histoire"))
    d = OUT / sid
    d.mkdir(parents=True, exist_ok=True)
    (d / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"🎙️  Voix ({len(story['beats'])} beats, {writer.word_count(story)} mots)")
    voice_path = d / "voice.mp3"
    words_path = voice_path.with_suffix(".words.json")
    texts = [b["text"] for b in story["beats"]]
    if args.reuse_voice and voice_path.exists() and words_path.exists():
        words = [voice.Word(**w) for w in json.loads(words_path.read_text())]
        dur = voice.duration_of(voice_path)
    else:
        words, dur = voice.synthesize(texts, voice_path, cfg, engine=args.voice)
    print(f"   durée voix : {dur:.1f} s")

    imgs = {}
    if not args.no_images:
        print("🎨 Illustrations (OpenRouter)")
        if not cfg.openrouter_key:
            print("   pas de OPENROUTER_API_KEY → scènes procédurales uniquement")
        imgs = images.generate_all(story, cfg, ROOT / ".cache" / "images")

    print("🎬 Rendu vidéo…")
    out = render_video(story, voice_path, words, dur, imgs, d / "video.mp4",
                       music=Path(args.music) if args.music else None,
                       preview_every=args.preview_every)
    post = story.get("post", {})
    caption = (post.get("caption", "") + "\n\n" + " ".join(post.get("hashtags", []))).strip()
    (d / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    print(f"✅ {out}\n   légende : {d / 'caption.txt'}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic", help="sujet de l'histoire (le script est écrit par OpenRouter)")
    src.add_argument("--story", help="fichier JSON d'histoire déjà écrit")
    src.add_argument("--batch", help="fichier texte : un sujet par ligne")
    src.add_argument("--ideas", type=int, metavar="N", help="propose N idées d'histoires")
    ap.add_argument("--write-only", action="store_true", help="écrit le script JSON sans faire la vidéo")
    ap.add_argument("--no-verify", action="store_true", help="saute la passe de fact-checking")
    ap.add_argument("--no-images", action="store_true", help="pas d'illustrations générées")
    ap.add_argument("--voice", default="auto", choices=["auto", "openrouter", "elevenlabs", "edge"])
    ap.add_argument("--reuse-voice", action="store_true", help="réutilise voice.mp3 déjà généré")
    ap.add_argument("--music", help="musique de fond (sinon nappe synthétique)")
    ap.add_argument("--number", type=int, help="numéro d'épisode affiché (N°xx)")
    ap.add_argument("--preview-every", type=int, default=0, help="sauve une image PNG toutes les N frames")
    args = ap.parse_args()
    cfg = Config.load()

    if args.ideas:
        for t in writer.suggest_topics(cfg, args.ideas):
            print("-", t)
        return

    if args.story:
        render_story(json.loads(Path(args.story).read_text(encoding="utf-8")), cfg, args)
        return

    topics = [args.topic] if args.topic else [
        l.strip() for l in Path(args.batch).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    for topic in topics:
        print(f"✍️  Script : {topic}")
        story = writer.write_story(topic, cfg, verify=not args.no_verify)
        STORIES.mkdir(exist_ok=True)
        p = STORIES / f"{slug(story.get('id') or topic)}.json"
        p.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   → {p} ({writer.word_count(story)} mots)")
        for b in story["beats"]:
            print(f"   · {b['text']}")
        if not args.write_only:
            render_story(story, cfg, args)


if __name__ == "__main__":
    sys.exit(main())
