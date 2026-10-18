#!/usr/bin/env python3
"""Génère (et publie) une vidéo verticale « histoire vraie » en pixel art.

Marques : brands/<marque>/brand.json (nourlio : nutrition, sport, sante · pile-ou-face : business)

Exemples :
  python make_video.py --brand nourlio --domain nutrition --topic "Angus Barbieri, 382 jours sans manger"
  python make_video.py --brand nourlio --domain sport --find-topics 10  # étape 1 : nouveaux sujets
  python make_video.py --brand nourlio --domain sport --next 3          # étapes 2-3 : 3 vidéos animées
  python make_video.py --story stories/hicks-1904.json                  # histoire écrite à la main
  python make_video.py --topic "..." --write-only                       # script seul, à relire
  python make_video.py --story ... --publish                            # + Instagram/YouTube/LinkedIn
  python make_video.py --publish-only output/nourlio/sport/hicks-1904 --schedule 2026-10-20T18:00
  python make_video.py --brand pile-ou-face --domain business --ideas 15
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from pixelstory import brand as brands
from pixelstory import cover, images, publish, topics as topicbank, voice, writer
from pixelstory.anim import writer as anim_writer
from pixelstory.config import ROOT, Config
from pixelstory.anim.render import render_anim
from pixelstory.render import render_video

OUT = ROOT / "output"
STORIES = ROOT / "stories"


def slug(s: str) -> str:
    s = s.lower()
    for a, b in (("àâä", "a"), ("éèêë", "e"), ("îï", "i"), ("ôö", "o"), ("ùûü", "u"), ("ç", "c")):
        s = re.sub(f"[{a}]", b, s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "histoire"


def next_number(b: str, d: str, sid: str) -> int:
    """Numéro d'épisode par marque + domaine (stable si on re-rend la même histoire)."""
    nums = []
    for p in (OUT / b / d).glob("*/story.json"):
        st = json.loads(p.read_text(encoding="utf-8"))
        if p.parent.name == sid and st.get("number"):
            return int(st["number"])
        nums.append(int(st.get("number", 0)))
    return max(nums, default=0) + 1


def prepare(story: dict, args, cfg: Config):
    b = brands.load_brand(args.brand or story.get("brand") or "nourlio")
    d = brands.domain(b, args.domain or story.get("domain"))
    brands.activate(b, d)
    story.update(brand=b["slug"], domain=d["slug"], brand_name=b["name"], domain_label=d["label"],
                 handle=b.get("handle", ""), tagline=b.get("tagline", ""))
    if b.get("voice") and "ELEVENLABS_VOICE" not in os.environ:
        cfg.voice_id = b["voice"]
    if b.get("openrouter_voice") and "OPENROUTER_TTS_VOICE" not in os.environ:
        cfg.tts_voice = b["openrouter_voice"]
    return b, d


