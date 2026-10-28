# Décisions

Une entrée par décision : date, décision, raison, alternatives écartées. La plus récente en bas.

---

## 2026-10-28 — Récap figé, crawl unique

**Décision.** Le site est un récap figé. On crawle l'historique une fois, sans crawl incrémental ni tâche planifiée.

**Raison.** L'aventure Classic de la guilde se termine avec la sortie de Forever : les données ne bougeront plus. Un site statique suffit, ne coûte rien à héberger et n'expose jamais le secret WCL au navigateur.

**Écarté.** Mise à jour hebdomadaire automatique (inutile pour des données figées). Temps réel (imposerait un backend proxy, une base et un hébergement).

---

## 2026-10-28 — Niveau de détail des données : niveau 2, niveau 3 ciblé

**Décision.** On crawle les tableaux agrégés par combat et par joueur (dégâts, soins, dégâts subis, morts, interruptions, dispels…). Les événements bruts (niveau 3) ne sont crawlés que pour des stats listées à l'avance, uniquement sur les combats concernés.

**Raison.** La plupart des titres envisagés sortent des tableaux agrégés. Le volume (environ 800 rapports, deux raids par semaine depuis 2019) reste raisonnable au niveau 2. Les données étant figées, on peut ajouter du niveau 3 plus tard sans tout recrawler.

**Écarté.** Résumés seuls (trop pauvres pour les titres). Événements bruts sur tout l'historique (coût en requêtes et en stockage disproportionné).

**À vérifier.** Les stats Sniper et Savior demandent les PV des cibles au moment du soin, qui dépendent de l'advanced combat logging. À tester sur quelques rapports de chaque époque. Fishbait / Domino est peut-être faisable dès le niveau 2 via le tableau Deaths.

---

## 2026-10-28 — Périmètre des rapports et dédoublonnage

**Décision.**
- Uniquement les rapports rattachés à la fiche de guilde WCL 482770 (Fable, Arugal AU). Nom et serveur inchangés de 2019 à MoP.
- On garde les combats en 40 en Era et en 25 de TBC à MoP (normal et héroïque). Exclus : 20, 10, LFR, Flex.
- Le filtre de format se fait au niveau du combat (taille et difficulté WCL), pas sur le nom de zone.
- Dédoublonnage par pull : si un même pull apparaît dans plusieurs rapports à des horaires qui se chevauchent, on garde celui du rapport contenant le plus de boss. On compare des plages horaires, pas des dates calendaires.
- Le cache brut conserve tout ; le filtrage et le dédoublonnage se font à l'étape de calcul.

**Raison.** De Wrath à MoP, une même zone existe en 10 et en 25. Une soirée de raid peut dépasser minuit, et un logger qui crashe peut couper une soirée en deux rapports. Un dédoublonnage par rapport entier perdrait la moitié de ces soirées.

**Écarté.** Liste manuelle de rapports perso supplémentaires (non retenue : rapports de guilde uniquement). Dédoublonnage par rapport entier et par date calendaire.

---

## 2026-10-28 — Joueurs, rerolls et seuil d'apparition

**Décision.**
- Un joueur = son main + ses rerolls, regroupés par un fichier de mapping manuel (`{"rerolls": {"Main": ["Reroll1", …]}}`, une première version existe avec 33 joueurs).
- Un personnage non mappé est un joueur à lui seul.
- Les noms sont comparés après normalisation Unicode (beaucoup de noms accentués).
- Le pipeline signale les personnages rattachés à deux joueurs, les rerolls listés introuvables dans les logs, et sort la liste des personnages non mappés qui passent le seuil.
- Seuil d'apparition dans les classements : 15 semaines de reset distinctes de présence en raid éligible, tous personnages confondus.

**Raison.** Le site classe des joueurs sur 7 ans, et beaucoup ont changé de main entre les extensions. 15 semaines, environ 3 mois, c'est à peu près la durée minimale pour que les autres membres se souviennent de quelqu'un. Les pickups disparaissent ainsi sans liste noire à tenir.

**Écarté.** Classement par personnage (un reroll couperait l'histoire d'un joueur en deux). Semaines civiles (un raid du mardi et un du lundi suivant doivent tomber dans la même semaine de jeu).

---

## 2026-10-28 — Rôle attribué combat par combat

