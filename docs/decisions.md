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

---

## 2026-10-28 — Site : « Achievements », info-bulles de méthode, macarons ronds

**Décision.**
- Les stats et leurs titres s'appellent « Achievements » sur le site (navigation, liste, fiche joueur).
- Chaque achievement a une info-bulle « comment c'est calculé » : la ligne `detail` de `config/stats.json`, les rôles pris en compte, le mode de classement (percentile et dénominateur minimal, total de carrière, meilleur pull…) et les seuils d'attribution du titre et du revers. Le texte est généré par `explain()` (`site/src/lib/stats.js`) à partir de la config, pas écrit à la main. Au survol sur ordinateur, au toucher sur téléphone (panneau en bas de l'écran). Sur la page d'un achievement, le même texte est affiché en clair.
- Macarons de rang ronds et sans bordure (le cercle rogne le cadre carré des icônes du jeu).

**Raison.** Design plus moderne que rétro. Les classements doivent pouvoir s'expliquer sans quitter la page, d'autant que certaines règles surprennent (base 100, percentile filtré, « lower is better »).

**Écarté.** Attribut `title` du navigateur (invisible sur téléphone). Texte d'explication écrit à la main par stat (diverge des réglages).

---

## 2026-10-28 — Fiche joueur : aperçu puis cartes par catégorie

**Décision.**
- L'encart « Achievements » en haut de la fiche est supprimé. Le titre gagné se voit sur la carte de la stat (ruban « Earned », ou « Infamous » pour un revers, et cadre coloré).
- La fiche commence par des tuiles d'aperçu : heures de raid, boss tués, wipes, semaines de raid, boss uniques, personnages. Trois stats génériques (`hours-played`, `boss-kills`, `wipes`, catégorie `overview`) sont ajoutées au contrat pour ça ; elles suivent les filtres comme les autres et ne sont pas des achievements.
- Puis une section par catégorie : Common, puis le rôle principal (le plus d'heures sous les filtres d'extension et de classe), puis les autres rôles joués, s'ils ont au moins une stat avec assez de pulls.
- Chaque stat a sa carte, dans le style des tuiles Timewalking (cadre beige fin, étiquette en capitales espacées, valeur en Oswald). Jusqu'à 3 grandes cartes par section pour les stats les plus marquantes (percentile ≥ 75, ou ≤ 25 sur une stat à revers, qui s'affiche alors sous le nom du revers) ; les autres en petites cartes, 6 visibles puis bouton « Show N more ». Réglages dans `config/site.json` → `player`.

**Raison.** La fiche doit raconter le joueur d'un coup d'œil : ses chiffres de base, puis ce qui le distingue, le reste restant accessible sans encombrer le téléphone.

**Écarté.** Liste de lignes par stat (illisible sur mobile, rien ne ressort). Encart séparé des titres gagnés (doublon avec les cartes).

---

## 2026-10-28 — Favicon « F » et ajustements de la fiche joueur

**Décision.**
- Favicon : un « F » en Cinzel Black, dégradé blanc → parchemin sur fond bleu Alliance, en SVG et en PNG (32, 180, 512). Cinzel (licence OFL) est proche du lettrage du logo du jeu *Fable* qui sert d'icône au Discord de la guilde. Généré par `scripts/make_favicon.py` (fonttools + Pillow dans le venv local).
- Fiche joueur : les six tuiles d'aperçu sont agrandies et occupent tout l'écran sur téléphone (2 × 3), 3 × 2 sur ordinateur. Les sections de stats n'ont plus de titre, seulement un grand espace entre elles.
- Info-bulles dans les cartes : le bouton « i » passe dans le coin haut-droit de la carte pour garder le nom centré ; la bulle s'ouvre décalée à côté du bouton, placée en JS et gardée dans l'écran. Sur téléphone, panneau en bas de l'écran comme avant. Le ruban « Earned » passe dans le coin haut-gauche.

