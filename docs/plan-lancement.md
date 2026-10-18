# Plan de lancement (8 premières semaines)

Objectif : faire grandir, pour chaque page, une audience qui s'intéresse vraiment à son sujet. On y arrive par la régularité, des accroches fortes et des ajustements chaque semaine selon les chiffres.

## Pages et rythme

| Page | Domaines | Rythme de départ | Plateformes |
|---|---|---|---|
| Nourlio | nutrition, sport, santé (en rotation) | 1 vidéo par jour | Instagram Reels, YouTube Shorts, LinkedIn |
| Pile ou Face | business | 4 vidéos par semaine | Instagram Reels, YouTube Shorts, LinkedIn |

- Rotation Nourlio : lundi nutrition, mardi sport, mercredi santé, puis on recommence.
- Créneaux : définir 1 ou 2 créneaux par jour dans le calendrier (« queue ») de chaque profil Upload-Post, puis publier avec `--queue`. Commencer en fin de journée et à midi, puis garder les créneaux qui marchent.
- Avoir toujours **7 jours d'avance** : chaque dimanche, `--find-topics 10` puis `--next 7 --publish --queue` (après relecture des scripts avec `--write-only` le premier mois).

## Règles de contenu (déjà intégrées au scénariste)

- Les 2 premières secondes décident de tout : l'accroche désigne un objet ou une personne visible à l'écran.
- Un indice à retenir et son rappel : ils poussent à regarder jusqu'au bout.
- Fin en boucle (« rappelez-vous que… ») : la vidéo repart sur l'accroche, ce qui fait monter la rétention.
- Miniature = image de l'accroche + 5 mots maximum (`cover_text`).
- Faits vérifiés et sources dans la description : la crédibilité fait partie de la marque.

## Chiffres à suivre chaque semaine

| Indicateur | Ce qu'il révèle | Action si faible |
|---|---|---|
| Rétention à 3 s | force de l'accroche | réécrire la phrase 1 plus concrète, image plus forte |
| Taux de visionnage complet | rythme et suspense | raccourcir (moins de 280 mots), indice plus tôt |
| Partages et enregistrements | valeur du sujet | privilégier les thèmes qui ont le plus de partages |
| Abonnés gagnés par vidéo | adéquation à la page | recentrer sur le domaine qui convertit |

Chaque semaine : repérer les 2 meilleures vidéos par page, ajouter 5 sujets de la même veine dans la banque (`topics-<domaine>.txt`) et retirer ceux qui ressemblent aux moins bonnes.

## Avant la première publication

1. Ajouter `OPENROUTER_API_KEY`, `ELEVENLABS_API_KEY` et `UPLOAD_POST_API_KEY` dans les réglages de l'environnement.
2. Créer dans Upload-Post les profils `nourlio` et `pileouface` et y connecter les comptes Instagram, YouTube et LinkedIn.
3. Générer une vidéo test entièrement automatique, la valider, faire un essai avec `--dry-run`, puis publier une seule vidéo.
4. Ensuite seulement, lancer la production en série.