**Décision.** Le rôle (TANK / DPS / HEALER) est celui que WCL indique pour chaque combat. La table de stats est au grain `(joueur, personnage, combat, rôle)`. Les classements d'un rôle ne comptent que les combats joués dans ce rôle.

**Raison.** Un druide ou un paladin peut tanker un soir et healer le suivant, un joueur peut être healer sur son main et DPS sur son reroll. Le volume de données rend acceptables quelques erreurs de détection, surtout sur les logs Era où le rôle est déduit par WCL.

**Écarté.** Rôle fixé par joueur ou par personnage (fausse les classements des hybrides). Correction manuelle des rôles (pas nécessaire).

---

## 2026-10-28 — Normalisation base 100 : médiane du rôle par pull

**Décision.** Score = valeur du joueur / médiane des joueurs du même rôle dans le même pull × 100. Kills seulement pour les scores de performance ; wipes inclus pour les stats fun (morts, etc.). On agrège ensuite par raid, extension ou carrière.

**Raison.** Neutralise d'un coup ce qui rend les extensions incomparables (stuff, inflation des chiffres, durée des combats, buffs). Mesure le joueur contre ses coéquipiers du soir, ce qui colle à l'esprit d'un récap de guilde. La médiane résiste aux morts précoces et aux AFK, contrairement à la moyenne.

