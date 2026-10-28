# Échantillons de données WCL

Un pull par extension, tiré du crawl d'essai (`docs/crawl-essai.md`), pour concevoir les stats sans accès à l'API. Ce sont les tableaux de niveau 2 que le crawl complet récupère pour chaque pull éligible (`config/crawl.json`) : Summary, DamageDone, Healing, DamageTaken, Deaths, Interrupts, Dispels, Casts.

| Fichier | Pull |
|---|---|
| `classic_mc_ragnaros_kill` | Molten Core, Ragnaros, 40, kill |
| `tbc_bt_illidan_kill` | Black Temple, Illidan, 25, kill |
| `wotlk_icc_lich_king_kill` | ICC, The Lich King, 25 normal, kill |
| `cata_ds_madness_heroic_kill` | Dragon Soul, Madness of Deathwing, 25 héroïque, kill |
| `cata_fl_ragnaros_heroic_wipe` | Firelands, Ragnaros, 25 héroïque, wipe |
| `mop_soo_garrosh_kill` | Siege of Orgrimmar, Garrosh, 25 normal, kill |

Chaque pull existe en deux versions :
- `*.json` : réponse complète, compacte ;
- `*_light.json` : même structure, indentée, avec chaque liste tronquée à 3 éléments (`"... N more"`). C'est la version à lire pour comprendre les champs.

## Structure

```
expansion, report, zone
fight      : id, name, difficulty (3 normal, 4 héroïque), size, kill, startTime/endTime (ms dans le rapport), fightPercentage
players    : personnages du rapport (id, name, server, subType = classe)
tables
  summary      : data.playerDetails.{tanks,healers,dps}[] → rôle, spé, ilvl, potionUse, healthstoneUse, combatantInfo.stats
                 data.composition, data.damageDone / healingDone / damageTaken (totaux par joueur), data.deathEvents
  damageDone   : data.entries[] par joueur → total, activeTime (ms), abilities[], targets[], gear[], talents[]
  healing      : idem, total = soins effectifs, overheal = soins perdus (aussi par capacité)
  damageTaken  : data.entries[] par joueur → total, abilities[] (ce qui l'a touché), sources[]
  deaths       : data.entries[] → une entrée par mort : name, timestamp, killingBlow, damage/healing reçus avant la mort
  interrupts   : data.entries[0].entries[] par sort ennemi → spellsInterrupted, details[] (qui a coupé, avec quoi)
  dispels      : data.entries[0].entries[] par aura dissipée, details[] (qui a dissipé)
  casts        : data.entries[] par joueur → total (nombre de casts), activeTime (ms)
```

Les identifiants de joueurs (`id`) sont propres au rapport. La durée du pull est `fight.endTime - fight.startTime`. Pour un temps d'activité en %, utiliser `activeTime / durée`.
