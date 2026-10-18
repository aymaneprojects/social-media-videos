"""Marques et domaines : `brands/<marque>/brand.json`."""
from __future__ import annotations

import json
from pathlib import Path

from . import gfx
from .config import ROOT
from .theme import Theme, apply_theme

BRANDS = ROOT / "brands"


def available() -> dict[str, list[str]]:
    out = {}
    for p in sorted(BRANDS.glob("*/brand.json")):
        out[p.parent.name] = list(json.loads(p.read_text(encoding="utf-8"))["domains"])
    return out


def load_brand(slug: str) -> dict:
    p = BRANDS / slug / "brand.json"
    if not p.exists():
        raise SystemExit(f"Marque inconnue « {slug} ». Disponibles : {', '.join(available())}")
    b = json.loads(p.read_text(encoding="utf-8"))
    b["slug"] = slug
    b["dir"] = p.parent
    gfx.ICONS[f"logo_{slug}"] = b["logo"]
    return b


def domain(brand: dict, name: str | None) -> dict:
    doms = brand["domains"]
    name = name or next(iter(doms))
    if name not in doms:
        raise SystemExit(f"Domaine « {name} » absent de {brand['slug']} : {', '.join(doms)}")
    return {**doms[name], "slug": name}


def activate(brand: dict, dom: dict):
    """Applique les couleurs du domaine à tout le rendu."""
    apply_theme(Theme.from_colors(dom["bg"], dom["accent"]))


def topics_file(brand: dict, dom: dict) -> Path:
    return Path(brand["dir"]) / f"topics-{dom['slug']}.txt"
