# Calcul d'essai (2026-10-28)

> **Mise à jour après décisions** (même jour) : les points 1, 2, 3, 6 et 9 sont tranchés et appliqués (voir `docs/decisions.md`). Relance sur le cache : **1 201 pulls Classic** + 288 pulls TBC à MoP venus du crawl d'essai, 50 064 lignes.
> - Potions Era depuis Casts : plus que 56 pulls Classic sur 1 201 sans aucun consommable.
> - 13 pulls écartés comme faux logs (moins de 10 joueurs avec un rôle).
> - Tanks Era par pull avec la règle des 10 % : 0 (13 pulls), 1 (584), 2 (412), 3 (170), 4 (22). 1 208 « tanks » WCL repassent DPS, 429 DPS ou healers deviennent tanks. Les tanks d'adds (Garr, Golemagg, Lucifron…) deviennent DPS.
> - Enchantements avec la liste d'emplacements : 65 % en Era, 90 à 98 % de TBC à Cata, 86 % en MoP avant d'exclure casque et distance (0/25 et 0/9 dans le sample : pas d'enchantement de tête en MoP, arme du chasseur en main droite), corrigé depuis.

Premier étage du calcul : `pipeline/facts.py` transforme chaque pull en lignes `(joueur, personnage, pull, rôle)` avec les métriques brutes, applique le mapping des rerolls et calcule un score base 100 contre la médiane du rôle dans le pull (kills seulement). Il affiche des contrôles pour faire ressortir les problèmes de données.

```
python -m pipeline.facts --samples      # les 6 pulls de data/samples/
python -m pipeline.facts --cache        # le cache brut (lecture seule, peut tourner pendant le crawl)
```

Sortie : `data/facts/facts_<source>.csv` (ignoré par git). Le cache doit être lu avec le Python du `.venv` (le module `pipeline.guild` demande `requests` et `python-dotenv`).

Essai fait sur les 6 samples (une extension chacun) et sur les **782 pulls Classic** déjà dans le cache (MC 476, BWL 239, Onyxia 67), soit 27 340 lignes.

## Ce qui marche

- Le même code lit les samples et le cache : les tableaux ont la même forme dans les 5 extensions.
- Rôles, scores base 100 DPS et healers, morts, premier mort, dispels, casts, temps actif, ilvl : disponibles partout.
- Morts scriptées : sur le Lich King, 25 morts sur 28 viennent de Fury of Frostmourne et sont bien exclues. Le premier mort retenu est le vrai premier mort.
- Équipement : `damageDone.gear` est vide en MoP, mais `summary.playerDetails[].combatantInfo.gear` est rempli dans toutes les extensions. C'est cette source qui est utilisée.
- Les noms accentués sont intacts dans les données. Le « � » vu dans la console Windows vient de l'affichage seulement (lancer avec `PYTHONIOENCODING=utf-8`).

## Problèmes trouvés

### 1. Potions invisibles en Classic Era (bloque The Junky en Era)
`potionUse` et `healthstoneUse` valent **0 dans les 782 pulls Classic**, alors que le tableau Casts montre « Healing Potion » (530), « Major Healthstone » (265), « Demonic Rune » (141), « Dark Rune » (127)… En TBC, Cata et MoP, les compteurs sont remplis. En Wrath, 1 seule potion sur le Lich King (une potion par combat dans cette extension, plausible).
→ En Era, compter les consommables depuis Casts, avec une **liste de sorts en config**. Attention : les potions de mana s'appellent « Restore Mana » et les potions de protection par leur effet (« Fire Protection »), un filtre sur le mot « potion » ne suffit pas.

### 2. Pulls parasites : le seuil de 10 joueurs ne suffit pas
Joueurs par pull : Onyxia surtout 20 à 29 (45 pulls sur 67, des « Onyxia Splits »), 3 pulls d'Onyxia avec moins de 10 joueurs (dont 1 à 1 joueur), MC 30 à 35 joueurs dans 270 pulls sur 476 (raids incomplets ou joueurs hors de portée du log).
→ Le filtre anti-parasites doit être une part de la taille du raid. 75 % (30 en 40, 19 en 25) garderait les MC à 30-35 et écarterait les splits d'Onyxia. À trancher, notamment pour les splits d'Onyxia (vrais raids de guilde ou non ?).

### 3. Tanks mal détectés en Era (fausse les stats tank en Era)
Tanks par pull en Classic : 0 dans 30 pulls, 1 dans 268, 4 à 6 dans 92. Le rôle tank vient de la déduction de WCL, peu fiable en Era (Firemaw et Razorgore sans tank, guerriers DPS classés tank…). Le score tank « dégâts subis / médiane des tanks du pull » donne des valeurs absurdes (max 17 514).
→ Confirme la décision de comparer les tanks à la médiane des tanks **sur le même boss, sur toute l'histoire**. Il faudra aussi décider si les stats tank Era sont publiées, ou filtrées (ex. tank = le plus de dégâts subis de mêlée du boss).

### 4. Entités qui ne sont pas des joueurs
Tricks of the Trade, Skull Banner, Stormlash Totem, Kalecgos (DS), RedistributedDamage, serpents de chasseur… apparaissent comme lignes des tableaux, et certaines interrompent ou dissipent (29 cas en Classic). Elles sont ignorées : seuls les joueurs listés avec un rôle dans le Summary comptent.
→ Les dégâts de Tricks of the Trade ou de Skull Banner ne sont crédités à personne. Acceptable pour la V1.

### 5. Interruptions très rares
Aucune interruption dans 717 pulls Classic sur 782 (92 %), ni dans les samples TBC, Wrath et Cata. Seul le sample MoP en a (Embodied Doubt, Garrosh).
→ The Nut Crusher ne compte que les pulls « où quelque chose pouvait être interrompu » : la stat sera très creuse en Era. À garder en tête en choisissant le seuil minimal de pulls.

### 6. Enchantements : liste des emplacements nécessaire
Les gear listent 18 ou 19 emplacements, dont colliers, anneaux, bijoux… jamais enchantables selon l'époque. Taux brut : 29 % en Era, environ 50 % ensuite.
→ Liste des emplacements enchantables **par extension**, en config (déjà dans « À décider »).

### 7. Lignes vides ou incomplètes
- 48 lignes avec 0 dégâts (DPS), 0 soins (healer) ou 0 dégâts subis (tank) sur des kills : déconnexions, AFK, ou rôle faux. Elles tirent les médianes vers le bas sans les fausser (médiane).
- 37 joueurs listés dans le Summary mais absents du tableau Casts.
- 11 lignes de classe « Unknown » en Classic (WCL n'a pas su identifier le personnage).
- 2 pulls sans `playerDetails` (liste vide) : rôles repris de `composition`, sans potions ni équipement.

### 8. Mapping des rerolls : l'Era n'est pas couvert
Sur les personnages Classic, 16 seulement sont dans `fable_rerolls.json`, 275 ne le sont pas. Le mapping a été pensé pour les extensions suivantes. Beaucoup de joueurs d'Era passeront peut-être le seuil des 15 semaines sous un autre nom que leur main d'après.
→ Une fois tout le Classic crawlé, sortir la liste des personnages non mappés au-dessus du seuil (prévu) et compléter le mapping.

### 9. Dossiers du crawl d'essai
36 dossiers de rapports du crawl d'essai sont à l'ancien format (`fights.json`, pas de `report.json`) : leurs 314 pulls sont ignorés par le calcul. Le crawl complet doit les re-télécharger à son passage (à vérifier en fin de crawl).

## Pas encore testé

- Dédoublonnage des pulls entre rapports qui se chevauchent, semaines de reset et seuil de 15 semaines (demandent l'heure absolue : présente dans le cache, absente des samples).
- Tout ce qui est au-delà de l'Era sur un vrai volume (le crawl n'y est pas encore).
- Les stats elles-mêmes et l'export JSON du site : étages suivants.
