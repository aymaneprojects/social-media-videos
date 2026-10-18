"""Scénariste « anim » : script narratif puis storyboard animé, plan par plan.

Passe 1 : le script (beats de texte), dans notre formule narrative.
Passe 2 : fact-check.
Passe 3 : le storyboard. Le modèle compose chaque plan avec le moteur
(personnages, objets, sprites ASCII, textes, particules, mouvements), ce qui
rend chaque vidéo visuellement unique.
"""
from __future__ import annotations

import json

from ..config import Config
from ..writer import VERIFY, _chat, _parse_json
from .engine import FIXED
from .library import OBJECT_DOCS

SCRIPT_SYSTEM = """Tu es le scénariste de la marque {brand} : des vidéos verticales (Reels, Shorts) en français qui
racontent des HISTOIRES VRAIES, illustrées en pixel art animé. Domaine : {domain} ({focus}).

FORMULE NARRATIVE (≈ 1 min 45, 270 à 330 mots, 26 à 36 beats, une phrase courte par beat) :
1. ACCROCHE (beat 1) : une image choc et concrète, au présent, désignant un objet ou une personne à l'écran :
   « Ce citron a sauvé plus de marins que tous les canons de la Royal Navy. »
2. CONTRE-INTUITION (beats 2-3) : « Vous pensez sûrement que… Sauf que… ». On parle au spectateur (vous).
3. CONTEXTE SEC : lieu + année (« Cameroun, août 1986. »), le protagoniste en une phrase.
4. ENQUÊTE / ESCALADE : faits concrets, chiffres précis, phrases de 3 à 14 mots, quelques coups de poing de 1-3 mots.
5. UN INDICE À RETENIR : « Retenez bien ce détail : … » (beat marqué "clue": "<icône>"),
   puis plus tard le rappel : « Vous vous souvenez de … ? » qui explique tout.
6. RELANCES : « Mais attendez. », « Le pire, … », « Le plus fou, … ».
7. AVIS PERSONNEL, une fois, sincère : « Je trouve ça génial. » / « J'adore cette idée. » + pourquoi.
8. BONUS final surprenant (conséquence actuelle, chiffre, ironie).
9. FIN EN BOUCLE : « Alors la prochaine fois que vous <geste du quotidien lié à l'accroche>, rappelez-vous que… »
   La phrase reste coupée : elle doit se raccorder grammaticalement à la 1re phrase de la vidéo.
- Faits EXACTS et vérifiables uniquement. Aucun chiffre inventé. Pas de morale lourde, pas d'appel à s'abonner.
- Nombres en chiffres sans espace (1400, 1747). Pas de « : » ni de « ? » isolés précédés d'un espace.
- Icônes possibles pour "clue" : {icons}

Réponds UNIQUEMENT en JSON :
{{"id": "slug-sans-accents", "title": "...",
  "beats": [{{"text": "..."}}, {{"text": "...", "clue": "lemon"}}],
  "post": {{"caption": "légende Instagram (2-3 phrases + question)", "youtube_title": "≤ 70 caractères",
            "linkedin_text": "3-5 lignes, la leçon pro à en tirer", "hashtags": ["#...", "..."]}},
  "sources": ["..."]}}"""