**Raison.** Reprendre l'identité visuelle de la guilde sans réutiliser l'artwork du jeu (illisible en 16 px, et propriété de Microsoft). Une fiche plus aérée, qui s'ouvre sur les chiffres clés du joueur.

**Écarté.** L'artwork du Discord tel quel en favicon. Info-bulle qui recouvre la carte.

---

## 2026-10-28 — Calcul : pulls retenus, tanks Era, consommables Era, enchantements

Suite au calcul d'essai (`docs/calcul-essai.md`).

**Décision.**
- **Pulls parasites** : on garde les raids incomplets et les splits (ex. « Onyxia Splits » à 20-29 joueurs). Seuls les faux logs évidents sont écartés : moins de 10 joueurs avec un rôle (ex. un Onyxia à 1 joueur). Réglage `min_players` de `config/compute.json`.
- **Tanks en Classic Era** : la détection de WCL est remplacée. Est tank tout guerrier, druide ou paladin ayant subi au moins 10 % des dégâts de mêlée du boss du pull. Comme le tableau DamageTaken ne croise pas capacité et source, la mêlée du boss subie par un joueur est estimée par min(dégâts « Melee » subis, dégâts subis des sources Boss). Un tank WCL qui ne passe pas la règle devient DPS.
- **Consommables en Era** : comptés depuis le tableau Casts avec une liste de sorts en config (`era_consumable_casts`). Oublier quelques potions rares est accepté : The Junky n'est pas une stat centrale.
- **Enchantements** : emplacements comptés = casque, épaules (en Era seulement à partir d'AQ40, soit le 2020-07-28 ou en AQ40 / Naxx), torse, poignets, mains, jambes, pieds, main droite, main gauche si c'est une arme ou un bouclier (reconnu à l'icône), arme à distance pour les chasseurs. En MoP, ni casque ni arme à distance (ces enchantements n'existent plus). Les emplacements vides (deux-mains) ne comptent pas.
- **Dossiers du crawl d'essai** : leur liste de combats s'appelle `fights.json` au lieu de `report.json` ; même contenu, le calcul lit les deux.

**Raison.** Les splits font partie de l'histoire de la guilde. En Era, WCL trouvait de 0 à 6 tanks par pull et ne comptait aucune potion. Sans liste d'emplacements, le taux d'enchantement comptait colliers, anneaux et bijoux.

**Écarté.** Seuil à 75 % de la taille du raid (aurait exclu les splits). Garder le rôle tank de WCL en Era.

**Conséquence à surveiller.** Les tanks d'adds en Era (Garr, Golemagg, Lucifron…) passent DPS avec la règle des 10 % et tirent leur score DPS vers le bas.

## 2026-10-28 — Accueil : Hall of fame aléatoire et records de guilde

**Décision.**
- Le Hall of fame tire `featured_count` (8) achievements au hasard parmi tous, une fois par chargement de page ; le tirage ne change pas quand on touche aux filtres.
- Sous les totaux, quatre grandes cartes de records de guilde, qui suivent le filtre d'extension : Loot Pinata (boss le plus tué), Guild Nemesis (boss le plus wipé), Fastest Finish (kill le plus rapide), et Bring a Snack (kill le plus lent). Titres et descriptions dans `config/site.json` → `home.records`, données dans `meta.guild_bosses` (une ligne par boss × difficulté).
- Totaux de l'accueil : Hours in raid, Boss kills, Wipes, Raiders, Pulls. **Hours in raid** = pour chaque rapport retenu, du début du premier combat (trash compris) dans une zone éligible à la fin du dernier pull de boss éligible. **Hours on bosses** (durée des seuls pulls de boss) reste dans les données mais n'est plus affiché sur l'accueil. **Raiders** = joueurs (main + rerolls) ayant au moins un pull éligible, qualifiés ou non ; exporté par masque d'extensions pour suivre le filtre sans double compte.
- Bandeau du site : « Classic Logs Timewalking ».

**Raison.** Varier l'accueil à chaque visite ; donner des faits de guilde, pas seulement des classements de joueurs.

**Écarté.** Une liste fixe de stats mises en avant. Damage dealt dans les totaux (chiffre énorme, peu parlant). Hours in raid comme durée totale des rapports (inclut l'attente avant le premier pull).

---

## 2026-10-28 — Tanks Era : boss ou adds

**Décision.** La règle des tanks en Classic Era devient : guerrier, druide ou paladin ayant subi au moins 10 % de la mêlée du boss **ou** au moins 10 % de la mêlée des adds du pull. La mêlée des adds subie par un joueur est estimée par min(dégâts « Melee » subis hors mêlée du boss, dégâts subis des sources non-boss). Réglage `era_tank.min_melee_share`.

**Raison.** Avec la seule mêlée du boss, les off-tanks (chiens de Golemagg, adds de Garr, Lucifron, Majordomo…) passaient DPS et tiraient leur score DPS vers le bas.

**Effet.** Sur les 1 201 pulls Classic du cache : plus aucun pull sans tank (13 avant). Golemagg passe surtout à 3 tanks, Garr et Lucifron à 3-5, Majordomo à 4-5 ; Magmadar, Geddon et Chromaggus restent à 1 (pas d'adds). Remplace la règle « boss seulement » de l'entrée précédente.

---

## 2026-10-28 — Enchantements : la cape compte

**Décision.** La cape (emplacement 14) s'ajoute aux emplacements enchantables, dans toutes les extensions. Oubli dans la liste initiale.

## 2026-10-28 — Favicon officiel de WoW Forever

**Décision.** Le favicon est le favicon officiel de *World of Warcraft: Forever*, fourni en SVG (`site/public/favicon.svg`, gardé tel quel). Les PNG `favicon-32.png`, `apple-touch-icon.png` (180, fond marine opaque pour iOS) et `icon-512.png` en sont tirés par `scripts/make_favicon.py` (fontTools + Pillow, sans dépendance de plus), cadrés sur le dessin et non sur le viewBox, qui a des marges vides. Deux éclats vert vif (`#0dff0d`) laissés dans le fichier source sont ignorés dans les PNG. Remplace le « F » de Fable sur fond bleu Alliance.

**Raison.** Le récap se clôt avec la sortie de Forever ; le favicon rattache le site au jeu. L'icône du Discord de la guilde reste visible, dans le hero de l'accueil.

**Écarté.** Un « W » redessiné en Cinzel aux couleurs de Forever (essayé avant d'avoir le fichier officiel). cairosvg ou resvg pour rasteriser (dépendances natives ou npm de plus).

---

## 2026-10-28 — Export du site depuis le cache (données partielles)

**Décision.**
- `python -m pipeline.export_site` lit le cache brut, passe par `pipeline/facts.py` et écrit `site/public/data/` au format du contrat, à la place des données fictives. `meta.partial = true` tant que le crawl n'est pas fini : le site affiche un bandeau « Incomplete data » au lieu de « Mock data ».
- **Dédoublonnage** : pulls du même boss et de la même difficulté dont les horaires se chevauchent dans deux rapports ; on garde le rapport qui contient le plus de pulls de boss (188 doublons sur 1 489 pulls au premier export).
- **Semaines de reset** : reset des royaumes océaniens (région US) le mardi à 15:00 UTC, ancre `reset_anchor_utc`. À confirmer.
- **Night Owl** : pull commencé entre 0 h et 6 h, heure de Sydney.
- **Hours in raid** : chaque soirée, du premier au dernier pull de boss (les combats de trash ne sont pas dans le cache). Un rapport est coupé en soirées à toute pause de plus de 3 heures entre deux pulls : certains rapports couvrent plusieurs jours (jusqu'à 290 heures).
- **Capacité « évitable »** : capacité ennemie hors mêlée qui a touché moins de la moitié des joueurs du pull.
- **Stats en attente** (`meta.pending`, cellules vides) : Overachiever (modèle ilvl à écrire), The Terrorist (dégâts alliés absents du niveau 2), Attention Seeker (liste des taunts), Blamed the Healer (niveau 3), Timekeeper (crawl du trash).
- **Base 100 des stats de rôle** : Damage Sponge et Secret DPS contre la médiane des tanks sur le même boss, sur toute l'histoire ; Pacemaker contre la médiane des durées de kill du boss ; One Button Wonder contre la médiane de la classe dans l'extension ; Smite Lord et Parse Fiend contre les healers du pull.
- Taux « par pull » (Sniper, Tank's Personal Nurse, Tunnel Vision, Add Wrangler, The Sweat, The Unprepared) : moyenne des taux de chaque pull, pour que le seuil de 10 pulls s'applique.

**Raison.** Voir le site sur de vraies données pendant le crawl, et faire apparaître les problèmes tôt.

**À surveiller.** Avec la règle des tanks Era, 89 lignes de healers (druides, paladins) passent tank, sans doute frappés par des adds.

---

## 2026-10-28 — Tanks Era : les healers restent healers

**Décision.** La règle des 10 % (mêlée du boss ou des adds) ne s'applique qu'aux joueurs que WCL classe DPS ou tank. Un healer WCL reste healer, même s'il a pris beaucoup de coups d'adds.

**Raison.** Au premier export, 89 lignes de druides et paladins healers passaient tank. Après correction : aucune, et chaque pull Classic garde au moins un tank.

---

## 2026-10-28 — Overachiever : comparaison aux joueurs de même niveau d'équipement

**Décision.** Overachiever = moyenne, sur ses kills, de l'écart entre le score base 100 du joueur et la moyenne des scores des **autres joueurs de la guilde** du même rôle et de la même extension dont l'ilvl, **mesuré par rapport à la médiane de son rôle dans le pull**, est à ±1 du sien en Classic Era et à ±2 ensuite. DPS et healers seulement (le score tank n'est pas relatif au pull). Il faut au moins 20 pairs (`config/compute.json` → `overachiever`).

**Raison.** L'ilvl relatif au raid du soir mesure « en avance ou en retard de stuff », sans mélanger les tiers d'une même extension. En Era, les ilvl sont très resserrés : à ±2, un kill se compare à 55 % de tous les kills de son rôle, à ±1 à 31 %, avec encore des milliers de pairs.

**Écarté.** Le percentile WCL par tranche d'ilvl (un parse contre le monde, demande les rankings de chaque rapport). L'ilvl brut (mélange les tiers d'une extension).

## 2026-10-28 — Une page par guilde : choix de guilde, Fable dans /fable

**Décision.** Le site devient multi-pages (Vite, `rollupOptions.input`) :
- `/` : choix de guilde, deux grandes cartes NightShift et Fable ;
- `/fable/` : le site actuel, inchangé à part le bandeau (« Classic Logs Timewalking » mène au choix de guilde, lien « Fable » dans la barre pour revenir à l'accueil de la guilde) ;
- `/nightshift/` : seulement le texte « Coming soon ».

Assets partagés (favicon, icônes de rang) à la racine de `site/public/`, ceux d'une guilde dans `site/public/<guilde>/`. Le pipeline écrit dans `site/public/fable/data/`. Données et rangs sont chargés en chemins relatifs à la page (`./data/`, `../ranks/`), identiques en dev et au build.

**Raison.** Préparer l'arrivée d'une deuxième guilde (NightShift) sans toucher au site de Fable.

**Écarté.** Une seule app avec la guilde dans le hash (`#/fable/...`) : URL moins lisible, et toutes les guildes chargeraient le même bundle de données.

**Reste ouvert.** Le pipeline et `CLAUDE.md` restent mono-guilde (Fable, fiche WCL 482770) ; NightShift est sur Thunderstrike (EU) ; la brancher demandera sa fiche WCL et sa faction (les icônes de rang sont Alliance).

---

## 2026-10-28 — Favorite Patient : part des soins, classée

**Décision.** Favorite Patient affiche la part des soins du healer sur les autres raideurs qui est allée à son patient favori, avec le total entre parenthèses (ex. « Yogiqt 52.1% (827.5K healing) »). Le classement va de la part la plus haute à la plus basse. Seuls les patients soignés sur au moins 10 pulls (`min_den`) peuvent être retenus, pour éviter qu'un seul pull donne 100 %. La stat n'est jamais tirée dans le Hall of fame de l'accueil (`hall_of_fame: false` dans `config/stats.json`).

**Raison.** Le total brut favorisait surtout les healers qui ont beaucoup joué ; la part dit à quel point le healer est « attaché » à un joueur. Trop compliquée à lire sur une carte d'accueil.

**Alternatives écartées.** Dénominateur = soins totaux, auto-soins compris (non retenu : les auto-soins ne sont pas des patients).

---

## 2026-10-28 — Rôle tank réservé aux classes qui peuvent tanker

**Décision.** Dans toutes les extensions, un joueur que WCL classe tank alors que sa classe ne peut pas tanker devient DPS. Classes tank (`tank_classes` dans `config/compute.json`) : Guerrier, Druide, Paladin, Chevalier de la mort, Moine.

**Raison.** Garde-fou contre les erreurs de rôle de WCL (ex. un chasseur dont le familier tient un add). Sur le cache actuel, aucun pull n'est concerné : les pulls tank de Loveling (chasseur) ont été joués sur son reroll guerrier Lovelain.

---

## 2026-10-28 — Compléments au crawl : taunts, tirs alliés, CD des tanks, trash, parses

**Constat.** Le tableau Casts de niveau 2 ne garde que les **5 capacités les plus lancées** par joueur (aucune ligne n'en a plus sur 9 600 vérifiées). Les taunts n'y apparaissent presque jamais, et les potions Era comptées depuis ce tableau étaient sous-estimées. Les dégâts entre joueurs ne sont dans aucun tableau en cache.

**Décision.** `python -m pipeline.crawl_extra`, lancé **une fois le crawl principal terminé**, sur les rapports déjà en cache (même cache, reprise possible) :
- **par pull éligible** (`extra_<fight>.json`), une requête : DamageDone filtré joueur → joueur (The Terrorist, auto-dégâts exclus au calcul) ; Casts filtré sur les taunts (Attention Seeker) ; en Era, Casts filtré sur `era_consumable_casts` (remplace le tableau Casts pour The Junky) ; si un joueur d'une classe tank est mort, les événements de buffs des CD défensifs (Blamed the Healer : mort de tank, hors morts scriptées, avec un CD actif à l'instant de la mort, CD externes compris) ;
- **par rapport** : DamageDone `killType: Trash` (`trash.json`, Timekeeper / The Tourist : part des dégâts de trash de la soirée, base 100 contre la médiane des DPS du rapport) ; parses WCL des kills (`rankings.json`, Parse Lord).
- Listes en config (`config/crawl.json` → `extras` : 11 taunts, 26 CD défensifs). Ce sont des filtres WCL : après une modification, recrawler avec `--refresh`.
- `--cost` mesure les points dépensés par requête. Une stat sans données reste dans `meta.pending`.

**Parse Lord.** Seul achievement mesuré contre le monde et non contre la guilde, ce qui revient sur « pas de parses WCL sur le site » pour cette stat seulement (sera mise en avant différemment). Parses des kills de Fable : par boss, moyenne du meilleur et du médian, puis moyenne sur les boss. DPS et healers, au moins 5 boss. Titre réservé aux 5 % du haut (`title_percentile: 95` sur la stat, au lieu de 90).

**Écarté.** `characterRankings` par personnage (milliers de requêtes, et compte les kills hors guilde).
