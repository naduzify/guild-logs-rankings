# Contrat de données pipeline → site

Le pipeline écrit trois fichiers JSON dans `site/public/fable/data/` (dossier ignoré par git, régénéré au build). Le site les charge au démarrage et ne fait que **filtrer, sommer et classer** : aucune règle de stat n'est codée côté React.

Tant que l'étape de calcul n'existe pas, `python -m pipeline.mock_site_data` écrit des données fictives au même format (`meta.mock = true`, le site affiche alors un bandeau).

## Pourquoi des « cellules additives »

Chaque stat se filtre par extension × classe × rôle, en multi-sélection (comme l'artifact « Fable Guild Rankings »). Trop de combinaisons pour tout précalculer. Le pipeline exporte donc, pour chaque stat, des **cellules** au grain `(joueur, extension, classe, rôle)` qui contiennent des quantités qu'on peut additionner (numérateur, dénominateur, sommes de régression…). Le site additionne les cellules qui passent les filtres, calcule la valeur de chaque joueur, puis le percentile parmi les joueurs qui ont une valeur.

## `meta.json`

```
generated      date ISO de l'export
mock           true si données fictives
guild          {name, server}
expansions     [{id, label, short}]            ← config/tiers.json
tiers          [{id, name, short, expansion}]  ← config/tiers.json
classes        ["Death Knight", "Druid", …]    (ordre = index utilisé dans les cellules)
roles          ["TANK", "DPS", "HEALER"]      (idem)
rank           {max, names[14]}                ← config/tiers.json
settings       {title_percentile, flip_percentile, min_den, min_role_weeks}  ← config/site.json
home           {top_n, pinned[], pinned_title, pinned_top_n, featured_count, records[]}  ← config/site.json
player         {overview[], highlights[], featured_per_category, featured_min_pct, visible_small}  ← config/site.json
stats          [définitions]                   ← config/stats.json
guild_totals   [[exp, pulls, kills, wipes, damage, boss_seconds, raid_seconds]]  (une ligne par extension)
               boss_seconds = durée cumulée des pulls de boss, kills et wipes (Hours on bosses)
               raid_seconds = durée cumulée des soirées de raid : pour chaque rapport retenu, du début du premier combat
                              (trash compris) dans une zone éligible à la fin du dernier pull de boss éligible (Hours in raid)
guild_raiders  [[mask, count]]  nombre de joueurs (main + rerolls) ayant au moins un pull éligible, par masque de bits
               des extensions où ils ont raidé (bit e = extension e). Le site compte ceux dont le masque croise le filtre.
guild_bosses   [[exp, boss, heroic, kills, wipes, fastest_kill, slowest_kill]]  (une ligne par boss × difficulté ; durées des kills en secondes, null sans kill)
```

## `players.json`

Liste des joueurs qualifiés (15 semaines de reset). L'index dans la liste est l'identifiant utilisé partout ailleurs.

```
{ "name": "Rassaa",                      main du mapping des rerolls
  "chars": [["Rassaa", 1], ["Torean", 6]],  personnage, index de classe
  "tiers": [0, 1, 2, 5],                  tiers validés pour le rang (index dans meta.tiers)
  "rank": 4,                              min(rank.max, nombre de tiers validés)
  "role_weeks": [3, 40, 12] }             semaines de reset distinctes par rôle (ordre de meta.roles), tous personnages
```

Un tier est validé quand le joueur y a au moins `rank.min_weeks_per_tier` semaines de reset distinctes de présence (config/tiers.json), ou le `min_weeks` propre au tier s'il en a un (Naxx Era : 2). Le rang ne dépend pas des filtres.

## `stats.json`

```
{ "<stat id>": [[joueur, extension, classe, rôle, ...valeurs], …] }
```

Les valeurs dépendent du mode `agg` de la stat :

| agg | valeurs | valeur du joueur |
|---|---|---|
| `ratio` | `num, den` | Σnum / Σden |
| `parse` | `avg, n, best, median` (un boss par ligne) | Σavg / Σn ; le site affiche aussi Σbest / Σn et Σmedian / Σn (Parse Lords) |
| `sum` | `n` | Σn |
| `distinct` | `[ids]` | taille de l'union des ids (semaines, boss, personnages) |
| `diff` | `a, ad, b, bd` | Σa/Σad − Σb/Σbd |
| `spread` | `n, s, ss` | écart-type : √(Σss/Σn − (Σs/Σn)²) |
| `slope` | `n, sx, sy, sxx, sxy` | pente de régression de y (score) sur x (semaine) |
| `top` | `{label: [num, den]}` | label au plus grand Σnum (`top_by: count`) ou Σnum/Σden (`top_by: mean`) ; `top_by: share` : label au plus grand Σnum parmi ceux qui ont Σden ≥ `min_den`, valeur = sa part de Σnum de tous les labels |
| `max` | `v, label` | plus grande valeur, avec son label |

Les cellules d'un rôle où le joueur a moins de `min_role_weeks` semaines (`role_weeks`) sont ignorées : toujours pour les achievements tank / healer / DPS, et pour les communs quand le filtre de rôle est actif. Sans `role_weeks` (données fictives), tout passe.

Un joueur n'a de valeur que si le dénominateur filtré atteint `min_den` (réglage global de `config/site.json`, surchargé par stat) : `den` pour `ratio`, le plus petit de `ad` et `bd` pour `diff`, `n` pour `spread` et `slope`.

## Champs d'une stat (`config/stats.json`)

- `category` : `common`, `tank`, `healer`, `dps`. Les cellules des stats de rôle n'existent que pour ce rôle. `overview` : stats génériques (heures, kills, wipes) affichées en tuiles en tête de fiche joueur, pas des achievements. `hours-played` sert aussi à déterminer le rôle principal.
- `title`, `flip` (titre du bas du classement), `description`, `detail`, `joke` : textes du site.
- `display` : `P` percentile, `N` nombre, `PN` les deux, `T` texte, `TN` texte et nombre.
- `number` : pour `PN` en `ratio`, le nombre de carrière affiché (`num` ou `den`).
- `direction` : `desc` (défaut, la valeur haute porte le titre) ou `asc`.
- `format` : `pct`, `score` (base 100), `rate` (+ `rate_unit`), `int`, `big`, `signed`, `pp` (points de %).
- `min_den`, `top_by`, `unit` : voir plus haut.
- `hall_of_fame: false` : achievement jamais tiré dans le Hall of fame de l'accueil.
- `title_percentile` : seuil du titre propre à l'achievement, à la place de celui de `config/site.json`.

## Percentile et titres

Percentile = part des joueurs classés derrière lui (sens `direction`), de 0 à 100. Sur une fiche joueur, le titre est attribué à partir de `title_percentile`, le revers (`flip`) en dessous de `flip_percentile`.

## Données partielles

Pendant le crawl, l'export réel (`python -m pipeline.export_site`) ajoute à `meta.json` :

```
partial        true tant que le crawl n'est pas fini (bandeau « Incomplete data » sur le site)
pending        [ids] des stats pas encore calculées : leurs cellules sont vides
```