**Écarté.** Ratio au record de la guilde sur le boss (écrasé par un record exceptionnel, et les scores bougent dès qu'on ajoute des données). Parses WCL (mesurent contre le monde, pas contre la guilde ; déjà couverts par le projet « Fable Guild Rankings », qui sert de référence de contrôle).

**Limites connues.** Les tanks sont 2 à 4 par pull, la médiane y est fragile : ils auront probablement des métriques propres. Pour les healers, soins effectifs ou bruts reste à trancher avec la liste des titres.

---

## 2026-10-28 — Stack : Python + React/Vite + GitHub Pages

**Décision.**
- Pipeline (collecte + calcul) en Python, table de stats en DuckDB / Parquet.
- Site en React + Vite (JavaScript), hébergé sur GitHub Pages.
- Contrat entre les deux : fichiers JSON (index des joueurs pour la recherche, une fiche par joueur, tops par catégorie). Le site ne fait qu'afficher.

**Raison.** Python est le plus confortable pour explorer les données et itérer sur les titres et la normalisation. React + Vite et le déploiement sur Pages sont déjà maîtrisés par le propriétaire. Le contrat JSON permet de faire évoluer chaque moitié indépendamment.

**Écarté.** Tout en TypeScript (moins pratique pour l'exploration de données). Astro (seul vrai avantage : des aperçus de liens par joueur dans Discord, jugés non prioritaires).

---

## 2026-10-28 — Archivage des données en trois étages

**Décision.**
1. Cache brut des réponses WCL : local, dans le repo, ignoré par git.
2. Instantané compressé de ce cache, archivé hors du PC une fois le crawl terminé (Release GitHub du repo par défaut, à confirmer au moment d'archiver).
3. Table de stats calculée (Parquet) : commitée dans le repo.

**Raison.** Avec des données figées, le cache est l'archive de 7 ans de guilde ; une seule copie locale est trop fragile si des rapports disparaissent de WCL. Commiter la table de stats permet de reconstruire le site sans crawler ni identifiants WCL : le secret ne sert qu'au crawl initial et ne va jamais en CI.

**Écarté.** Cache local seulement (une seule copie). Cache brut dans git (trop lourd, limite GitHub de 100 Mo par fichier).

---

## 2026-10-28 — Langue

**Décision.** Site en anglais uniquement. Les textes des titres (nom, description, blague) vivent dans la config des titres, pas en dur dans le code React. Docs du repo en français, code en anglais.

**Raison.** La guilde joue sur un serveur australien et les noms de titres envisagés sont déjà en anglais. Garder les textes en config permet d'ajuster les blagues sans toucher au code, et laisse une traduction possible plus tard.

**Écarté.** Site multilingue (travail inutile vu le public).

---

## 2026-10-28 — Accès WCL via l'endpoint `/user` (compte abonné)

**Décision.** Le crawl interroge `https://classic.warcraftlogs.com/api/v2/user` avec un jeton utilisateur obtenu une fois par le flux OAuth authorization code (`python -m pipeline.auth`, redirection `http://localhost:8765/callback`). Le jeton est stocké dans `.wcl_user_token.json`, ignoré par git. Le client ID / secret de `.env` servent à cet échange de jeton.

**Raison.** WCL archive les rapports environ 2 ans après leur envoi ; le contenu d'un rapport archivé n'est lisible que via `/user`, par un compte abonné. Lors du crawl d'essai, tous les rapports Classic, TBC et Wrath tirés étaient archivés, et les rapports Cata vont l'être à leur tour. Le compte Gold du propriétaire y donne accès.

**Écarté.** Client credentials sur `/client` (prévu au départ) : n'accède qu'aux rapports non archivés.

**Détails.** Résultats de l'essai dans `docs/crawl-essai.md`.

---

## 2026-10-28 — Crawl complet : tableaux retenus et filtrage dès la collecte

**Décision.**
- Tableaux crawlés pour chaque pull éligible : Summary, DamageDone, Healing, DamageTaken, Deaths, Interrupts, Dispels, Casts (liste dans `config/crawl.json`). Casts sert uniquement au nombre total de casts et au temps actif.
- Les pulls hors format ne sont **pas** crawlés : taille ≠ 40 en Era / 25 ensuite, difficulté hors {3, 4}, ou moins de 10 joueurs présents (`friendlyPlayers`). La liste des pulls de chaque rapport, elle, est mise en cache entièrement.
- Pas d'événements de soin (niveau 3) dans le crawl complet : on les crawlera plus tard, de façon ciblée, si Sniper / Savior sont retenus.

**Raison.** Budget API de 3000 points/heure et sortie du site visée pour le 4 novembre 2026. Les règles d'analyse sur les auras ou le détail des casts demanderaient plus de temps qu'il n'en reste.

**Écarté.** Buffs / Debuffs (pas le temps d'en tirer des règles). Crawler tous les pulls « pour garder tout » : le cache ne garde donc plus les tableaux des pulls hors format, mais on peut les crawler plus tard, puisque la liste des pulls est en cache.

---

## 2026-10-28 — Liste des stats V1

**Décision.**
- 44 stats réparties en 4 catégories : communes (24), tank (7), healer (6), DPS (7). Liste, titres et descriptions en anglais dans `docs/stats.md`.
- Les stats communes sont calculées par rôle et filtrées par rôle sur la fiche joueur, plutôt que déclinées dans chaque catégorie.
- Percentile calculé sur un taux, parmi les joueurs qualifiés ; nombre en dur = total de carrière.
- Tanks comparés à la médiane des tanks sur le même boss, sur toute l'histoire de la guilde. Healers : soins effectifs.
- Morts scriptées exclues des stats de mort (liste en config).
- Compléments au crawl : un tableau DamageDone sur le trash par rapport (Timekeeper / The Tourist) et, en niveau 3 ciblé, les buffs des tanks autour de leurs morts (Blamed the Healer).

**Raison.** Une première liste d'environ 100 stats contenait beaucoup de doublons (présence, morts, interruptions par rôle…). Une base plus petite permet d'itérer. Les tanks sont 2 ou 3 par pull : la médiane du pull est trop fragile. Sur le kill du Lich King de l'échantillon, 25 des 28 morts viennent de Fury of Frostmourne.

**Écarté pour la V1.** Not Even Close! (événements de dégâts subis des tanks avec leurs PV sur chaque kill, trop cher). Wipe Pumper, Legendary Flex, Necromancer, Bubble Wrap / Gardener, Threat Dealer, Crazy Pet Lady, Savior, True Sniper : reportées en V2.


---

## 2026-10-28 — Site : filtres multi-sélection par cellules additives

**Décision.**
- Chaque stat se filtre par extension × rôle × classe, en multi-sélection, sur l'accueil, les classements et la fiche joueur.
- Le pipeline exporte chaque stat en cellules `(joueur, extension, classe, rôle, valeurs…)` dont les valeurs s'additionnent (numérateur / dénominateur, ensembles d'ids, sommes de régression…). Le site additionne les cellules filtrées, calcule la valeur de chaque joueur puis son percentile. Format complet dans `docs/site-data.md`.
- Pas de bouton « Adjust expansions to Era » : les joueurs sont déjà filtrés à 15 semaines et toutes les stats sont en base 100.

**Raison.** Avec 5 extensions, 11 classes et 3 rôles en multi-sélection, les combinaisons se comptent en dizaines de milliers : impossible de tout précalculer. Les cellules additives gardent les règles de stats dans le pipeline (le site ne connaît que 8 modes d'agrégation génériques) pour un export d'environ 1 Mo.

**Écarté.** Filtres à choix unique entièrement précalculés (on ne pourrait pas cocher « TBC + Wrath »). Site qui recalcule les stats depuis les données brutes (règles dupliquées en JavaScript).

---

## 2026-10-28 — Site : rang PvP par tier de raid

**Décision.**
- Chaque nom de joueur porte un macaron de rang PvP de 1 à 14, avec les **icônes officielles Alliance** (Private → Grand Marshal), copiées dans `site/public/ranks/`.
- Un rang par tier de raid validé, plafonné à 14. Liste des 19 tiers (fusions Gruul/Mag, SSC/TK, BT/Hyjal, HoF/ToES, comme l'artifact « Fable Guild Rankings ») dans `config/tiers.json`.
- Un tier est validé à partir d'un seuil de semaines de reset de présence dans ce tier (`min_weeks_per_tier`, valeur à fixer, 4 par défaut).
- Le rang ne dépend pas des filtres.

**Raison.** Clin d'œil au système d'honneur de Vanilla, lisible d'un coup d'œil : plus un joueur a fait de tiers avec la guilde, plus il est gradé. Un seuil de présence évite qu'un remplaçant d'un soir valide un tier.

**Écarté.** Badge SVG maison (moins reconnaissable). Tier validé dès un pull ou dès un kill (trop facile à obtenir).

**Note.** Les icônes sont des assets Blizzard, utilisées dans un site de fans non commercial.

---

## 2026-10-28 — Site : structure et données fictives

**Décision.**
- Site dans `site/` : React 18 + Vite 5, sans routeur externe (routage par hash, filtres dans l'URL pour partager une vue filtrée), `base: './'` pour GitHub Pages.
- Pages : accueil (totaux de guilde + tops), liste des titres, classement par stat, fiche joueur.
- Les textes et réglages d'affichage vivent en config : `config/stats.json` (44 stats, textes, mode d'agrégation, format), `config/site.json` (stats de l'accueil, seuils des titres), `config/tiers.json` (extensions, tiers, rangs).
- `site/public/data/` est ignoré par git : régénéré par l'export (ou par `python -m pipeline.mock_site_data` en attendant l'étape de calcul).
- `npm` tourne avec un cache local au repo (`--cache ./.npm-cache`) pour ne rien écrire hors du dossier.

**Raison.** Permet de construire le site contre le vrai contrat de données avant que le calcul n'existe, et de régler textes et seuils sans toucher au code.

**Écarté.** react-router (inutile pour 4 routes). Données fictives écrites à la main dans le site (divergeraient du contrat).

---

## 2026-10-28 — Site : palette Timewalking en bleu Alliance, mobile d'abord

**Décision.**
- Palette reprise de timewalking.blizzard.com : fond marine profond, cartes marine translucides, texte crème `#fff2df`, texte secondaire beige `#c6af8d`, accent parchemin `#eccaa1`, rouge `#e5484d`. Son bleu-vert principal (`#0093b2`) est remplacé par un bleu Alliance `#2f6fd8` (`#1c4f9e` en foncé), et les deux marines sont légèrement décalées vers ce bleu (`#061529`, `#0b2a4e`) pour rester assorties.
- Thème sombre uniquement, comme l'original. Polices du site Timewalking : Oswald (titres), Barlow Condensed (sous-titres), Roboto (texte).
- CSS écrit mobile d'abord : filtres repliés derrière un bouton « Filters » sous 720 px, chips de 34 px de haut, colonne « Career » et texte du percentile masqués sur téléphone, tiers sur une ligne qui défile, champ de recherche en 16 px (pas de zoom iOS), marges `safe-area`.

**Raison.** Le site sera surtout ouvert depuis un lien partagé dans Discord, donc sur téléphone. La palette Timewalking donne le ton « récap Blizzard » voulu ; le bleu Alliance rattache le site à la faction de la guilde et aux icônes de rang.

**Écarté.** Garder le bleu-vert d'origine. Garder le thème clair de l'artifact.
