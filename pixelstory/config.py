"""Configuration lue depuis l'environnement ou le fichier .env à la racine."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class Config:
    openrouter_key: str
    writer_model: str
    image_model: str
    tts_model: str
    tts_voice: str
    elevenlabs_key: str
    voice_id: str
    voice_model: str
    voice_stability: float
    voice_style: float
    voice_speed: float
    upload_post_key: str
    upload_post_user: str
    edge_voice: str

    @classmethod
    def load(cls) -> "Config":
        _load_dotenv()
        g = os.environ.get
        return cls(
            openrouter_key=g("OPENROUTER_API_KEY", ""),
            writer_model=g("OPENROUTER_WRITER_MODEL", "anthropic/claude-sonnet-5.5"),
            image_model=g("OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image"),
            # Voix ElevenLabs servie par OpenRouter (/api/v1/audio/speech)
            tts_model=g("OPENROUTER_TTS_MODEL", "elevenlabs/eleven-multilingual-v2"),
            tts_voice=g("OPENROUTER_TTS_VOICE", "daniel"),
            # Optionnel : clé ElevenLabs directe (voix perso / clonées)
            elevenlabs_key=g("ELEVENLABS_API_KEY", ""),
            # Nom(s) de voix de la Voice Library (ex. Benjamin, Yarik) ou voice_id, séparés par des virgules :
            # la première trouvée est utilisée
            voice_id=g("ELEVENLABS_VOICE", "Benjamin,Yarik"),
            voice_model=g("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            voice_stability=float(g("ELEVENLABS_STABILITY", "0.45")),
            voice_style=float(g("ELEVENLABS_STYLE", "0.35")),
            voice_speed=float(g("ELEVENLABS_SPEED", "1.05")),
            upload_post_key=g("UPLOAD_POST_API_KEY", ""),
            # Profil Upload-Post : sinon celui défini dans brands/<marque>/brand.json
            upload_post_user=g("UPLOAD_POST_USER", ""),
            edge_voice=g("EDGE_VOICE", "fr-FR-HenriNeural"),
        )
