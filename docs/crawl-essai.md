# Crawl d'essai (2026-10-28)

But : vérifier, avant le crawl complet, la détection des rôles, la présence des PV des cibles (Sniper, Savior) et le volume du cache.

Échantillon : 5 rapports au hasard par extension (graine 42), parmi ceux qui contiennent au moins un kill en 40 (Era) ou en 25 (TBC → MoP). Script : `python -m pipeline.probe crawl` puis `analyze`. Liste des rapports : `data/cache/probe_selection.json` ; résultats bruts : `data/cache/probe_summary.md` (non commités).

| Extension | Rapports de guilde | Rapports tirés |
|---|---|---|
| Classic | 403 | 3 × Molten Core, 2 × Onyxia |
| TBC | 227 | Sunwell, 2 × Gruul/Magtheridon, 2 × BT/Hyjal |
| Wrath | 208 | ToC, 2 × Ulduar, Naxx/Sarth/Maly, ICC |
| Cata | 123 | 4 × Firelands, Dragon Soul |
| MoP | 104 | HoF/ToES, 2 × SoO, 2 × ToT |

Total : 1065 rapports, tous sur `classic.warcraftlogs.com` (y compris 2019). 27 rapports n'ont pas de zone.

## 1. Accès : les vieux rapports sont archivés

WCL archive un rapport environ 2 ans après son envoi. Archivé, son contenu n'est plus lisible via l'endpoint `/client` (client credentials), seulement via `/user` avec un compte abonné. Les 15 rapports Classic, TBC et Wrath tirés étaient archivés. Les premiers rapports Cata (fin 2024) le seront d'ici quelques semaines.

→ Le pipeline passe par `/user` : connexion unique au compte Gold (`python -m pipeline.auth`, flux OAuth authorization code), jeton dans `.wcl_user_token.json` (ignoré par git). Voir `docs/decisions.md`.

## 2. Rôles

Le tableau Summary donne pour chaque pull `playerDetails.tanks / healers / dps`, avec classe, spé, ilvl, stats, potions et pierres de soin. Aucun joueur n'apparaît dans deux rôles sur un même pull, et aucun n'est sans spé.

| Extension | Tanks (min / méd. / max) | Healers | DPS |
|---|---|---|---|
| Classic (40) | 1 / 2,5 / 5 | 5 / 9,5 / 12 | 12 / 23 / 27 |
| TBC (25) | 2 / 3 / 4 | 5 / 6 / 8 | 14 / 16 / 17 |
| Wrath (25) | 0 / 2 / 3 | 1 / 5 / 5 | 0 / 19 / 21 |
| Cata (25) | 0 / 2 / 3 | 0 / 4 / 5 | 1 / 19 / 20 |
| MoP (25) | 2 / 2 / 3 | 2 / 5 / 6 | 15 / 18 / 19 |

Les cas à 0 sont des anomalies réelles, pas des erreurs de détection :
- **Flame Leviathan** (Ulduar) : combat en véhicules, rôles inexploitables. À exclure des classements de performance.
- **Onyxia en Wrath** (event 25) : wipe de 39 s avec 14 joueurs.
- **Bosses de TK soloés en Cata** (Al'ar, Solarian, Void Reaver) : farm de transmo, 1 joueur, mais WCL les classe en taille 25. → Le filtre de format ne suffit pas : il faut aussi un **nombre minimal de joueurs présents** (et/ou ne garder que les zones de l'extension en cours).

En Classic, les tanks varient de 1 à 5 : WCL déduit le rôle de la spé, des off-tanks DPS peuvent tomber d'un côté ou de l'autre. C'est conforme à ce qui était accepté.

## 3. PV des cibles (Sniper, Savior)

- Les PV de la cible sont présents dans **100 %** des événements `heal`, à toutes les époques (`includeResources: true`).
- `resourceActor = 2` : ressources de la cible ; `resourceActor = 1` : uniquement sur les auto-soins (source = cible). Dans les deux cas, ce sont donc les PV de la cible.
- **Limite** : `hitPoints` est presque toujours en **pourcentage** (`maxHitPoints = 100`) et donne les PV **après** le soin. Les PV absolus n'apparaissent que sur une minorité d'événements.

Conséquences :
- **Sniper** (cible > 75 % avant le soin) : faisable de façon approchée. Un soin avec overheal et cible à 100 % après est un « tir sur cible pleine » sans calcul. Pour un seuil exact, il faut les PV max de la cible.
- **Savior** (cible < 10 % avant le soin) : il faut retrancher le soin au pourcentage après soin, donc connaître les PV max absolus de la cible. On peut les estimer par joueur et par pull à partir des événements où les PV absolus sont présents, ou via l'Endurance donnée par Summary (approximatif). Les soins « PV après < 10 % » sont très rares (0 à 17 par kill), le vrai signal est avant le soin.
- Volume : un kill fait jusqu'à ~10 000 événements de soin (souvent plus d'une page en Wrath → MoP). Le niveau 3 sur les soins doit rester ciblé.

## 4. Volume et coût

| Extension | Mo / rapport | Extrapolé |
|---|---|---|
| Classic | 3,8 | 1,5 Go |
| TBC | 9,5 | 2,2 Go |
| Wrath | 17,0 | 3,5 Go |
| Cata | 19,0 | 2,3 Go |
| MoP | 14,9 | 1,6 Go |

Soit **~11 Go de JSON brut** pour tout l'historique avec les 10 tableaux de l'essai (Summary, DamageDone, Healing, DamageTaken, Deaths, Interrupts, Dispels, Casts, Buffs, Debuffs) sur chaque pull de boss, plus une page d'événements de soin par rapport. Le JSON se compresse très bien : l'instantané devrait tenir sous la limite de 2 Go par fichier d'une Release GitHub, à vérifier.

**Coût API** : ~8,5 points par pull (requête des 10 tableaux). Budget du compte : 3000 points/heure. Pour ~14 000 pulls (~13,5 par rapport), ça fait **~120 000 points, soit ~40 h de crawl** en continu. Leviers : ne pas crawler les pulls hors format (10, 20, solo) au lieu de tout garder, retirer les tableaux inutiles (Summary contient déjà dégâts, soins, dégâts subis et morts en version résumée).

## 5. Ce qu'il y a dans les tableaux

- **Summary** : composition, rôles, spé, ilvl, stats, `potionUse`, `healthstoneUse`, `deathEvents`, totaux dégâts / soins / dégâts subis.
- **Deaths** : chaque mort avec horodatage, tueur et capacité → ordre des morts (Fishbait / Domino) faisable au niveau 2.
- **Interrupts** : par capacité ennemie, qui a interrompu quoi. Vide quand le boss n'a rien d'interruptible (la majorité des pulls Classic et Cata).
- **Dispels**, **Casts**, **Buffs** / **Debuffs** (uptime des auras : flasks, consommables…), **DamageTaken** par capacité (stats du genre « a mangé le plus de mécaniques évitables »).
