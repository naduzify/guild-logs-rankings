# Stats du site (V1)

Liste des stats affichées sur le site, issue de la session Claude Chat du 2026-10-28. Les titres et descriptions sont en anglais (texte du site). La description est une phrase drôle ; ce qui est mesuré est entre parenthèses (champ `detail` de la config, info-bulle du site).

## Conventions

- **Percentile** : rang parmi les joueurs qualifiés (10 semaines de reset ou plus, `min_weeks`), toujours calculé sur un taux (par pull, par minute, base 100) pour ne pas avantager les vétérans. **Nombre** : total sur la carrière.
- **Stats communes** : calculées par rôle, puis filtrées par TANK / DPS / HEALER sur la fiche joueur.
- **Stats de rôle** : seuls les combats joués dans ce rôle comptent.
- **Kills seulement** pour les stats de performance. Kills et wipes pour les stats fun.
- **Score de performance** (base 100) : DPS et healers seulement dans les stats communes qui l'utilisent (Metronome, Comfort Boss, Clutch Player, Glow Up, Overachiever) ; le « score » d'un tank est ses dégâts subis, pas une performance. La médiane du rôle laisse de côté les joueurs à 0 et demande au moins 3 joueurs au-dessus de 0 (`min_score_peers`), sinon le pull n'a pas de score ; même règle pour toutes les stats en base 100.
- **Tanks** : comparés à la médiane des tanks sur le même boss, sur toute l'histoire de la guilde, et pas à la médiane du pull (2 ou 3 tanks par pull, médiane trop fragile).
- **Healers** : soins effectifs (overheal exclu) pour la performance.
- **Morts scriptées** exclues des stats de mort : liste en config (ex. Fury of Frostmourne sur le Lich King, 25 morts sur 28 dans l'échantillon).
- **Revers** (*flip*) : titre donné à l'autre bout du même classement.

Légende : [P] percentile, [N] nombre, [P+N] les deux, [T] texte sur la fiche. ⚙️ liste en config ; 📋 casts par sort (déjà dans le cache) ; 🔬 niveau 3 ciblé ; 🆕 crawl supplémentaire.

## Common (40)

1. **The Gang**: Raid invite? Already in the group. (Distinct reset weeks with at least one eligible pull. The card also shows hours in boss fights, first logged pull and expansions played.) [P+N]
2. **Identity Crisis** (ex-The Undecided): Asks "what should I play next tier?" every tier. (Distinct characters raided on, with their classes and roles on the card.) [N]
3. **Kill Collector**: Gotta kill 'em all. (Distinct bosses killed, encounter × difficulty, plus the number of guild first kills attended.) [P+N]
4. **The Immortal**: Wipe, run back, play the soundboard, repeat. (Wipes attended. The card also shows heartbreaks: wipes with the boss under 5%.) [P+N]
5. **Lucky Charm** (flip: **Black Cat**): Bring him to prog. Or don't. The logs have opinions. (Guild wipe rate on a boss when he is in the raid, minus its wipe rate on that boss without him; lower is better.) [P]
6. **Fishbait**: First one down, so the rest know where to lie. (Share of pulls where he dies first, scripted deaths excluded. The card shows deaths in the first 15 seconds.) [P+N]
7. **Floor Inspector**: Five stars. Would lie down again. (Deaths per pull, kills and wipes. The card shows kills watched from the floor.) [P+N]
8. **The Roach**: "Women and children first." He misheard. (Wipes he survived: no death recorded for him by the end of the pull, whether by Feign Death, Vanish or a strategic run out of range.) [P+N]
9. **Last Stand**: Still standing when half the raid isn't. Someone has to loot. (Kills where fewer than half the raid was alive at the end, him included. Battle-rezzed players count as dead.) [N]
10. **Arch-Nemesis**: Same spell, different raid night. (Ability that killed him most often, with the count, melee hits left out: « Melee » était l'ennemi juré de 131 joueurs sur 155. Falling and lava deaths are listed on the card.) [T]
11. **Healers Love Him** (flip: **Left to Die**): Healers have favourites. They just won't admit it. (Healing received from other players, his own heals, potions and healthstones left out; base 100 vs his role on the same boss, then divided by the reference of his class and role in the expansion, the median of its players' averages (one vote per player with at least 10 pulls; no class step under 3 such players): warlocks, with Life Tap, are healed far more than other DPS.) [P]
12. **Mechanic Magnet**: If it glows on the floor, he's standing in it. (Damage taken from "avoidable" abilities, base 100 vs his role. Avoidable means a non-melee enemy ability that hit less than half the raid in that pull. ; ses propres sorts qui le blessent, Stagger, Cauterize, Shadow Word: Death, Hellfire, Seal / Judgement of the Martyr et of Blood, Blood Tap, sont exclus) [P]
13. **The Junky**: The pull timer waits for his potion cooldown. (Potions and healthstones used per pull.) [P+N]
14. **The Unprepared**: Bare gear, full confidence. (Share of enchantable slots left without an enchant, per kill.) ⚙️ [P]
15. **Overachiever**: Out-parsed you in quest greens. Someone uninstalled. (Performance score compared to what his ilvl, relative to the pull, would predict.) [P]
16. **Metronome** (flip: **Rollercoaster**): Same number every week, to the decimal. (How much his performance score swings from one kill to the next, standard deviation; lower is better.) [P]
17. **The Nut Crusher**: Kicks where it hurts. Your cast bar is merely a suggestion. (Interrupts per hour, on boss pulls and nights' trash where the raid interrupted something; at least 10 such pulls, a night's trash counting as one.) [P+N]
18. **The Janitor**: Dispel first, ask what it was later. (Dispels per pull.) [P+N]
19. **The Sweat** (flip: **Snoozer**): Hasn't blinked since Molten Core. (Active time as a share of the pull. The card shows casts per minute compared to his class.) [P]
20. **Comfort Boss**: Everyone has a boss that's secretly a training dummy. (Boss where his average performance score is highest.) [T]
21. **The Terrorist**: Mind controlled. Allegedly. (His share of the raid's friendly fire, self-damage excluded: his friendly damage divided by the raid's, over the boss pulls (kills and wipes) and the nights' trash he was in. At least 10 pulls or nights with friendly fire.) Interrupteur **Single target only** : même calcul sur les seuls sorts à cible unique (variante `the-terrorist-single`, voir `single_target` de `config/compute.json`). ⚙️🆕 [P+N]
22. **Clutch Player**: Farm nights are practice. First kills are game day. (Average performance score on the guild's first kills of each boss, compared to his score on farm kills.) [P]
23. **Glow Up**: Started in greens. Ended on top of the meters. (Trend of his performance score over the weeks, as the slope of a regression. Only players with scored kills in at least 3 raid tiers under the filters.) [P]

24. **Heartbreaker**: Close enough to taste the loot. Not to roll on it. (Wipes with the boss under 5% health, WCL `fightPercentage`, as a share of his wipes.) [P+N]
25. **Spectator**: Watched the kill in third person. (Kills where he died, scripted deaths excluded, as a share of his kills.) [P+N]
26. **Iron Man**: Sign ups are overrated, assume he's coming. (Longest run of consecutive reset weeks raided; weeks without any guild raid are skipped.) [P+N]
27. **Comeback Kid**: "I'm done with this game." Several times. (Longest absence before a comeback, in reset weeks the guild raided without him.) [P+N]
28. **Late Arrival**: Traffic, dinner, patch download: a new excuse every week. (Share of his raid nights where he missed every pull of the night's first boss; nights with at least two bosses.) [P+N]
29. **Early Leaver**: "One more pull" never applied to him. (Same, with the night's last boss.) [P+N]
30. **Loot Hoarder**: Somehow always the best geared. The loot council has no comment. (Share of the raid he out-geared, item level, ties count half, averaged over his kills.) [P]
31. **Self-Made**: Who needs healers? Leech, potions and pure spite. (Share of the healing he received that came from himself: self-heals, potions, healthstones, leech.) [P]
32. **Guardian Angel**: Some heals are personal. (Healer who healed him the most, and that healer's share of the healing he got from the guild's healers; only healers who healed him on at least 10 pulls. Not in the home Hall of fame.) [N]
33. **Personal Hell**: Saw that boss more often than his family. (Boss he wiped on most often.) [T]
34. **Obliterated**: Not just dead. Closed-casket dead. (Biggest overkill, as a multiple of the median overkill of the guild's deaths in the expansion, with the ability, boss and date. Instant kill mechanics are detected and left out: a boss ability whose smallest overkill is above 30 times that median.) [T+N]
35. **Suicide Pact**: Ride or die. Mostly die. (Raider he died with most often: both dead within 10 seconds, before a fifth of the raid is down.) [T]
36. **Pioneer**: In the first-kill screenshot. And in every wipe before it. (Guild first kills attended, each boss and difficulty.) [P+N]

37. **Parse Lord**: Purple is a personality. (Warcraft Logs parses on Fable kills: per boss, the average of his best and his median parse (both against the rankings at the time of each kill), then the average over his kills (each boss weighs its number of kills, whichever character played them). Every role, tanks included, at least 50 kills. The only achievement not measured against the guild.) [P]
38. **Martyr**: Takes one for the team. Several, actually. (His share of the raid's friendly fire received: damage dealt to him by other raid members, divided by the raid's friendly fire, over the boss pulls and the nights' trash he was in. Damage on oneself left out. At least 10 pulls or nights with friendly fire.) [P+N]
39. **Headhunter**: Collects scalps. Doesn't check the nameplate colour. (Killing blows landed on other raid members with his own abilities, on boss pulls and the nights' trash. Career total; the number opens the list of his victims.) ⚙️🆕 [N]
40. **Collateral Damage**: Survived the boss. Didn't survive the raid. (Deaths from a killing blow landed by another raid member with his own abilities, on boss pulls and the nights' trash. Career total; the number opens the list of who killed him.) ⚙️🆕 [N]

## Tank (7)

1. **Damage Sponge**: The boss's favourite chew toy. (Share of the pull's tank damage taken, base 100 vs tanks on the same boss. N = pulls tanked.) [P+N]
2. **Brick Wall** (flip: **Paper Tank**): The healers fall over before he does. (Deaths per pull as tank. The card shows his longest kill streak without dying.) [P]
3. **Secret DPS**: Threat is just a DPS meter if you squint. (Damage done, base 100 vs tanks on the same boss.) [P]
4. **Add Wrangler** (flip: **Boss Hugger**): If it spawns, it's his. (Share of damage taken from adds rather than the boss.) [P]
5. **Pacemaker**: Pulls when he's ready. He's always ready. (Kill duration when he tanks, compared to the median duration for that boss.) [P]
6. **Attention Seeker**: Look at me. No, ME. (Taunts per minute, boss pulls and the trash of the nights he tanked.) 📋⚙️ [P]
7. **Blamed the Healer**: His cooldowns were perfect. His healers, apparently, were not. (Share of his deaths as a tank with a defensive cooldown active, such as Shield Wall, Survival Instincts or Icebound Fortitude; not Divine Sacrifice, a healer's raid cooldown, nor Dancing Rune Weapon, mostly offensive. Total deaths as a tank shown alongside; at least 30.) 🔬⚙️ [P+N]

## Healer (6)

1. **Healing Machine**: Mana is temporary. The meter is forever. (Effective healing, base 100 vs healers in the pull. N = pulls healed.) [P+N]
2. **Sniper** (flip: **Sniped**): Fastest heals in the raid. Yours land on a full health bar. (Overheal share, overheal / (effective healing + overheal), base 100 vs the healers of his class in the expansion; lower is better. Sniper: his heals land first. Sniped: someone else topped the target up first.) [P]
3. **Tank's Personal Nurse** (flip: **Raid Healer**): Laser-focused on the tank, or whack-a-mole on the raid frames. (Share of healing done on tanks. The card shows healing on himself, other healers and pets.) [P]
4. **Smite Lord**: Who needs heals when the boss is dead? (Damage done, base 100 vs healers in the pull.) [P]
5. **Favorite Patient**: The healer's favourite. Rumour says gold changed hands. (Player he healed the most, shown as the share of his healing on other raiders that went to him, total in brackets; only patients healed on at least 10 pulls. Ranked from the highest share. Not in the home Hall of fame.) [N]
6. **Parse Fiend**: Stood in the fire to heal it back. For the logs. (Self-healing covering his own avoidable damage: the smaller of avoidable damage taken and self-healing done, base 100 vs healers in the pull.) [P]

## DPS (7)

1. **Big Pumper**: Carries the raid on his back. The meters agree. (Damage done, base 100 vs DPS in the pull. The card shows kills ranked #1 and kills in the top 3.) [P+N]
2. **Main Character Moment**: Screenshotted, framed, posted in Discord. (Best single-pull score, with the boss and the date.) [T+N]
3. **Tunnel Vision** (flip: **Pest Control**): Adds don't count towards the parse. (Share of damage done on the boss rather than adds.) [P]
4. **One Button Wonder** (flip: **Keyboard Pianist**): Found the best button. Pressed it until the keycap wore off. (Share of damage from his top ability, compared to his class.) [P]
5. **Final Boss Energy**: Last boss of the night: finds a sixth gear to get home sooner. (Performance score on final raid bosses — Ragnaros, Illidan, the Lich King, Deathwing, Garrosh… — minus his score on the other bosses.) ⚙️ [P]
6. **Timekeeper** (flip: **The Tourist**): The trash is dead before the tank finds it. (Share of the raid's damage done on trash over the night, base 100 vs DPS, then divided by the mean of his class in the expansion; nights where he tanked a boss are left out. The Tourist has the lowest share and enjoys the scenery.) 🆕 [P]
7. **Engineer's Pride**: Sapper first, apologise later. (Damage from bombs, rockets and sappers. The card shows damage taken from his own sapper.) ⚙️ [N]

## Données supplémentaires à crawler

`python -m pipeline.crawl_extra`, après le crawl principal (détail dans `docs/decisions.md`) :
- **The Terrorist** : DamageDone filtré joueur → joueur, par pull, et sur le trash de chaque rapport (`trash_extra.json`).
- **Attention Seeker** 📋 : Casts filtré sur les taunts, par pull et sur le trash de chaque rapport (`trash_extra.json`, durée du trash = `totalTime`) (le tableau Casts de niveau 2 ne garde que 5 capacités par joueur). En Era et en WotLK, aussi les consommables (The Junky ; en WotLK, filtrés par ID).
- **Blamed the Healer** 🔬 : événements de buffs des CD défensifs, sur les pulls où un joueur d'une classe tank meurt.
- **Timekeeper / The Tourist** 🆕 : DamageDone sur le trash (`killType: Trash`), par rapport.
- **Headhunter / Collateral Damage** 🆕 : tableau Deaths sur le trash de chaque rapport (`trash_deaths.json`, `killType: Trash`) ; sur les pulls de boss, le tableau Deaths du crawl principal suffit (source du coup fatal dans ses événements).
- **The Terrorist, cible unique** 🔬 : événements de friendly fire des sorts « premier coup seulement » (`ff_events.json`, toutes les pages), seulement sur les rapports où l'un d'eux a touché un joueur.
- **Parse Lord** : parses WCL des kills, par rapport, deux fois : `rankings_historical.json` (`timeframe: Historical`, classement à la date du combat, pour le meilleur et le parse médian) et `rankings.json` (classement d'aujourd'hui, en secours pour un kill sans parse historique).

## Reportées en V2

- **Not Even Close!** (tank sous 10 % de PV et survivant) : demande les événements de dégâts subis des tanks avec leurs PV sur chaque kill, trop cher pour la V1.
- Wipe Pumper, Legendary Flex, Necromancer (rez en combat), Bubble Wrap / Gardener (absorbs, HoTs), Threat Dealer, Crazy Pet Lady (dégâts du familier).
- Savior et True Sniper (niveau 3 sur les soins, PV max des cibles à estimer).
