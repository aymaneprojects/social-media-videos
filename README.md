# Histoires vraies en pixel art : Nourlio & Pile ou Face

Ce dépôt produit et publie automatiquement des vidéos verticales de 60 à 65 s (1080×1920, 30 fps) pour Instagram (Reels), YouTube (Shorts) et LinkedIn : des histoires vraies en pixel art, avec HUD, sous-titres mot par mot et glitchs. La narration suit toujours la même formule : accroche choc, date, protagoniste, escalade, retournement, puis question et chute ironique.

## Marques

| Marque | Domaine | Accent |
|---|---|---|
| **NOURLIO** | `nutrition` | vert acide `#B8F53A` |
| **NOURLIO** | `sport` | orange `#FF7A1F` |
| **NOURLIO** | `sante` | cyan `#2EE6D6` |
| **PILE OU FACE** | `business` | or `#F5C542` |

Chaque marque vit dans `brands/<marque>/` : `brand.json` (nom, @handle, logo pixel, voix, couleurs et sujet de chaque domaine, profil Upload-Post) et `topics-<domaine>.txt` (banque de sujets). Pour ajouter un domaine ou une marque, il suffit d'ajouter une entrée ou un dossier : toutes les nuances sont calculées à partir du fond et de l'accent (`pixelstory/theme.py`).

## Le pipeline en 3 étapes

1. **Trouver les sujets** : `--find-topics 10` demande à l'IA des histoires vraies, surprenantes, visuelles, avec retournement et indice, sans doublon avec la banque (`brands/<marque>/topics-<domaine>.txt`) ni avec ce qui est déjà fait (`*.done.txt`).
2. **Générer les animations** : pour chaque sujet, l'IA écrit le script (formule maison : accroche, « vous pensez sûrement… sauf que », indice à retenir puis rappel, « mais attendez », avis personnel, fin en boucle), le fait vérifier, puis compose **un storyboard unique** plan par plan : personnages, objets, sprites dessinés pour l'occasion, mouvements calés sur les mots de la voix.
3. **Générer la vidéo** : voix ElevenLabs, rendu pixel art 180×320 agrandi ×6 (1080×1920), bruitages synchronisés, carton de fin de la marque, puis publication Upload-Post (immédiate, programmée ou en file).

```bash
python make_video.py --brand nourlio --domain sante --find-topics 10   # 1. sujets
python make_video.py --brand nourlio --domain sante --next 3 --publish --queue   # 2 + 3, en file de publication
```

Exemples complets, faits à la main avec le moteur (un univers différent par vidéo) :
`stories/nourlio/nutrition/scorbut-lind.json`, `stories/nourlio/sante/phineas-gage.json`,
`stories/nourlio/sport/hicks-1904-anim.json`, `stories/pile-ou-face/business/lustig-tour-eiffel.json`.

## Pipeline technique

| Étape | Outil |
|---|---|
| Script + découpage en scènes + fact-checking | OpenRouter (`anthropic/claude-sonnet-5.5`) |
| Voix off | ElevenLabs : voix **Benjamin** ou **Yarik** (Voice Library, API ElevenLabs), ou voix par défaut via OpenRouter |
| Synchro mot à mot | horodatage natif ElevenLabs, ou alignement Whisper local pour la voix OpenRouter |
| Illustrations | OpenRouter (`google/gemini-3.1-flash-image`), puis pixelisation, tramage et recoloration aux couleurs du domaine |
| Animations, HUD, sous-titres, sons, encodage | Python (Pillow + numpy) + ffmpeg |
| Publication Instagram / YouTube / LinkedIn | Upload-Post (`POST /api/upload`), programmation possible |

## Installation

```bash
pip install -r requirements.txt     # + ffmpeg installé sur la machine
cp .env.example .env                # puis renseigner les clés
```

- `OPENROUTER_API_KEY` : script, illustrations, et voix si tu n'as pas de clé ElevenLabs.
- `UPLOAD_POST_API_KEY` : publication. Dans Upload-Post, crée un profil par marque (`nourlio`, `pileouface`) et connecte-y les comptes Instagram, YouTube et LinkedIn.
- `ELEVENLABS_API_KEY` : nécessaire pour Benjamin et Yarik. OpenRouter ne sert que les 21 voix ElevenLabs par défaut (daniel, george, adam…). Le script cherche la voix par son nom dans ton compte ou dans la Voice Library et l'ajoute automatiquement. Tu peux aussi mettre directement un `voice_id` dans `ELEVENLABS_VOICE`. Attention : l'accès aux voix de la Voice Library par l'API demande un abonnement ElevenLabs payant.

## Utilisation

