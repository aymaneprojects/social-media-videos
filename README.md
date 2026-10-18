# Histoires vraies en pixel art : nutrition & sport

Ce dépôt produit automatiquement des vidéos verticales de 60 à 65 s (1080×1920, 30 fps) pour les Reels Instagram, TikTok et YouTube Shorts. Le style imite celui des vidéos de référence : pixel art monochrome magenta, HUD (étiquette, numéro d'épisode, horloge, progression), sous-titres mot par mot avec mot-clé en rose, glitchs entre les plans. La narration suit la même formule : accroche choc, date, protagoniste, escalade, retournement, puis question et chute ironique.

## Pipeline

| Étape | Outil |
|---|---|
| Script + découpage en scènes + fact-checking | OpenRouter (`anthropic/claude-sonnet-5.5`) |
| Voix off | ElevenLabs : voix **Benjamin** ou **Yarik** (Voice Library, API ElevenLabs), ou voix par défaut via OpenRouter |
| Synchro mot à mot | horodatage natif ElevenLabs, ou alignement Whisper local pour la voix OpenRouter |
| Illustrations | OpenRouter (`google/gemini-3.1-flash-image`), puis pixelisation, tramage et recoloration magenta |
| Animations, HUD, sous-titres, sons, encodage | Python (Pillow + numpy) + ffmpeg |

## Installation

```bash
pip install -r requirements.txt     # + ffmpeg installé sur la machine
cp .env.example .env                # puis renseigner les clés
```

- `OPENROUTER_API_KEY` : script, illustrations, et voix si tu n'as pas de clé ElevenLabs.
- `ELEVENLABS_API_KEY` : nécessaire pour Benjamin et Yarik. OpenRouter ne sert que les 21 voix ElevenLabs par défaut (daniel, george, adam…). Le script cherche la voix par son nom dans ton compte ou dans la Voice Library et l'ajoute automatiquement. Tu peux aussi mettre directement un `voice_id` dans `ELEVENLABS_VOICE`. Attention : l'accès aux voix de la Voice Library par l'API demande un abonnement ElevenLabs payant.

## Utilisation

```bash
# 1. Une vidéo à partir d'un sujet (script écrit et vérifié par OpenRouter)
python make_video.py --topic "Angus Barbieri, 382 jours sans manger"

# 2. Relire le script avant de payer la voix et les images
python make_video.py --topic "..." --write-only     # → stories/<id>.json, modifiable à la main
python make_video.py --story stories/<id>.json

# 3. Production en série
python make_video.py --batch topics.txt
python make_video.py --ideas 20                      # nouvelles idées d'histoires
```

Chaque vidéo est rangée dans `output/<id>/` : `video.mp4`, `caption.txt` (légende + hashtags), `story.json` et `voice.mp3`.

Options utiles : `--reuse-voice` (re-rendu sans repayer la voix), `--no-images`, `--music fichier.mp3`, `--number 12` (N° d'épisode), `--voice edge` (voix gratuite pour tester).

## Format d'une histoire (`stories/*.json`)

Chaque *beat* correspond à une phrase dite, associée à une scène animée. Exemple complet : `stories/hicks-1904.json`.

```json
{"text": "Sur 32 coureurs, seuls 14 arrivent.", "highlight": ["14"],
 "scene": {"type": "grid", "total": 32, "highlight": 14, "icon": "runner", "label": "À L'ARRIVÉE"}}
```

Scènes disponibles : `title`, `date`, `profile`, `number`, `grid`, `checklist`, `gauge`, `route`, `alert`, `icon`, `clock`, `dossier`, `ecg`, `bars`, `image`. Les paramètres sont décrits dans `pixelstory/scenes.py` (`SCENE_DOCS`). Ajoute `"image": "prompt en anglais"` à un beat pour lui générer une illustration, et `"clock": "18:31:53"` pour faire sauter l'horloge du HUD.

## Code

```
make_video.py          CLI
pixelstory/writer.py   prompts OpenRouter (formule narrative + fact-check)
pixelstory/voice.py    ElevenLabs / OpenRouter TTS + alignement Whisper / Edge (secours)
pixelstory/images.py   génération OpenRouter + style pixel magenta
pixelstory/scenes.py   catalogue de scènes animées
pixelstory/render.py   timeline, HUD, sous-titres, glitchs, encodage ffmpeg
pixelstory/audio.py    nappe d'ambiance, bruitages, loudness -14 LUFS
assets/fonts/          VT323, Silkscreen, Pixelify Sans (licence OFL)
```