BOARD_SYSTEM = """Tu es réalisateur d'animation pixel art. On te donne un script découpé en beats (phrases).
Pour CHAQUE beat, compose un plan ("shot") avec le moteur décrit ci-dessous. Chaque vidéo doit être
visuellement unique : invente des compositions propres à l'histoire (lieux, objets, personnages, gestes).

TOILE : 180 x 320 pixels logiques (x vers la droite, y vers le bas). Centre utile : x 90, y 100-270.
Le texte-clé se place en haut (y 55-90). Le bas (y > 280) reste presque vide.
Les sujets doivent être GRANDS : un personnage principal px 3-4, un objet principal size 2-4.

PLAN : {{"els": [...], "keep": false, "drop": [], "update": {{}}, "chip": "1747", "bg": "glow|stars|none",
        "camera": {{"zoom": [1, 1.15], "focus": [90, 160]}}}}
- "keep": true reprend les éléments du plan précédent (figés dans leur état final) ; "drop" en retire par id ;
  "update": {{"id": {{"move": [...]}}}} les fait bouger. Utilise keep sur 2-4 beats pour faire évoluer une scène.
- "chip" : petite étiquette de date en haut à gauche.

ÉLÉMENTS (tous : id, x, y, at, in, in_dur, move, loop, out, s, alpha) :
- person : {{"type":"person","px":3,"x":90,"y":260 (= pieds),"top":couleur,"pants","skin":"skin|skin2|skin3",
  "hair","hair_style":"short|long|bun|curly|bald","hat":"fedora|top|cap|helmet|bicorne","hat_color",
  "beard":true|"mustache","glasses":true,"outfit":"shirt|suit|coat|labcoat|dress|uniform","tie",
  "pose":"stand|walk|arms_up|point|hold|think|sit","face":"neutral|happy|sad|surprised|closed","facing":"right|left"}}
- obj : {{"type":"obj","name":NOM,"size":1.5,"color":...}} avec NOM parmi : {objects}
  Options utiles : paper{{title,lines,check,sign}}, card{{lines_text:[...]}}, calendar{{text}}, building{{w,h,sign}},
  bottle{{label,liquid,level}}, barrel{{label}}, coin{{spin,symbol}}, bag{{symbol}}, crowd{{n,w,tops,cheer}},
  head{{brain,zone,rod,rod_k}}, rod{{l,angle}}, arrow{{l,angle}}, wave{{w}}, mountain{{w,h}}, screen{{text}}.
- sprite : {{"type":"sprite","art":["..##..",".####."],"colors":{{"#":"accent","o":"black"}},"px":3}}
  → dessine TOI-MÊME les objets absents de la liste (8 à 20 colonnes, '.' = transparent). Ou {{"icon":"skull"}}.
- text : {{"type":"text","text":"NON.","size":24|16|8,"color":"accent"}} — mots-clés en MAJUSCULES, 1 à 3 mots.
- counter : {{"type":"counter","from":0,"to":1746,"size":24,"dur":1.2,"sep":" " (ou "" pour une année)}}
- rect / ellipse {{w,h,fill,outline,shade}}, line {{pts:[[0,0],[30,10]],dash,arrow}}, poly {{pts}},
  glow {{r,color}} (halo derrière le sujet), particles {{kind:"bubbles|smoke|sparks|rain|snow|stars|stink|confetti|dust",w,h,n,color}}.
ANIMATION :
- "at": secondes depuis le début du plan, ou "w3" = au 4e mot du beat (synchronise l'apparition sur la voix !).
- "in": pop|fade|fall|rise|slide_l|slide_r|slide_u|slide_d|draw|type|stamp|grow|grow_up|zoom|flash|none
- "move": [{{"to":[x,y],"at":"w5","dur":0.8,"ease":"inout|out|in|back|bounce|linear","s":1.2}}]
- "loop": float|pulse|blink|shake|sway|bob ; "out": {{"at":"w8","preset":"fade|fall|shrink|up"}}
COULEURS : thème = accent, accent2, accent_d, accent_dd, pale, soft, mid, dim, ink ; fixes = {colors}.
Garde l'accent du thème comme couleur dominante, et des touches de couleurs fixes pour le sens (rouge = danger).

RÈGLES : 3 à 7 éléments par plan, des entrées décalées sur les mots ("w…"), au moins un mouvement par plan,
un mot-clé texte sur ~1 plan sur 3, jamais deux plans identiques de suite.
Réponds UNIQUEMENT en JSON : {{"shots": [ {{...plan du beat 1...}}, {{...beat 2...}}, ... ]}} (autant que de beats).

EXEMPLE de deux plans :
{example}"""

