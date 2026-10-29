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
- `/` : choix de guilde, deux grandes cartes Fable puis NightShift ;
- `/fable/` : le site actuel, inchangé à part le bandeau (« Classic Logs Timewalking » mène au choix de guilde, lien « Fable » dans la barre pour revenir à l'accueil de la guilde) ;
- `/nightshift/` : seulement le texte « Coming soon ».

Assets partagés (favicon, icônes de rang) à la racine de `site/public/`, ceux d'une guilde dans `site/public/<guilde>/`. Le pipeline écrit dans `site/public/fable/data/`. Données et rangs sont chargés en chemins relatifs à la page (`./data/`, `../ranks/`), identiques en dev et au build.

**Raison.** Préparer l'arrivée d'une deuxième guilde (NightShift) sans toucher au site de Fable.

**Écarté.** Une seule app avec la guilde dans le hash (`#/fable/...`) : URL moins lisible, et toutes les guildes chargeraient le même bundle de données.

**Reste ouvert.** Le pipeline et `CLAUDE.md` restent mono-guilde (Fable, fiche WCL 482770) ; NightShift est sur Thunderstrike (EU) ; la brancher demandera sa fiche WCL et sa faction (les icônes de rang sont Alliance).

## 2026-10-28 — Thème Horde pour NightShift, page de choix coupée en deux

**Décision.**
- NightShift est une guilde Horde : thème rouge. La classe `.horde` redéfinit les mêmes tokens que le thème Alliance (`--navy*` en rouge sombre, `--alliance*` en rouge Horde `#d4252c`). Elle s'applique au `<body>` de `/nightshift/` et à la carte NightShift de `/`.
- Fond de `/` : bleu côté Fable (1re carte : à gauche, ou en haut sur téléphone), rouge côté NightShift, séparés par une découpe à quelques larges dents (`clip-path`), tracée d'un trait blanc de 1,5 px avec un léger glow (SVG). Une luciole (point lumineux fixe, sans pulsation) parcourt d'un trait la partie visible de la découpe, de haut en bas (de gauche à droite sur téléphone), à vitesse constante (2200 px/s, sans easing), s'éteint, attend environ 9 fois la durée du trajet, puis repart ; masquée si `prefers-reduced-motion`. La géométrie est dans `site/src/split.js`, qui calcule en px la découpe, le trait blanc et le trajet de la luciole (`offset-path`) à partir des mêmes points, et les recalcule au redimensionnement ; sans JS, le fond est simplement coupé en deux moitiés droites. La page `/` fait la hauteur de l'écran visible (`100svh`, barre d'adresse mobile comprise) et coupe le calque (`overflow: clip`), qui sinon allongeait la page et faisait apparaître une barre de défilement. Le calque est ancré sur la grille des cartes, pas sur l'écran : la déchirure passe toujours dans l'espace entre les cartes (72 px sur téléphone, 96 px à partir de 560 px), où ses dents restent courtes, et mord plus largement ailleurs. « Pick a guild » en crème, majuscules espacées, avec une ombre sombre pour rester lisible sur les deux fonds. Sur téléphone (cartes empilées), elle est horizontale ; à partir de 560 px, verticale au milieu.

**Raison.** Marquer la faction de chaque guilde dès la page d'entrée.

**Écarté.** Calque fixé sur l'écran (sur téléphone la cassure tombait en plein dans la carte NightShift). Dégradé doux entre les deux couleurs (moins net que la cassure demandée).

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

**Coût mesuré** (essai du 2026-10-28, 3 rapports) : 1 point par pull (tirs alliés, taunts, consommables, CD), ~0,7 point par rapport pour le trash, ~1 + 2 points par kill pour les parses. Pour tout l'historique (~6 000 pulls, ~5 000 kills, ~800 rapports) : environ 18 000 points, soit ~6 h de budget, dont 11 000 pour les parses.

**Écarté.** `characterRankings` par personnage (milliers de requêtes, et compte les kills hors guilde).

---

## 2026-10-28 — Hours Raiding : durée des soirées, plus seulement les combats de boss

**Décision.** Hours Raiding compte, pour chaque soirée d'un personnage, le temps de son premier à son dernier pull de boss éligible (même découpage en soirées que « Hours in raid » sur l'accueil : coupure à plus de `night_gap_hours` d'écart). Le trash entre deux boss est donc compté, celui avant le premier boss non (pas dans le cache). Pour rester additif, le temps est réparti sur ses pulls : de la fin du pull précédent à la fin de celui-ci.

**Raison.** La durée des seuls combats de boss ne faisait qu'environ 20 % d'une soirée (59 h contre 286 h en Era), soit ~0,7 h par semaine pour les plus assidus, loin du ressenti. Après le changement : ~2,7 à 3 h par semaine.

## 2026-10-28 — Accueil : section « Guild Legends » (stats épinglées)

**Décision.** The Gang et Parse Lord (`home.pinned`) sont toujours affichés au-dessus du Hall of fame et sortis de son tirage. Mise en valeur :
- titre « Guild Legends » (`home.pinned_title`) encadré de filets dégradés et de losanges, en or ;
- un seul panneau sans bordure pour les deux cartes, fond marine avec un léger halo parchemin venant du haut, padding large, trait court couleur parchemin entre les deux (horizontal sur téléphone) ;
- top 5 (`home.pinned_top_n`) au lieu du top 3 ; les joueurs classés 1er, 2e ou 3e sont agrandis selon leur place, ex aequo compris (deux 1ers ont la même taille) (nom en Oswald, macaron agrandi) ; seul le n°1 a la position et la valeur en or ;
- l'or (`--gold-text`, `#f3cf7a`) n'est utilisé nulle part ailleurs sur le site, pour rester le signal du prestige ;
- reflet lumineux lent sur le nom des n°1 (un balayage toutes les 7 s), coupé si `prefers-reduced-motion`.

**Raison.** Faire ressentir le prestige de ces deux stats par la mise en scène du n°1 plutôt que par un cadre.

**Écarté.** Cadre épais doré et couronnes de laurier dans les coins (essayés : trop chargés).

---

## 2026-10-28 — Rang PvP : seuil de 2 semaines pour Naxx Era

**Décision.** Un tier peut fixer son propre seuil (`min_weeks` dans `config/tiers.json`, à la place de `rank.min_weeks_per_tier`). Naxx (Era) passe à **2 semaines de reset**.

**Raison.** La guilde n'a que 5 semaines de logs de Naxx en Era avant TBC : avec 4 semaines, une seule absence suffisait à rater le tier (ex. Rassaa, 3 semaines).

## 2026-10-28 — Most Soundboard dans Guild Legends, section Ghosts of Fable

**Décision.**
- Guild Legends : Parse Lords cède sa place à **Most Soundboard**, une distinction faite main, sans stat ni page : 1. Rassaa, 2. Yogiqt, chacun avec un portrait détouré (ours couronné pour Rassaa, nain guerrier couronné pour Yogiqt ; `site/public/fable/legends/`, WebP transparent recadré, 400 px de haut). Pas de numéro ni de macaron de rang : portrait à gauche, nom à droite, le premier en plus grand et en or. Le portrait garde son détourage d'origine (retirer son halo sombre trouait la fourrure) et s'intègre par une ombre portée et un léger halo parchemin en CSS. Le portrait de Yogiqt (illustration sur fond de lave) est détouré avec `rembg` (modèle `u2net`, plus net que `isnet-general-use` sur l'armure), installé dans le `.venv` avec le modèle dans `data/models/` (ignoré par git, `U2NET_HOME`), recadré sur le buste, bas fondu en dégradé (le personnage sort du cadre), affiché un peu plus petit que l'ours. Le nom et la légende du premier sont centrés à droite du portrait. Une entrée de `home.pinned` peut donc être un objet `{id, title, description, entries}` au lieu d'un id de stat. Parse Lords retourne dans le tirage du Hall of fame ; sa suppression reste ouverte (proche de Big Pumper).
- **Ghosts of Fable**, sous le Hall of fame : tous les raideurs vus dans des pulls éligibles qui n'ont pas les 15 semaines de reset, en pastilles (classe la plus jouée, nombre de semaines), du plus de semaines au moins ; les 60 premiers, puis « Show all ». Suit le filtre d'extension. Données : `meta.ghosts`, calculé par l'export.

**Raison.** Honorer les membres pour autre chose que les logs ; donner une place à ceux qui sont passés par la guilde sans y rester assez pour les classements.

## 2026-10-28 — Fiche joueur : « Your best friend » ; macarons de rang recadrés

**Décision.**
- Encart **Your best friend** de la fiche joueur, sous les filtres et au-dessus de l'aperçu : le joueur classé avec qui il a partagé le plus de soirées de raid. Une soirée partagée = au moins un même pull éligible ce soir-là (soirée = date à Sydney − 6 h, pour garder les pulls d'après minuit sur leur soirée). En cas d'égalité : « Your best friends » et tous les noms séparés par des virgules. Indépendant des filtres. Calculé par l'export (`players.json` → `friends: {names, nights}`), textes dans `config/site.json` → `player.best_friend`.
- **Macarons de rang** : la découpe ronde coupait les coins des emblèmes. Les icônes sont réduites à 70 % et posées sur un fond bleu radial dans leurs propres tons, bords fondus (`scripts/make_ranks.py`, originaux dans `site/assets-src/ranks/`, sortie 112 px). Taille par défaut du macaron passée de 20 à 22 px pour garder l'emblème lisible.

**Écarté.** Compter les semaines de reset partagées (trop large : deux groupes d'une même semaine ne raident pas ensemble).

## 2026-10-29 — Combats en véhicules exclus

**Décision.** Flame Leviathan (Ulduar, encounter 744) et Icecrown Gunship Battle (ICC, 847) sont retirés de toutes les stats et de tous les records, au calcul (`config/compute.json` → `excluded_encounters`). Le cache brut les garde. 60 pulls de 25 joueurs retirés.

**Raison.** Les dégâts, soins et morts y sont ceux des véhicules et des canons, pas le jeu des joueurs : ils fausseraient la base 100 et les stats de mort.

**Écarté.** Les retirer au crawl (les pulls étaient déjà en cache) ; les garder pour les seules stats de présence (simplicité : une seule règle).

## 2026-10-29 — Consommables en WotLK

**Décision.** En WotLK, The Junky (et The Unprepared) ne lisent plus les compteurs WCL `potionUse` / `healthstoneUse`, presque toujours à 0 (365 potions sur 2 019 pulls, contre ~1 par joueur et par pull en TBC, Cata et MoP). Comme en Era, les consommables sont comptés depuis un tableau Casts filtré, récupéré par le complément au crawl, mais par **ID de capacité** (`config/compute.json` → `wotlk_consumable_ids`) : Speed 53908 (la potion la plus utilisée), Wild Magic 53909, Runic Healing / Mana Potion 43185 / 43186, Indestructible 53762, injecteurs 67489 / 67490, Fel Healthstone 47875-47877. En attendant le complément, le tableau Casts de niveau 2 (5 capacités par joueur) sert de repli.

**Vérifié.** En TBC, le compteur WCL compte bien Haste (28507) et Destruction (28508) : pour chaque joueur dont le tableau Casts montre l'une d'elles, `potionUse` est au moins égal au nombre de lancers (1 412 cas sur 1 412). TBC, Cata et MoP gardent donc les compteurs WCL.

**Écarté.** Filtrer par nom en WotLK : la potion de vitesse se lance sous le nom « Speed », trop ambigu.

## 2026-10-29 — Logs de PTR exclus

**Décision.** Six rapports de la fiche de guilde sont des logs de PTR, tous avec « PTR » dans le titre : ToGC (mai 2023, dont un en 10), Hyjal et BT (8 et 9 janvier 2022), et deux d'août 2021 sans boss. Ils sont exclus de toutes les stats par une liste de codes (`config/crawl.json` → `excluded_reports`) ; le cache brut les garde, le complément au crawl les saute. 37 pulls éligibles retirés (10 kills), 38 personnages vus seulement sur le PTR disparaissent.

**Vérifié.** Aucun autre rapport n'est antérieur à la sortie live de son raid (premiers rapports de chaque zone comparés aux dates de sortie). Les trois rapports « prepatch » de mai 2024 sont le prépatch Cata sur les serveurs live, gardés.

**Écarté.** Filtrer sur le mot « PTR » dans le titre : une liste explicite est plus lisible, et les données ne bougeront plus.

## 2026-10-29 — Seuil par rôle : 10 semaines de reset

**Décision.** En plus des 15 semaines de reset (tous personnages) pour apparaître dans les classements, un joueur doit avoir **au moins 10 semaines de reset dans un rôle**, tous personnages confondus, pour être classé sur ce rôle (`config/site.json` → `min_role_weeks`).
- Achievements tank, healer et DPS : toujours.
- Achievements communs : seulement quand le filtre de rôle est actif ; sans filtre, seules les 15 semaines comptent.
- Fiche joueur : une section de rôle n'apparaît que si le joueur a ses 10 semaines dans ce rôle (règle l'ancien point « seuil minimal pour afficher un rôle sur la fiche »).

L'export donne `role_weeks` par joueur ; le site ignore les cellules d'un rôle sous le seuil. Résultat au 2026-10-29 : 26 tanks classés sur 36, 131 DPS sur 149, 46 healers sur 64.

**Raison.** Les off-specs et rerolls de passage, avec peu de pulls, sortaient en tête de certains classements de rôle (taux sur un petit échantillon).

**Écarté.** Un seuil en nombre de pulls (`min_den`) : il reste, mais 10 pulls se font en une soirée ; les semaines mesurent une vraie présence dans le rôle.

## 2026-10-29 — Fiche joueur : cartes de totaux avec bandeau de rang

**Décision.** Sous « Your best friend », trois cartes mises en avant : **Total damage done**, **Total damage taken**, **Total healing done**, en raid (pulls de boss éligibles, kills et wipes ; soins effectifs, sans le surplus). Ce sont trois stats `sum` de catégorie `overview` (`damage-done`, `damage-taken`, `healing-done`) : elles ont leur page de classement, suivent les filtres, mais restent hors du Hall of fame et du compte des achievements. Réglage : `config/site.json` → `player.highlights`.

Un **bandeau en coin** (à gauche) affiche le rang dans la guilde (« #7 ») sous les filtres actifs, coloré comme un parse WCL : jaune clair pour le n°1, puis selon le percentile rose (99+), orange (95+), violet (75+), bleu (50+), vert (25+), gris. Texte du bandeau en marine foncé (fonds clairs). La bordure et le halo de la carte prennent la même couleur.

**Corrigé au passage.** Le seuil de 10 semaines par rôle ne s'applique d'office qu'aux achievements tank / healer / DPS ; il touchait aussi la catégorie `overview` (tuiles d'aperçu), qui ne le subit plus que sous filtre de rôle, comme les communs.

## 2026-10-29 — Fiche joueur : titres de section, cartes de totaux plus visibles

**Décision.**
- La fiche joueur a maintenant des **titres de section**, ornementés comme « Guild Legends » sur l'accueil : **Player Contribution** au-dessus des trois cartes de totaux, puis **General** (communs), **Damage Dealer**, **Tank**, **Healer** au-dessus des sections de catégorie. Textes dans `config/site.json` → `player.section_titles` ; une clé absente n'affiche pas de titre. Remplace la règle « sections sans titre, séparées par un grand espace ».
- Cartes de totaux : bandeau de rang à **largeur fixe** et texte centré, à 45° (la largeur variait avec la longueur du rang, d'où un mauvais alignement d'une carte à l'autre) ; **violet plus foncé** (`#8b3fd9`, texte blanc) que celui des parses ; halo et dégradé de la couleur du bandeau sur la carte, halo sur la valeur comme sur les titres ; plus d'espace sous les cartes.

## 2026-10-29 — Totaux de carrière comparables entre extensions

**Décision.** Les trois totaux de la fiche joueur (dégâts infligés, dégâts subis, soins) sont **classés en « SoO terms »**, le vrai total restant affiché à côté, en petit, entre parenthèses. Pour chaque pull, le montant du joueur est divisé par le débit de référence de ce pull, ce qui donne des « secondes de raideur moyen », puis multiplié par le débit médian de la guilde sur les kills de Siege of Orgrimmar (`config/compute.json` → `scaled_totals_tier`) :
- dégâts infligés : médiane des DPS du pull ;
- soins : médiane des healers du pull ;
- dégâts subis : **moyenne** du raid (en raid de 40, le joueur médian ne prend presque rien et les tanks d'Era valaient des multiples énormes de cette médiane : deux tanks à 30 M de dégâts réels arrivaient 4e et 5e).

Cellules `[converti, réel]`, nouveau mode d'agrégation `scaled` (classé sur le converti, réel dans `extra`).

**Raison.** Les débits explosent d'une extension à l'autre (DPS médian des DPS sur les kills : 426 en Era, 1 423 en TBC, 7 916 en WotLK, 29 042 en Cata, 190 779 en MoP) et au sein d'une extension (MSV 111k, SoO 268k). Le calcul au pull absorbe l'écart entre extensions, la progression du stuff dans un tier et les combats particuliers (buff d'ICC). Comme c'est une somme, il compte à la fois la présence et la performance : voulu pour un total de carrière.

**Écarté.** Un facteur par extension (trop grossier : écart ×2,4 entre MSV et SoO) ; les PV moyens des boss (rien pour les soins et les dégâts subis, adds et phases, taille de raid, stuff qui progresse alors que les PV restent fixes).

## 2026-10-29 — Totaux de carrière : référence BWL (Era) au lieu de SoO

**Décision.** Les totaux de carrière sont exprimés en « BWL terms » : débit médian de la guilde sur les kills de Blackwing Lair en Classic Era (`scaled_totals_tier: "bwl"`), au lieu de Siege of Orgrimmar. L'ordre des classements ne change pas (la référence n'est qu'un facteur commun), seule l'échelle affichée change.

**Raison.** Classic Era a connu très peu de powercreep au cours de l'extension : BWL est une référence stable et parlante pour la guilde, là où SoO est le sommet d'une montée rapide (MSV 111k → SoO 268k de DPS médian).

## 2026-10-29 — Rerolls mineurs : sous 5 semaines de reset

**Décision.** Un personnage joué moins de **5 semaines de reset** (`config/site.json` → `min_char_weeks`) est un reroll mineur :
- il reste **listé sur la fiche joueur** (tous les rerolls le sont, y compris ceux de classe inconnue), mais sans sa classe ni sa pastille de couleur ;
- sa classe ne donne **pas de puce** à côté du nom du joueur (sauf si un autre personnage de cette classe a ses 5 semaines) ;
- il ne compte **pas pour The Undecided**.

L'export donne les semaines de chaque personnage (`players.json` → `chars: [nom, classe, semaines]`).

**Raison.** Un reroll monté pour une soirée ajoutait une puce de classe et un personnage à The Undecided, comme un vrai reroll.

## 2026-10-29 — Audit des stats : corrections et nouvelles stats

Audit des stats sur les données réelles (8 714 pulls après dédoublonnage). Valeurs avant → après sur le classement sans filtre.

**Corrections.**
- **Scores base 100** (`facts.add_scores` et `export_site.base100`) : la médiane du rôle laisse de côté les joueurs à 0 et demande au moins 3 joueurs au-dessus de 0 (`min_score_peers`), sinon pas de score. Avant : un healer à 40 444 (deux autres « healers » à 0 et 752), un tank à 26 019, un Healers Love Him à 1 110 323 (pull court, médiane de 1).
- **Stats communes sur le score de performance** (Metronome, Comfort Boss, Clutch Player, Glow Up) : DPS et healers seulement. Le score d'un tank est ses dégâts subis ; les tanks et un healer à 40 444 finissaient derniers de Metronome (σ 909).
- **Tanks en Era** : WCL ne donne tank que les talents Protection / Guardian. Ceux-là restent tanks ; les autres ne le deviennent qu'à **25 %** de la mêlée du boss ou des adds (au lieu de 10 % pour tous). Avant : 946 lignes tank en spé Fury (Aye n°1 de Secret DPS à 1 170), et de vrais tanks passés DPS en bas de Big Pumper et en haut de One Button Wonder.
- **Expansion d'un rapport** : `config/crawl.json` → `report_expansion` force l'extension des rapports mal étiquetés. `LKkhdpbfD6Tq41Q3` (Throne of Thunder étiqueté Firelands) mettait 22 pulls de Lei Shen en Cata.
- **Healers Love Him** : soins reçus des autres (ses propres soins, potions et pierres de soins exclus), base 100 contre le rôle dans le pull, puis divisés par la **moyenne** de sa classe et de son rôle dans l'extension. Avant : les 5 premiers étaient des démonistes (Life Tap). La médiane de classe a été écartée : elle vaut 0 ou presque pour les classes qui ne reçoivent presque jamais de soins.
- **Final Boss Energy** : score sur les boss de fin **moins** score sur les autres boss (`diff`). Avant, c'était le score sur les boss de fin, avec le même top 3 que Big Pumper. « Nefarian's End » (BWD) ajouté aux boss de fin.
- **Fishbait** : le premier mort est cherché parmi les joueurs seulement (72 pulls n'avaient pas de premier mort).

**Changements.**
- **Night Owl supprimé** : 95 pulls sur 8 714 commencent après minuit, maximum 5,9 %. `compute.json` → `night` devient `timezone`.
- **Arch-Nemesis** sans « Melee » (`arch_nemesis_ignore`) : « Melee » était l'ennemi juré de 131 joueurs sur 155 ; sans lui, il y a 34 ennemis différents.
- **Glow Up** : seulement les joueurs avec des kills notés dans au moins 3 tiers de raid sous les filtres (`min_tiers`, tiers exportés dans la cellule `slope`).
- **The Undecided** devient **Identity Crisis** (id `identity-crisis`).

**Nouvelles stats** (communes) : Heartbreaker, Spectator, Iron Man, Comeback Kid, Late Arrival, Early Leaver, Loot Hoarder, Self-Made, Guardian Angel, Personal Hell, Obliterated, Suicide Pact, Pioneer (définitions dans `docs/stats.md`). Nouvelles agrégations `streak` et `gap` (semaines de raid de la guilde numérotées à la suite, les semaines sans raid de guilde ne comptent pas comme absences) et format `times`.
- **Obliterated** : overkill rapporté à l'overkill médian de l'extension ; les mécaniques d'exécution sont détectées et exclues (capacité dont le plus petit overkill dépasse 30 fois cette médiane, au moins 3 morts : Ethereal Corruption, Rocket Strike, Ascend to the Heavens, Dark Glare, Hand of Death…). **Écarté** : la médiane par boss ou par capacité, trop instable (une médiane de quelques points donnait des valeurs de 500 000).
- **Suicide Pact** : morts à 10 s d'écart au plus, en ne comptant que les morts d'avant le premier cinquième du raid au sol (sinon chaque wipe associerait tout le monde).

**En question.** Top of the Meters (part des kills finis n°1 des DPS) : corrélation de rang 0,84 avec Big Pumper, mais 3 noms en commun seulement dans les top 10 ; elle récompense les pics plus que la régularité et dépend de la composition du raid.

**Étudié, pas appliqué.** Retirer les boss sans points All Stars sur WCL. Relevé fait avec un DPS de la guilde par zone et difficulté : 34 boss, presque tous en Cata et MoP (Alysrazor, Spine of Deathwing, Lei Shen, Sha of Pride…). Impact : Main Character Moment change beaucoup (le meilleur pull de 41 joueurs sur 144 est sur un de ces boss, dont le top 3 actuel, tous sur Alysrazor) ; Big Pumper et Healing Machine bougent peu (9 noms sur 10 restent dans le top 10) ; les totaux de carrière perdent 25 % de leur volume. La liste MoP reste à vérifier sur le site WCL avant de l'utiliser.

## 2026-10-29 — Illustrations Varian et Garrosh sur le choix de guilde

**Décision.** Sur `/`, chaque moitié porte une illustration à 50 % d'opacité, fondue vers la découpe et vers le haut et le bas : Varian côté Alliance (Fable), mis en miroir pour faire face à Garrosh, et Garrosh côté Horde (NightShift), placé dans le calque rouge pour suivre la découpe. Sur téléphone, Varian occupe la moitié haute de l'écran et Garrosh la moitié basse. Les images sont calées sur l'écran (et non sur le calque de la découpe) grâce aux variables `--screen-top` / `--screen-h` posées par `split.js`.

**Raison.** Donner une identité Alliance contre Horde à la page d'entrée.

**Écarté.** Les images en plein contraste : elles gênaient la lecture des cartes et du titre.

## 2026-10-29 — Luciole plus lente, avec traînée de lumière

**Décision.** La luciole du choix de guilde parcourt la découpe à 1000 px/s au lieu de 2200, soit 18 % du cycle ; la pause reste à peu près aussi longue qu'avant. Elle laisse une traînée continue de 30 images rémanentes : des copies qui suivent le même chemin à 5 ms d'écart (environ 5 px), de plus en plus petites et pâles, dont les halos se fondent en un seul trait de lumière d'environ 150 px. Le halo de la luciole elle-même reste modéré (14 px). Elle alterne le sens à chaque passage : haut → bas, pause, bas → haut, pause (gauche ↔ droite sur téléphone) ; la traînée reste derrière elle dans les deux sens. Couleurs : jaune très pâle, presque blanc (cœur `#fffef5`, halo `#fff7c4` / `#ffef94`) au lieu du jaune-vert. Les copies sont créées par `split.js` ; le chemin et la durée passent par les variables `--fly-path` et `--fly-time` du calque.

**Raison.** On voyait mal la luciole à 2200 px/s. Une traînée de points espacés ressemblait à un collier de perles ; on voulait un effet de résidu de lumière.

**Écarté.** Une traînée en dégradé orientée selon le chemin (`offset-rotate: auto`) : elle pivote d'un coup aux angles de la découpe, alors que les copies suivent les angles. La propriété `scale` pour rétrécir les copies : elle s'applique aussi au déplacement le long du chemin et les sort de la découpe.

## 2026-10-29 — Damage Done avec le trash, interrupteur « Bosses only »

**Décision.**
- L'ancienne stat **Damage Done** devient **Damage Done to Bosses** (`damage-done-bosses`), avec le même calcul.
- Une nouvelle **Damage Done** (`damage-done`) ajoute les dégâts sur le trash des mêmes soirées (`reports/<code>/trash.json`, crawl complémentaire). Une soirée loggée dans plusieurs rapports ne compte que le trash du rapport qui porte le plus de pulls de boss retenus. Le trash d'un personnage va à son rôle principal de la soirée. Il est converti en « BWL terms » au taux de la soirée : la médiane des débits de référence de ses pulls de boss.
- Sur la fiche joueur, la carte « Total damage done » affiche Damage Done par défaut. Un interrupteur **Bosses only** (rail et curseur, rôle ARIA `switch`, `player.highlights[].toggle`) la bascule vers Damage Done to Bosses : valeur, rang et bandeau suivent.

**Raison.** Le trash est une part réelle de la soirée de raid, mais le total boss seul reste la base de comparaison la plus propre.

**À savoir.** Tant que le crawl complémentaire n'est pas fini, seul le trash des soirées déjà crawlées est compté (67 soirées au 2026-10-29) ; la description de la stat le dit.

## 2026-10-29 — Sniper / Sniped, comparé à la classe

**Décision.** La stat healer `sniper` devient `sniped`. Le titre principal **Sniper** (bleu) va au **moins** d'overheal (`direction: asc`), le revers **Sniped** (rouge) au plus d'overheal. Le taux d'overheal de chaque pull est ramené en base 100 contre la médiane des healers de la même classe dans la même extension, puis moyenné.
- Haut du classement : ses soins arrivent sur des cibles qu'un autre a déjà remontées.
- Bas du classement : c'est lui qui passe le premier.

**Raison.** Un fort overheal vient surtout d'un autre healer plus rapide. Dans le jargon, le sniper est celui qui vole le soin, pas celui qui le perd. Surtout, l'overheal dépend d'abord de la classe : 73 % pour les paladins WotLK (Beacon of Light), 23 % pour les prêtres WotLK (boucliers Discipline sans overheal), contre une vingtaine de points d'écart au plus entre joueurs d'une même classe. Avant la correction, la stat classait des classes plutôt que des joueurs. Après, les deux bouts du top 10 mélangent druides, paladins, prêtres et chamans.

**Écarté.** Savoir qui a « snipé » qui : il faut les événements de soin (niveau 3), c'est le True Sniper reporté en V2.

## 2026-10-29 — Blamed the Healer : tolérance d'une seconde ; Timekeeper comparé à la classe

**Blamed the Healer.** Un cooldown défensif retiré jusqu'à 1 s avant la mort d'un tank compte comme actif (`cd_death_tolerance_ms`). WCL enregistre la fin des buffs d'un joueur qui meurt 100 à 400 ms avant sa mort : sans tolérance, aucune mort ne passait (2 sur 2 065 morts de tanks en Era et TBC). Avec 1 s, 52 morts réparties sur 8 tanks classés.

**Timekeeper / The Tourist.** La part des dégâts sur le trash de la soirée, en base 100 contre la médiane des DPS de la soirée, est divisée par la moyenne de sa classe dans l'extension. Un personnage qui a tanké un boss dans la soirée est écarté.
- **Raison.** Les classes à sorts de zone dominaient (mages 111, druides 73 en moyenne). Des tanks Era joués DPS sur les boss, mais qui tankaient le trash, finissaient en bas.
- **Écarté : l'activité** (temps actif sur le trash). Elle varie peu (65 à 126), favorise la mêlée grâce à l'attaque automatique et les tanks du trash, ressemble peu aux dégâts (corrélation de rang 0,23) et ferait doublon avec The Sweat.

## 2026-10-29 — Trash dans The Terrorist, Attention Seeker et The Nut Crusher ; Healers Love Him par boss ; Divine Sacrifice retiré

**The Terrorist.** Part du joueur dans le friendly fire total du raid, au lieu de ses dégâts alliés rapportés aux dégâts subis par le raid : Σ ses dégâts alliés ÷ Σ ceux du raid, sur les pulls de boss (kills et wipes) et le trash des soirées où il était. Le seuil `min_den` porte sur le nombre de pulls (ou soirées de trash) où le raid a fait du friendly fire : troisième valeur de la cellule, `"min_den_on": "count"`. Le nombre affiché est la somme de ses dégâts alliés. Avant, ce nombre était une somme de parts : 0 pour tout le monde.
- **Écarté : la moyenne des parts par pull.** Le friendly fire est rare (4 % des pulls WotLK, presque tous sur Yogg-Saron) : un Kel'Thuzad à 30 000 de friendly fire de raid, dont un joueur fait la moitié, pesait autant qu'un Yogg à 377 000. Kosmo (13,6 % du friendly fire de ses pulls) passait derrière Tenzin (12,1 %).
- **Écarté : la part sur toute l'extension ou par tier**, présent ou non : elle revient à classer sur le total, donc sur le temps de jeu, déjà affiché en nombre.

**The Nut Crusher.** Interruptions **par heure** (et non plus par pull) sur les pulls de boss et le trash des soirées où le raid a interrompu quelque chose : le trash d'une soirée ne peut pas compter comme un pull. Seuil `min_den` sur le nombre de pulls (`"min_den_on": "count"`). Troisième tableau de `trash_extra`.

**Attention Seeker.** Les taunts sur le trash comptent, avec la durée du trash du rapport (`totalTime`), pour les personnages qui ont tanké les boss ce soir-là.

**Crawl.** Nouveau type `trash_extra` dans `pipeline.crawl_extra` : une requête par rapport, deux tableaux sur le trash (`killType: Trash`), les dégâts entre joueurs et les taunts, mêmes filtres que par pull. Le trash d'une soirée enregistrée dans plusieurs rapports ne compte qu'une fois : on garde le rapport qui contient le plus de pulls retenus, comme pour Damage Done.

**Healers Love Him.** Deux changements :
- base 100 contre la médiane du **rôle sur le même boss** (tous les pulls de l'histoire), et non plus du rôle dans le pull ;
- référence de classe = médiane des moyennes de ses joueurs (une voix par joueur ayant au moins `min_den` pulls dans la classe), sans correction de classe sous 3 votants (`min_score_peers`).
- **Raison.** Un healer Chaman WotLK montait à 1 370 alors qu'il recevait des autres autant que ses collègues (33 000 par pull contre 26 000 à 69 000). Les healers reçoivent si peu de soins des autres que la médiane d'un pull était parfois minuscule, et quelques pulls donnaient des scores énormes. La moyenne de classe par ligne était aussi dominée par le joueur aux 1 233 pulls sur 1 413.
- **Essayé** : la voix par joueur seule, en gardant la médiane du pull. Pire (2 371), et elle faisait monter les tanks Era dont la classe compte beaucoup de petits off-tanks.

**Blamed the Healer.** Divine Sacrifice retiré des CD défensifs : c'est un CD de raid lancé par un paladin healer, pas un CD du tank (21 morts de tank en WotLK). Il est retiré de la liste du crawl, et son ID (64205) est ignoré au calcul pour les données déjà crawlées (`cd_ignored_ids`). Anti-Magic Shell reste.

## 2026-10-29 — MoP : Mogu'shan, Heart of Fear et Terrace forment un seul tier

Mogu'shan Vaults, Heart of Fear et Terrace of Endless Spring sont fusionnés en un tier `t14` (« MSV / HoF / ToES ») dans `config/tiers.json` : c'est le même tier d'équipement (T14), sorti en une seule phase en MoP Classic. 18 tiers au lieu de 19. Effet : rang PvP (un tier validé de moins possible en MoP) et Glow Up (au moins 3 tiers).
