"""Scénariste : OpenRouter écrit l'histoire (texte + découpage en scènes), puis
une seconde passe vérifie les faits avant la mise en voix."""
from __future__ import annotations

import json
import re
import time

import requests

from .config import Config
from .scenes import SCENE_DOCS

REFERENCE_SCRIPTS = """
EXEMPLE 1 (64 s) :
Il est 4h30 du matin quand le bateau se retourne. / 26 mai 2013, au large du Nigeria. / Harrison Okene, 29 ans, est cuisinier sur un remorqueur. / Il est aux toilettes quand une vague géante couche le navire. / En quelques secondes, le bateau coule. / 30 mètres plus bas, il touche le fond. / Dans le noir complet, Harrison nage à tâtons. / Et il trouve une poche d'air. / Un mètre à peine, sous le plafond d'une cabine. / L'eau glacée lui monte jusqu'à la poitrine. / Autour de lui, ses 11 collègues sont morts. / Les heures passent. Il entend les poissons. / Il sent l'air devenir lourd, chargé de son propre souffle. / Une journée. Deux journées. Personne ne vient. / 60 heures après le naufrage, des plongeurs descendent enfin. / Leur mission : remonter les corps. / L'un d'eux avance dans l'épave avec sa lampe. / Il aperçoit une main. Il la saisit. Et la main serre la sienne. / Harrison est vivant. Mais il ne peut pas remonter d'un coup. / Après trois jours sous pression, ça le tuerait. / On le place alors dans une chambre de décompression pendant encore deux jours et demi. / Il est le seul survivant.

EXEMPLE 2 (61 s) :
Cette nuit-là, un seul homme a eu la fin du monde au bout des doigts. / 26 septembre 1983, en pleine guerre froide. / Stanislav Petrov, officier soviétique, surveille le ciel américain depuis un bunker secret près de Moscou. / Minuit passé. / La sirène hurle. / Le satellite vient de détecter un missile nucléaire tiré depuis les USA. / Puis un deuxième. / Un troisième. / Au total, cinq missiles en route vers l'URSS. / Le protocole est clair. / Il doit prévenir ses chefs. / Et ses chefs riposteront. / Avec tout l'arsenal. / Mais quelque chose cloche. / Une vraie attaque, ce serait des centaines de missiles. / Pas cinq. / Alors il prend une décision folle. / Il signale une erreur du système. / Et il attend. / 10 minutes. / 15. / Rien n'explose. / Le satellite s'était trompé. / Il avait pris des reflets du soleil sur les nuages pour des tirs de missiles. / Petrov a sans doute évité une guerre nucléaire. / Sa récompense ? / Un blâme. / Et une histoire gardée secrète pendant des années.

EXEMPLE 3 (63 s) :
Il y a 212 ans, jour pour jour, Londres a été frappée par une vague. / Une vague de bière. / 17 octobre 1814. / Dans le quartier de St Giles, l'un des plus pauvres de la ville, se dresse la brasserie Meux. / À l'intérieur, une cuve géante de 7 mètres de haut. / Elle contient plus de 600 000 litres de bière brune. / Ce jour-là, un cerclage de fer cède. / Personne ne s'inquiète. / Une heure plus tard, la cuve explose. / Le choc fait éclater les cuves voisines. / Au total, près d'un million et demi de litres jaillissent d'un coup. / Le mur de la brasserie s'effondre. / Une vague brune de plusieurs mètres déferle dans les ruelles. / Les maisons sont inondées jusqu'aux caves, où vivent des familles entières. / Dans l'une d'elles, des proches sont réunis pour veiller un petit garçon mort la veille. / 8 personnes meurent, noyées dans la bière. / Le procès a lieu peu après. / Le verdict ? / Un acte de Dieu. / Personne n'est responsable. / Mieux encore : la brasserie se fait rembourser les taxes sur la bière perdue. / Et le quartier, lui, a gardé l'odeur pendant des mois.
"""

