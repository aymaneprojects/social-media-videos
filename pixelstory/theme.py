"""Thème de couleurs actif (une couleur de fond + une couleur d'accent par domaine).

Toutes les nuances sont dérivées des deux couleurs, ce qui garantit une
identité cohérente quel que soit le domaine. Le reste du code lit `T.*` au
moment du dessin : changer de thème = `apply_theme(...)`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields


def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


WHITE_BASE = (250, 248, 242)


@dataclass
class Theme:
    BG: tuple = (13, 18, 16)
    BG2: tuple = (0, 0, 0)
    GRID: tuple = (0, 0, 0)
    DIM: tuple = (0, 0, 0)
    MID: tuple = (0, 0, 0)
    SOFT: tuple = (0, 0, 0)
    ACCENT: tuple = (184, 245, 58)
    ACCENT2: tuple = (0, 0, 0)
    PALE: tuple = (0, 0, 0)
    WHITE: tuple = WHITE_BASE
    SHADOW: tuple = (0, 0, 0)
    INK: tuple = (0, 0, 0)          # texte foncé sur papier / sur aplat d'accent
    RAMP: list = field(default_factory=list)  # pour recolorer les illustrations

    @classmethod
    def from_colors(cls, bg, accent) -> "Theme":
        bg = hex_rgb(bg) if isinstance(bg, str) else tuple(bg)
        ac = hex_rgb(accent) if isinstance(accent, str) else tuple(accent)
        grey = lambda t: _mix(bg, WHITE_BASE, t)  # noqa: E731
        return cls(
            BG=bg,
            BG2=_mix(bg, ac, 0.07),
            GRID=_mix(bg, ac, 0.13),
            DIM=_mix(bg, ac, 0.28),
            MID=_mix(grey(0.35), ac, 0.35),
            SOFT=_mix(grey(0.62), ac, 0.30),
            ACCENT=ac,
            ACCENT2=_mix(ac, WHITE_BASE, 0.38),
            PALE=_mix(WHITE_BASE, ac, 0.12),
            WHITE=WHITE_BASE,
            SHADOW=_mix(bg, (0, 0, 0), 0.6),
            INK=_mix(bg, (0, 0, 0), 0.3),
            RAMP=[bg, _mix(bg, ac, 0.14), _mix(bg, ac, 0.28), _mix(bg, ac, 0.46),
                  _mix(bg, ac, 0.72), ac, _mix(ac, WHITE_BASE, 0.45), _mix(ac, WHITE_BASE, 0.82)],
        )


T = Theme.from_colors("#0D1210", "#B8F53A")


def apply_theme(theme: Theme):
    """Remplace le thème actif sur place et vide les caches dépendants."""
    for f in fields(Theme):
        setattr(T, f.name, getattr(theme, f.name))
    from . import gfx, render
    gfx.background.cache_clear()
    render._OVERLAY = None
