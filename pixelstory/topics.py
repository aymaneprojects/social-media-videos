"""Étape 1 du pipeline : trouver des sujets et alimenter la banque de chaque domaine."""
from __future__ import annotations

import re
from pathlib import Path

from .config import Config
from .writer import _chat, _parse_json

CRITERIA = """Critères d'un bon sujet (tous obligatoires) :
- histoire VRAIE, documentée (sources sérieuses), peu connue du grand public francophone ;
- une accroche choc qui tient en une phrase et désigne quelque chose de visuel (un objet, une personne, un lieu) ;
- un mystère ou un paradoxe, un retournement, et un détail-indice qu'on peut faire « retenir » au spectateur ;
- des chiffres concrets ; une chute ironique ou un bonus actuel ;
- un geste du quotidien lié au sujet pour la fin en boucle (« la prochaine fois que vous… ») ;
- facile à illustrer en pixel art (objets, personnages, lieux simples)."""


def _key(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9àâäéèêëîïôöùûüç ]", " ", s)
    words = [w for w in s.split() if len(w) > 3][:4]
    return " ".join(words)


def known(path: Path) -> list[str]:
    out = []
    for p in (path, path.with_suffix(".done.txt")):
        if p.exists():
            out += [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    return out


def find_topics(cfg: Config, brand: dict, dom: dict, path: Path, n: int = 10) -> list[str]:
    have = known(path)
    prompt = (f"Marque {brand['name']}, domaine {dom['label']} ({dom['focus']}).\n{CRITERIA}\n"
              f"Propose {n + 5} sujets différents, variés en époques et en pays. "
              f"Déjà traités ou prévus (à NE PAS reproposer) :\n- " + "\n- ".join(have[-80:] or ["(aucun)"]) +
              '\nRéponds en JSON : {"topics": [{"topic": "Nom — année — l\'idée en une phrase", '
              '"hook": "phrase d\'accroche", "score": 1-10}]}')
    res = _parse_json(_chat(cfg, [{"role": "user", "content": prompt}], temperature=0.9))
    keys = {_key(h) for h in have}
    fresh = []
    for t in sorted(res.get("topics", []), key=lambda x: -float(x.get("score", 0))):
        k = _key(t.get("topic", ""))
        if k and k not in keys:
            keys.add(k)
            fresh.append(t["topic"].strip())
        if len(fresh) >= n:
            break
    with open(path, "a", encoding="utf-8") as f:
        f.writelines(t + "\n" for t in fresh)
    return fresh
