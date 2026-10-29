# Stats du site (V1)

Liste des stats affichées sur le site, issue de la session Claude Chat du 2026-10-28. Les titres et descriptions sont en anglais (texte du site). Chaque stat a encore besoin de sa phrase « blague », à écrire dans la config des titres.

## Conventions

- **Percentile** : rang parmi les joueurs qualifiés (15 semaines de reset ou plus), toujours calculé sur un taux (par pull, par minute, base 100) pour ne pas avantager les vétérans. **Nombre** : total sur la carrière.
- **Stats communes** : calculées par rôle, puis filtrées par TANK / DPS / HEALER sur la fiche joueur.
- **Stats de rôle** : seuls les combats joués dans ce rôle comptent.
- **Kills seulement** pour les stats de performance. Kills et wipes pour les stats fun.
- **Score de performance** (base 100) : DPS et healers seulement dans les stats communes qui l'utilisent (Metronome, Comfort Boss, Clutch Player, Glow Up, Overachiever) ; le « score » d'un tank est ses dégâts subis, pas une performance. La médiane du rôle laisse de côté les joueurs à 0 et demande au moins 3 joueurs au-dessus de 0 (`min_score_peers`), sinon le pull n'a pas de score ; même règle pour toutes les stats en base 100.
- **Tanks** : comparés à la médiane des tanks sur le même boss, sur toute l'histoire de la guilde, et pas à la médiane du pull (2 ou 3 tanks par pull, médiane trop fragile).
- **Healers** : soins effectifs (overheal exclu) pour la performance.
- **Morts scriptées** exclues des stats de mort : liste en config (ex. Fury of Frostmourne sur le Lich King, 25 morts sur 28 dans l'échantillon).
- **Revers** (*flip*) : titre donné à l'autre bout du même classement.

Légende : [P] percentile, [N] nombre, [P+N] les deux, [T] texte sur la fiche. ⚙️ liste en config ; 📋 casts par sort (déjà dans le cache) ; 🔬 niveau 3 ciblé ; 🆕 crawl supplémentaire.

## Common (37)

1. **The Gang**: Never misses a raid night. (Distinct reset weeks with at least one eligible pull. The card also shows hours in boss fights, first logged pull and expansions played.) [P+N]
2. **Identity Crisis** (ex-The Undecided): Still can't pick a main. (Distinct characters raided on, with their classes and roles on the card.) [N]
3. **Kill Collector**: Gotta kill 'em all. (Distinct bosses killed, encounter × difficulty, plus the number of guild first kills attended.) [P+N]
4. **The Immortal**: Died a thousand times, always came back for more. (Wipes attended. The card also shows heartbreaks: wipes with the boss under 5%.) [P+N]
5. **Lucky Charm** (flip: **Black Cat**): The raid wipes less when he shows up. (Guild wipe rate on a boss when he is in the raid, minus its wipe rate on that boss without him; lower is better.) [P]
6. **Fishbait**: First one on the floor. (Share of pulls where he dies first, scripted deaths excluded. The card shows deaths in the first 15 seconds.) [P+N]
7. **Floor Inspector**: Knows every tile of the raid floor. (Deaths per pull, kills and wipes. The card shows kills watched from the floor.) [P+N]
8. **The Roach**: The raid wiped. He didn't. (Wipes he survived: no death recorded for him by the end of the pull, whether by Feign Death, Vanish or a strategic run out of range.) [P+N]
9. **Last Stand**: Still standing when half the raid isn't. (Kills where fewer than half the raid was alive at the end, him included. Battle-rezzed players count as dead.) [N]
10. **Arch-Nemesis**: There's always that one spell. (Ability that killed him most often, with the count, melee hits left out: « Melee » était l'ennemi juré de 131 joueurs sur 155. Falling and lava deaths are listed on the card.) [T]
11. **Healers Love Him** (flip: **Left to Die**): The healers' favourite. (Healing received from other players, his own heals, potions and healthstones left out; base 100 vs his role on the same boss, then divided by the reference of his class and role in the expansion, the median of its players' averages (one vote per player with at least 10 pulls; no class step under 3 such players): warlocks, with Life Tap, are healed far more than other DPS.) [P]
12. **Mechanic Magnet**: If it can be stood in, he's in it. (Damage taken from "avoidable" abilities, base 100 vs his role. Avoidable means a non-melee enemy ability that hit less than half the raid in that pull.) [P]
13. **The Junky**: Can quit anytime he wants. (Potions and healthstones used per pull.) [P+N]
14. **The Unprepared**: Enchants are for tryhards. (Share of enchantable slots left without an enchant, per kill.) ⚙️ [P]
15. **Overachiever**: Punches above his item level. (Performance score compared to what his ilvl, relative to the pull, would predict.) [P]
16. **Metronome** (flip: **Rollercoaster**): You always know what you get. (How much his performance score swings from one kill to the next, standard deviation; lower is better.) [P]
17. **The Nut Crusher**: Kicks where it hurts. (Interrupts per hour, on boss pulls and nights' trash where the raid interrupted something; at least 10 such pulls, a night's trash counting as one.) [P+N]
18. **The Janitor**: Cleans up every debuff. (Dispels per pull.) [P+N]
19. **The Sweat** (flip: **Snoozer**): Never stops pressing buttons. (Active time as a share of the pull. The card shows casts per minute compared to his class.) [P]
20. **Comfort Boss**: His favourite punching bag. (Boss where his average performance score is highest.) [T]
21. **The Terrorist**: Friendly fire isn't. (His share of the raid's friendly fire, self-damage excluded: his friendly damage divided by the raid's, over the boss pulls (kills and wipes) and the nights' trash he was in. At least 10 pulls or nights with friendly fire.) [P+N]
22. **Clutch Player**: Shows up when it matters. (Average performance score on the guild's first kills of each boss, compared to his score on farm kills.) [P]
23. **Glow Up**: Look at him now. (Trend of his performance score over the weeks, as the slope of a regression. Only players with scored kills in at least 3 raid tiers under the filters.) [P]

24. **Heartbreaker**: So close. So, so close. (Wipes with the boss under 5% health, WCL `fightPercentage`, as a share of his wipes.) [P+N]
25. **Spectator**: Best seat in the house: the floor. (Kills where he died, scripted deaths excluded, as a share of his kills.) [P+N]
26. **Iron Man**: Never skips a week. (Longest run of consecutive reset weeks raided; weeks without any guild raid are skipped.) [P+N]
27. **Comeback Kid**: Said he quit. Came back anyway. (Longest absence before a comeback, in reset weeks the guild raided without him.) [P+N]
28. **Late Arrival**: Just in time for the second boss. (Share of his raid nights where he missed every pull of the night's first boss; nights with at least two bosses.) [P+N]
29. **Early Leaver**: Has work tomorrow. (Same, with the night's last boss.) [P+N]
30. **Loot Hoarder**: Somehow always the best geared. (Share of the raid he out-geared, item level, ties count half, averaged over his kills.) [P]
31. **Self-Made**: Who needs healers? (Share of the healing he received that came from himself: self-heals, potions, healthstones, leech.) [P]
32. **Guardian Angel**: The healer who always has his back. (Healer who healed him the most, and that healer's share of the healing he got from the guild's healers; only healers who healed him on at least 10 pulls. Not in the home Hall of fame.) [N]
33. **Personal Hell**: That one boss he just can't get past. (Boss he wiped on most often.) [T]
34. **Obliterated**: Not just dead. Very dead. (Biggest overkill, as a multiple of the median overkill of the guild's deaths in the expansion, with the ability, boss and date. Instant kill mechanics are detected and left out: a boss ability whose smallest overkill is above 30 times that median.) [T+N]
35. **Suicide Pact**: Together until the very end. (Raider he died with most often: both dead within 10 seconds, before a fifth of the raid is down.) [T]
36. **Pioneer**: There the first time. (Guild first kills attended, each boss and difficulty.) [P+N]

37. **Parse Lords**: Ranked against the whole world, not just Fable. (Warcraft Logs parses on Fable kills: per boss, the average of his best and median parse, then the average over bosses. DPS and healers, at least 5 bosses. The only achievement not measured against the guild.) [P]

## Tank (7)

1. **Damage Sponge**: Eats everything the boss throws. (Share of the pull's tank damage taken, base 100 vs tanks on the same boss. N = pulls tanked.) [P+N]
2. **Brick Wall** (flip: **Paper Tank**): Does not fall over. (Deaths per pull as tank. The card shows his longest kill streak without dying.) [P]
3. **Secret DPS**: Tanking is optional, pumping is not. (Damage done, base 100 vs tanks on the same boss.) [P]
4. **Add Wrangler** (flip: **Boss Hugger**): Collector of adds. (Share of damage taken from adds rather than the boss.) [P]
5. **Pacemaker**: Sets the pace of the kill. (Kill duration when he tanks, compared to the median duration for that boss.) [P]
6. **Attention Seeker**: Look at me. No, ME. (Taunts per minute, boss pulls and the trash of the nights he tanked.) 📋⚙️ [P]
7. **Blamed the Healer**: Had a cooldown up and still died. Must be the healers. (Tank deaths with a defensive cooldown active, such as Shield Wall, Survival Instincts or Icebound Fortitude; not Divine Sacrifice, a healer's raid cooldown.) 🔬⚙️ [N]

## Healer (6)

1. **Healing Machine**: Keeps the raid alive. (Effective healing, base 100 vs healers in the pull. N = pulls healed.) [P+N]
2. **Sniper** (flip: **Sniped**): Gets there first. Every time. (Overheal share, overheal / (effective healing + overheal), base 100 vs the healers of his class in the expansion; lower is better. Sniper: his heals land first. Sniped: someone else topped the target up first.) [P]
3. **Tank's Personal Nurse** (flip: **Raid Healer**): Has eyes for the tanks only. (Share of healing done on tanks. The card shows healing on himself, other healers and pets.) [P]
4. **Smite Lord**: Healer by contract, DPS at heart. (Damage done, base 100 vs healers in the pull.) [P]
5. **Favorite Patient**: His favourite patient. (Player he healed the most, shown as the share of his healing on other raiders that went to him, total in brackets; only patients healed on at least 10 pulls. Ranked from the highest share. Not in the home Hall of fame.) [N]
6. **Parse Fiend**: Stood in the fire to heal it back. For the logs. (Self-healing covering his own avoidable damage: the smaller of avoidable damage taken and self-healing done, base 100 vs healers in the pull.) [P]

## DPS (7)

1. **Big Pumper**: Makes the numbers go up. (Damage done, base 100 vs DPS in the pull. The card shows kills ranked #1 and kills in the top 3.) [P+N]
2. **Main Character Moment**: His moment of glory. (Best single-pull score, with the boss and the date.) [T+N]
3. **Tunnel Vision** (flip: **Pest Control**): Only sees the boss. (Share of damage done on the boss rather than adds.) [P]
4. **One Button Wonder** (flip: **Keyboard Pianist**): Found the best button and kept pressing it. (Share of damage from his top ability, compared to his class.) [P]
5. **Final Boss Energy**: Saves his best for the last boss. (Performance score on final raid bosses — Ragnaros, Illidan, the Lich King, Deathwing, Garrosh… — minus his score on the other bosses.) ⚙️ [P]
6. **Timekeeper** (flip: **The Tourist**): Keeps the trash moving. (Share of the raid's damage done on trash over the night, base 100 vs DPS, then divided by the mean of his class in the expansion; nights where he tanked a boss are left out. The Tourist has the lowest share and enjoys the scenery.) 🆕 [P]
7. **Engineer's Pride**: Boom goes the dynamite. (Damage from bombs, rockets and sappers. The card shows damage taken from his own sapper.) ⚙️ [N]

## Données supplémentaires à crawler

`python -m pipeline.crawl_extra`, après le crawl principal (détail dans `docs/decisions.md`) :
- **The Terrorist** : DamageDone filtré joueur → joueur, par pull, et sur le trash de chaque rapport (`trash_extra.json`).
- **Attention Seeker** 📋 : Casts filtré sur les taunts, par pull et sur le trash de chaque rapport (`trash_extra.json`, durée du trash = `totalTime`) (le tableau Casts de niveau 2 ne garde que 5 capacités par joueur). En Era et en WotLK, aussi les consommables (The Junky ; en WotLK, filtrés par ID).
- **Blamed the Healer** 🔬 : événements de buffs des CD défensifs, sur les pulls où un joueur d'une classe tank meurt.
- **Timekeeper / The Tourist** 🆕 : DamageDone sur le trash (`killType: Trash`), par rapport.
- **Parse Lords** : parses WCL des kills, par rapport.

## Reportées en V2

- **Not Even Close!** (tank sous 10 % de PV et survivant) : demande les événements de dégâts subis des tanks avec leurs PV sur chaque kill, trop cher pour la V1.
- Wipe Pumper, Legendary Flex, Necromancer (rez en combat), Bubble Wrap / Gardener (absorbs, HoTs), Threat Dealer, Crazy Pet Lady (dégâts du familier).
- Savior et True Sniper (niveau 3 sur les soins, PV max des cibles à estimer).