```bash
# Une vidéo à partir d'un sujet (script écrit et vérifié par OpenRouter)
python make_video.py --brand nourlio --domain nutrition --topic "Angus Barbieri, 382 jours sans manger"

# Les 3 sujets suivants de la banque du domaine (déplacés dans topics-<domaine>.done.txt)
python make_video.py --brand nourlio --domain sante --next 3

# Relire le script avant de payer la voix et les images
python make_video.py --brand pile-ou-face --domain business --topic "..." --write-only
python make_video.py --story stories/pile-ou-face/business/<id>.json

# Publier (rien n'est publié sans --publish)
python make_video.py --story ... --publish                    # tout de suite, sur les plateformes de la marque
python make_video.py --publish-only output/nourlio/sport/hicks-1904 --schedule 2026-10-20T18:00
python make_video.py --publish-only output/... --dry-run      # affiche ce qui serait envoyé
python make_video.py --publish-only output/... --queue        # prochain créneau libre du calendrier Upload-Post

# Idées de sujets
python make_video.py --brand nourlio --domain sport --ideas 15
```

Chaque vidéo est rangée dans `output/<marque>/<domaine>/<id>/` : `video.mp4`, `caption.txt`, `story.json`, `voice.mp3`, plus `publish.json` une fois publiée (ce fichier empêche de publier deux fois ; `--force` pour passer outre).

Options utiles : `--reuse-voice` (re-rendu sans repayer la voix), `--no-images`, `--music fichier.mp3`, `--number 12`, `--platforms instagram,youtube`, `--voice edge` (voix gratuite pour tester).

## Format animé (`"format": "anim"`, par défaut)

Chaque beat (phrase dite) peut ouvrir un plan (`shot`) composé d'éléments :

```json
{"text": "Et pour les deux derniers, deux oranges et un citron par jour.",
 "shot": {"els": [
   {"type": "glow", "x": 90, "y": 160, "r": 50},
   {"type": "obj", "name": "orange", "x": 42, "y": 160, "size": 2.6, "at": "w5"},
   {"type": "obj", "name": "lemon", "x": 138, "y": 160, "size": 2.6, "at": "w9"},
   {"type": "text", "text": "PAR JOUR", "x": 90, "y": 215, "size": 16, "at": "w10", "in": "pop"}]}}
```

- Toile 180×320 ; `"at": "w5"` = apparition au 6e mot de la phrase (synchro voix).
- Éléments : `person` (personnage paramétrique : tenue, coiffure, chapeau, pose, expression), `obj` (une quarantaine d'objets : `pixelstory/anim/library.py`), `sprite` (dessin ASCII libre), `text`, `counter`, `rect`, `ellipse`, `line`, `poly`, `glow`, `particles`.
- Animations : `in` (pop, fall, slide, draw, type, stamp…), `move` (déplacements), `loop` (float, pulse, shake…), `out`.
- `"keep": true` prolonge la scène précédente ; `"clue": "lemon"` ajoute un indice dans la barre « INDICES ».

## Ancien format à scènes types (`--format hud`)

Chaque *beat* correspond à une phrase dite, associée à une scène animée. Exemple complet : `stories/nourlio/sport/hicks-1904.json`.

```json
{"text": "Sur 32 coureurs, seuls 14 arrivent.", "highlight": ["14"],
 "scene": {"type": "grid", "total": 32, "highlight": 14, "icon": "runner", "label": "À L'ARRIVÉE"}}
```

Scènes disponibles : `title`, `date`, `profile`, `number`, `grid`, `checklist`, `gauge`, `route`, `alert`, `icon`, `clock`, `dossier`, `ecg`, `bars`, `image`. Les paramètres sont décrits dans `pixelstory/scenes.py` (`SCENE_DOCS`). Ajoute `"image": "prompt en anglais"` à un beat pour lui générer une illustration, et `"clock": "18:31:53"` pour faire sauter l'horloge du HUD.

## Code

```
make_video.py          CLI
pixelstory/brand.py    chargement des marques et domaines
pixelstory/theme.py    palette dérivée de (fond, accent)
pixelstory/publish.py  publication Upload-Post
pixelstory/topics.py   étape 1 : recherche de sujets sans doublon
pixelstory/anim/       moteur d'animation (engine, library, render) + scénariste storyboard (writer)
pixelstory/writer.py   prompts OpenRouter du format hud (+ fact-check partagé)
pixelstory/voice.py    ElevenLabs / OpenRouter TTS + alignement Whisper / Edge (secours)
pixelstory/images.py   génération OpenRouter + style pixel aux couleurs du domaine
pixelstory/scenes.py   catalogue de scènes animées
pixelstory/render.py   timeline, HUD, sous-titres, glitchs, encodage ffmpeg
pixelstory/audio.py    nappe d'ambiance, bruitages, loudness -14 LUFS
assets/fonts/          VT323, Silkscreen, Pixelify Sans (licence OFL)
```