SYSTEM_TEMPLATE = """Tu es le scénariste de la marque {brand} : une série de vidéos verticales (Reels, Shorts) en français,
des HISTOIRES VRAIES racontées en ~60 secondes, en pixel art.
Domaine de cet épisode : {domain} ({focus}).

LA FORMULE NARRATIVE (à respecter strictement, c'est elle qui fait le succès) :
1. ACCROCHE : la 1re phrase balance le fait le plus fou ou une tension immédiate, sans contexte.
2. DATE + LIEU dans la 2e phrase, sèche : « 30 août 1904, Saint-Louis. »
3. PROTAGONISTE : nom, âge, rôle en une phrase.
4. ESCALADE : phrases courtes au présent, une info par phrase, des chiffres précis.
   Alterne phrases moyennes (8-14 mots) et coups de poing (1-3 mots : « Puis un deuxième. » « Pas cinq. »).
5. RETOURNEMENT vers 70 % : « Mais quelque chose cloche. » / « Alors il prend une décision folle. »
6. CHUTE : une question de 2-3 mots (« Sa récompense ? » « Le verdict ? »), une réponse ironique ou
   choquante, puis une dernière phrase qui laisse une trace.
- Ton : sobre, factuel, tension de thriller. Aucun adjectif inutile, aucune morale, aucun « incroyable ».
- Pas d'appel à l'abonnement, pas d'intro « Saviez-vous ».
- 145 à 170 mots au total (≈ 60-65 s de voix), 16 à 26 beats, 16 mots max par beat.
- Écris les nombres en chiffres sauf s'ils sont plus naturels en lettres (« deux jours et demi »).
- Faits EXACTS uniquement. Si un détail est incertain ou légendaire, ne l'utilise pas ou dis-le.

Voici trois scripts de la série (même formule, autres thèmes) :
{refs}

DÉCOUPAGE VISUEL : chaque beat (= une phrase ou un fragment) a une scène animée en pixel art.
Scènes disponibles (type {{paramètres}}) :
{scenes}
Icônes à privilégier pour ce domaine : {icons}
Règles visuelles :
- Ne répète jamais le même type deux beats de suite. Varie beaucoup.
- Le 2e beat est en général une scène « date ». Le protagoniste a une scène « profile ».
- Chaque chiffre important mérite sa scène (number, gauge, grid, clock, bars, route).
- Tous les textes affichés à l'écran sont COURTS (≤ 18 caractères par libellé), en français.
- « image » : prompt EN ANGLAIS décrivant une illustration (personnage, lieu, objet) pour 4 à 7 beats
  maximum, typiquement l'accroche, le profil (portrait), 2-4 moments clés. Ces beats utilisent la scène
  « image », « profile » (portrait), « dossier » ou « date »/« number »/« icon » (en fond).
  Décris un sujet visuel simple, sans texte. Les autres beats n'ont pas de champ image.
- « highlight » : 1 ou 2 mots EXACTS du beat à colorer en rose (le mot qui frappe).
- « clock » (optionnel) : heure affichée dans le HUD quand l'histoire saute dans le temps (« 14:30:00 »).

RÉPONDS UNIQUEMENT avec un objet JSON valide :
{{
  "id": "slug-court-sans-accents",
  "title": "titre interne",
  "location": "VILLE OU LIEU (court, majuscules)",
  "clock_start": "HH:MM:SS",
  "beats": [
    {{"text": "...", "highlight": ["..."], "scene": {{"type": "...", ...}}, "image": "...optionnel..."}}
  ],
  "post": {{"caption": "légende Instagram (2-3 phrases, accroche + question pour les commentaires)",
            "youtube_title": "titre YouTube Shorts accrocheur, 70 caractères max, sans hashtag",
            "linkedin_text": "texte LinkedIn : 3 à 5 lignes courtes, l'histoire en une phrase puis la leçon à en tirer (ton professionnel, sans emoji excessif)",
            "hashtags": ["#... (6 à 10, en français, liés au domaine)"]}},
  "sources": ["références (livre, article, archive) qui appuient les faits"]
}}"""

VERIFY = """Tu es fact-checker. Voici un script de vidéo « histoire vraie » au format JSON.
Vérifie chaque fait : dates, lieux, noms, âges, chiffres, enchaînement des événements.
- Corrige toute erreur dans "text" ET dans les paramètres de "scene" concernés (valeurs, dates, libellés).
- Supprime ou nuance tout détail légendaire non établi.
- Garde la formule, le rythme, le nombre de mots (145-170) et la structure JSON identiques.
- Ajoute un champ "fact_notes": liste courte de ce que tu as vérifié/corrigé et ce qui reste incertain.
Réponds UNIQUEMENT avec le JSON corrigé."""


def _chat(cfg: Config, messages, temperature=0.8, max_tokens=8000) -> str:
    if not cfg.openrouter_key:
        raise RuntimeError("OPENROUTER_API_KEY manquante (voir .env.example)")
    body = {"model": cfg.writer_model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    for attempt in range(4):
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=300,
                          headers={"Authorization": f"Bearer {cfg.openrouter_key}",
                                   "X-Title": "pixel-stories"})
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        if r.status_code in (429, 500, 502, 503) and attempt < 3:
            time.sleep(2 ** (attempt + 1))
            continue
        raise RuntimeError(f"OpenRouter {r.status_code}: {r.text[:300]}")
    raise RuntimeError("OpenRouter injoignable")


def _parse_json(txt: str) -> dict:
    txt = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
    a, b = txt.find("{"), txt.rfind("}")
    return json.loads(txt[a:b + 1])


def word_count(story: dict) -> int:
    return sum(len(b["text"].split()) for b in story["beats"])


def build_system(brand: dict, dom: dict) -> str:
    return SYSTEM_TEMPLATE.format(brand=brand["name"], domain=dom["label"], focus=dom["focus"],
                                  refs=REFERENCE_SCRIPTS, scenes=SCENE_DOCS, icons=", ".join(dom.get("icons", [])))


def write_story(topic: str, cfg: Config, brand: dict, dom: dict, verify: bool = True) -> dict:
    msgs = [{"role": "system", "content": build_system(brand, dom)},
            {"role": "user", "content": f"Sujet : {topic}\nÉcris le script JSON."}]
    story = _parse_json(_chat(cfg, msgs))
    n = word_count(story)
    if not 135 <= n <= 185:
        msgs += [{"role": "assistant", "content": json.dumps(story, ensure_ascii=False)},
                 {"role": "user", "content": f"Le script fait {n} mots. Ajuste-le à 145-170 mots, même JSON."}]
        story = _parse_json(_chat(cfg, msgs))
    if verify:
        story = _parse_json(_chat(cfg, [{"role": "system", "content": VERIFY},
                                        {"role": "user", "content": json.dumps(story, ensure_ascii=False)}],
                                  temperature=0.2))
    return story


def suggest_topics(cfg: Config, dom: dict, n: int = 20, exclude: list[str] = ()) -> list[str]:
    prompt = (f"Propose {n} histoires vraies, peu connues et vérifiables, domaine {dom['label']} ({dom['focus']}), "
              "parfaites pour la formule (accroche choc, date, protagoniste, escalade, retournement, chute ironique). "
              f"Évite : {', '.join(exclude) or 'rien'}. "
              'Réponds en JSON : {"topics": ["Nom — année — l\'idée en une phrase", ...]}')
    return _parse_json(_chat(cfg, [{"role": "user", "content": prompt}], temperature=0.9))["topics"]