EXAMPLE = json.dumps([
    {"els": [{"type": "glow", "x": 48, "y": 160, "r": 40},
             {"type": "obj", "name": "lemon", "x": 48, "y": 160, "size": 3.2, "loop": "float"},
             {"type": "text", "text": "VS", "x": 92, "y": 160, "size": 16, "color": "soft", "at": "w7"},
             {"type": "sprite", "art": ["..##########++..", ".############+..", "..##########++..", "...bbbbbbb......",
                                        "..oo.....oo....."], "colors": {"#": "grey2", "+": "steel", "b": "brown", "o": "black"},
              "px": 4, "x": 138, "y": 160, "at": "w10", "in": "slide_r"},
             {"type": "obj", "name": "cross", "x": 138, "y": 160, "size": 2.2, "at": "w13", "in": "stamp"}]},
    {"keep": True, "update": {"p0": {"move": [{"to": [33, 170], "at": 0.1, "dur": 0.6}]}},
     "els": [{"type": "rect", "x": 40, "y": 154, "w": 40, "h": 42, "fill": None, "outline": "accent", "at": 0.8, "in": "fade"}]},
], ensure_ascii=False)


def write_script(topic: str, cfg: Config, brand: dict, dom: dict, verify: bool = True) -> dict:
    sys_ = SCRIPT_SYSTEM.format(brand=brand["name"], domain=dom["label"], focus=dom["focus"],
                                icons=", ".join(dom.get("icons", [])) + ", lemon, coin, skull, clock, brain, heart")
    story = _parse_json(_chat(cfg, [{"role": "system", "content": sys_},
                                    {"role": "user", "content": f"Sujet : {topic}"}]))
    if verify:
        story = _parse_json(_chat(cfg, [{"role": "system", "content": VERIFY.replace("145-170", "270-330")},
                                        {"role": "user", "content": json.dumps(story, ensure_ascii=False)}],
                                  temperature=0.2))
    return story


def write_board(story: dict, cfg: Config) -> dict:
    sys_ = BOARD_SYSTEM.format(objects=OBJECT_DOCS, colors=", ".join(FIXED), example=EXAMPLE)
    numbered = "\n".join(f"{i + 1}. {b['text']}" + (f"  [indice: {b['clue']}]" if b.get("clue") else "")
                         for i, b in enumerate(story["beats"]))
    shots: list = []
    # par paquets de 10 beats pour garder des réponses fiables
    for a in range(0, len(story["beats"]), 10):
        chunk = numbered.split("\n")[a:a + 10]
        ctx = f"Histoire : {story.get('title', '')}\nScript complet :\n{numbered}\n\n" \
              f"Compose UNIQUEMENT les plans des beats {a + 1} à {a + len(chunk)}."
        if shots:
            ctx += "\nDernier plan déjà composé (pour la continuité) :\n" + json.dumps(shots[-1], ensure_ascii=False)
        res = _parse_json(_chat(cfg, [{"role": "system", "content": sys_}, {"role": "user", "content": ctx}],
                                temperature=0.7, max_tokens=16000))
        got = res.get("shots", [])
        shots += (got + [{}] * len(chunk))[: len(chunk)]
    for b, sh in zip(story["beats"], shots):
        b["shot"] = sanitize(sh)
    story["format"] = "anim"
    return story


def sanitize(sh: dict) -> dict:
    """Corrige ce qui casserait le rendu (types inconnus, valeurs hors toile)."""
    from .library import OBJECTS
    ok_types = {"person", "obj", "sprite", "text", "counter", "rect", "ellipse", "line", "poly", "glow", "particles"}
    els = []
    for e in sh.get("els", []) if isinstance(sh, dict) else []:
        if not isinstance(e, dict) or e.get("type") not in ok_types:
            continue
        if e["type"] == "obj" and e.get("name") not in OBJECTS:
            e = {"type": "text", "text": str(e.get("name", "")).upper()[:12], "x": e.get("x", 90),
                 "y": e.get("y", 160), "size": 16, "at": e.get("at", 0)}
        for k, lo, hi in (("x", -40, 220), ("y", -40, 360)):
            try:
                e[k] = max(lo, min(hi, float(e.get(k, 90 if k == "x" else 160))))
            except (TypeError, ValueError):
                e[k] = 90 if k == "x" else 160
        els.append(e)
    out = dict(sh) if isinstance(sh, dict) else {}
    out["els"] = els
    return out


def write_anim_story(topic: str, cfg: Config, brand: dict, dom: dict, verify: bool = True) -> dict:
    story = write_script(topic, cfg, brand, dom, verify)
    return write_board(story, cfg)