def render_story(story: dict, cfg: Config, args) -> Path:
    b, d = prepare(story, args, cfg)
    sid = slug(story.get("id") or story.get("title", "histoire"))
    story["number"] = args.number or story.get("number") or next_number(b["slug"], d["slug"], sid)
    out_dir = OUT / b["slug"] / d["slug"] / sid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"🎞️  {b['name']} · {d['label']} · N°{int(story['number']):02d} · {story.get('title', sid)}")

    print(f"🎙️  Voix ({len(story['beats'])} beats, {writer.word_count(story)} mots)")
    voice_path = out_dir / "voice.mp3"
    words_path = voice_path.with_suffix(".words.json")
    texts = [x["text"] for x in story["beats"]]
    if args.reuse_voice and voice_path.exists() and words_path.exists():
        words = [voice.Word(**w) for w in json.loads(words_path.read_text())]
        dur = voice.duration_of(voice_path)
    else:
        words, dur = voice.synthesize(texts, voice_path, cfg, engine=args.voice)
    print(f"   durée voix : {dur:.1f} s")

    imgs = {}
    if not args.no_images and story.get("format") != "anim":
        if cfg.openrouter_key:
            print("🎨 Illustrations (OpenRouter)")
            imgs = images.generate_all(story, cfg, ROOT / ".cache" / "images")
        else:
            print("🎨 pas de OPENROUTER_API_KEY → scènes procédurales uniquement")

    print("🎬 Rendu vidéo…")
    if story.get("format") == "anim":
        out = render_anim(story, voice_path, words, dur, out_dir / "video.mp4",
                          music=Path(args.music) if args.music else None, preview_every=args.preview_every)
    else:
        out = render_video(story, voice_path, words, dur, imgs, out_dir / "video.mp4",
                           music=Path(args.music) if args.music else None, preview_every=args.preview_every)
    cv = cover.make_cover(out, story)
    print(f"🖼️  miniature : {cv}")
    post = story.get("post", {})
    caption = (post.get("caption", "") + "\n\n" + " ".join(post.get("hashtags", []))).strip()
    (out_dir / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    print(f"✅ {out}")
    if args.publish:
        do_publish(out_dir, story, b, cfg, args)
    return out


def do_publish(out_dir: Path, story: dict, b: dict, cfg: Config, args):
    pub = b.get("publish", {})
    platforms = [p.strip() for p in (args.platforms or ",".join(pub.get("platforms", []))).split(",") if p.strip()]
    user = cfg.upload_post_user or pub.get("user", "")
    if args.dry_run:
        print("🧪 Simulation : champs envoyés à Upload-Post")
        for k, v in publish.build_fields(story, platforms, user, args.schedule, pub.get("timezone"), args.queue):
            print(f"   {k} = {v[:110]!r}{'…' if len(v) > 110 else ''}")
        return
    publish.publish(out_dir / "video.mp4", story, cfg.upload_post_key, user, platforms,
                    schedule=args.schedule, timezone=pub.get("timezone"), force=args.force, queue=args.queue)


def pop_topics(path: Path, n: int) -> list[str]:
    """Prend les n premiers sujets non faits et les déplace dans *.done.txt."""
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    take, rest = lines[:n], lines[n:]
    path.write_text("\n".join(rest) + ("\n" if rest else ""), encoding="utf-8")
    done = path.with_suffix(".done.txt")
    with open(done, "a", encoding="utf-8") as f:
        f.writelines(t + "\n" for t in take)
    return take


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic", help="sujet de l'histoire (script écrit par OpenRouter)")
    src.add_argument("--story", help="fichier JSON d'histoire déjà écrit")
    src.add_argument("--batch", help="fichier texte : un sujet par ligne")
    src.add_argument("--next", type=int, metavar="N", help="N sujets suivants de brands/<marque>/topics-<domaine>.txt")
    src.add_argument("--ideas", type=int, metavar="N", help="propose N idées d'histoires pour le domaine")
    src.add_argument("--find-topics", type=int, metavar="N",
                     help="cherche N nouveaux sujets et les ajoute à la banque du domaine")
    src.add_argument("--publish-only", metavar="DOSSIER", help="publie une vidéo déjà rendue (output/...)")
    ap.add_argument("--brand", help="marque (dossier de brands/), défaut : nourlio")
    ap.add_argument("--domain", help="domaine de la marque (nutrition, sport, sante, business...)")
    ap.add_argument("--format", default="anim", choices=["anim", "hud"],
                    help="anim : animations uniques par histoire (défaut) · hud : ancien format à scènes types")
    ap.add_argument("--write-only", action="store_true", help="écrit le script JSON sans faire la vidéo")
    ap.add_argument("--no-verify", action="store_true", help="saute la passe de fact-checking")
    ap.add_argument("--no-images", action="store_true", help="pas d'illustrations générées")
    ap.add_argument("--voice", default="auto", choices=["auto", "openrouter", "elevenlabs", "edge"])
    ap.add_argument("--reuse-voice", action="store_true", help="réutilise voice.mp3 déjà généré")
    ap.add_argument("--music", help="musique de fond (sinon nappe synthétique)")
    ap.add_argument("--number", type=int, help="numéro d'épisode affiché (N°xx)")
    ap.add_argument("--preview-every", type=int, default=0, help="sauve une image PNG toutes les N frames")
    ap.add_argument("--publish", action="store_true", help="publie via Upload-Post après le rendu")
    ap.add_argument("--platforms", help="ex. instagram,youtube,linkedin (défaut : ceux de la marque)")
    ap.add_argument("--schedule", help="date de publication ISO, ex. 2026-10-20T18:00 (fuseau de la marque)")
    ap.add_argument("--queue", action="store_true",
                    help="place la vidéo dans le prochain créneau libre du calendrier Upload-Post de la marque")
    ap.add_argument("--dry-run", action="store_true", help="affiche ce qui serait publié sans rien envoyer")
    ap.add_argument("--force", action="store_true", help="republie même si déjà publié")
    args = ap.parse_args()
    cfg = Config.load()

    if args.publish_only:
        d = Path(args.publish_only)
        story = json.loads((d / "story.json").read_text(encoding="utf-8"))
        b, _ = prepare(story, args, cfg)
        do_publish(d, story, b, cfg, args)
        return

    if args.story:
        render_story(json.loads(Path(args.story).read_text(encoding="utf-8")), cfg, args)
        return

    b = brands.load_brand(args.brand or "nourlio")
    dom = brands.domain(b, args.domain)
    if args.ideas:
        for t in writer.suggest_topics(cfg, dom, args.ideas):
            print("-", t)
        return
    if args.find_topics:
        path = brands.topics_file(b, dom)
        new = topicbank.find_topics(cfg, b, dom, path, args.find_topics)
        print(f"🔎 {len(new)} nouveaux sujets ajoutés à {path} :")
        for t in new:
            print("  +", t)
        return

    if args.topic:
        topics = [args.topic]
    elif args.next:
        topics = pop_topics(brands.topics_file(b, dom), args.next)
    else:
        topics = [l.strip() for l in Path(args.batch).read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.startswith("#")]
    for topic in topics:
        print(f"✍️  Script [{b['name']} · {dom['label']}] : {topic}")
        if args.format == "anim":
            story = anim_writer.write_anim_story(topic, cfg, b, dom, verify=not args.no_verify)
        else:
            story = writer.write_story(topic, cfg, b, dom, verify=not args.no_verify)
        story.update(brand=b["slug"], domain=dom["slug"])
        STORIES.mkdir(exist_ok=True)
        p = STORIES / b["slug"] / dom["slug"] / f"{slug(story.get('id') or topic)}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   → {p} ({writer.word_count(story)} mots)")
        for x in story["beats"]:
            print(f"   · {x['text']}")
        if not args.write_only:
            args.brand, args.domain = b["slug"], dom["slug"]
            render_story(story, cfg, args)


if __name__ == "__main__":
    sys.exit(main())
