# Stats du site (V1)

Liste des stats affichées sur le site, issue de la session Claude Chat du 2026-10-28. Les titres et descriptions sont en anglais (texte du site). Chaque stat a encore besoin de sa phrase « blague », à écrire dans la config des titres.

## Conventions

- **Percentile** : rang parmi les joueurs qualifiés (15 semaines de reset ou plus), toujours calculé sur un taux (par pull, par minute, base 100) pour ne pas avantager les vétérans. **Nombre** : total sur la carrière.
- **Stats communes** : calculées par rôle, puis filtrées par TANK / DPS / HEALER sur la fiche joueur.
- **Stats de rôle** : seuls les combats joués dans ce rôle comptent.
- **Kills seulement** pour les stats de performance. Kills et wipes pour les stats fun.
- **Tanks** : comparés à la médiane des tanks sur le même boss, sur toute l'histoire de la guilde, et pas à la médiane du pull (2 ou 3 tanks par pull, médiane trop fragile).
- **Healers** : soins effectifs (overheal exclu) pour la performance.
- **Morts scriptées** exclues des stats de mort : liste en config (ex. Fury of Frostmourne sur le Lich King, 25 morts sur 28 dans l'échantillon).
- **Revers** (*flip*) : titre donné à l'autre bout du même classement.

Légende : [P] percentile, [N] nombre, [P+N] les deux, [T] texte sur la fiche. ⚙️ liste en config ; 📋 casts par sort (déjà dans le cache) ; 🔬 niveau 3 ciblé ; 🆕 crawl supplémentaire.

## Common (25)

1. **The Gang**: Never misses a raid night. (Distinct reset weeks with at least one eligible pull. The card also shows hours in boss fights, first logged pull and expansions played.) [P+N]
2. **The Undecided**: Still can't pick a main. (Distinct characters raided on, with their classes and roles on the card.) [N]
3. **Kill Collector**: Gotta kill 'em all. (Distinct bosses killed, encounter × difficulty, plus the number of guild first kills attended.) [P+N]
4. **The Immortal**: Died a thousand times, always came back for more. (Wipes attended. The card also shows heartbreaks: wipes with the boss under 5%.) [P+N]
5. **Night Owl**: Past bedtime, still pulling. (Share of pulls started after midnight, Sydney time.) [P]
6. **Lucky Charm** (flip: **Black Cat**): The raid wipes less when he shows up. (Guild wipe rate on a boss when he is in the raid, minus its wipe rate on that boss without him; lower is better.) [P]
7. **Fishbait**: First one on the floor. (Share of pulls where he dies first, scripted deaths excluded. The card shows deaths in the first 15 seconds.) [P+N]
8. **Floor Inspector**: Knows every tile of the raid floor. (Deaths per pull, kills and wipes. The card shows kills watched from the floor.) [P+N]
9. **The Roach**: The raid wiped. He didn't. (Wipes he survived: no death recorded for him by the end of the pull, whether by Feign Death, Vanish or a strategic run out of range.) [P+N]
10. **Last Stand**: Still standing when half the raid isn't. (Kills where fewer than half the raid was alive at the end, him included. Battle-rezzed players count as dead.) [N]
11. **Arch-Nemesis**: There's always that one spell. (Ability that killed him most often, with the count. Falling and lava deaths are listed on the card.) [T]
12. **Healers Love Him** (flip: **Left to Die**): The healers' favourite. (Healing received, base 100 vs his role in the pull.) [P]
13. **Mechanic Magnet**: If it can be stood in, he's in it. (Damage taken from "avoidable" abilities, base 100 vs his role. Avoidable means a non-melee enemy ability that hit less than half the raid in that pull.) [P]
14. **The Junky**: Can quit anytime he wants. (Potions and healthstones used per pull.) [P+N]
15. **The Unprepared**: Enchants are for tryhards. (Share of enchantable slots left without an enchant, per kill.) ⚙️ [P]
16. **Overachiever**: Punches above his item level. (Performance score compared to what his ilvl, relative to the pull, would predict.) [P]
17. **Metronome** (flip: **Rollercoaster**): You always know what you get. (How much his performance score swings from one kill to the next, standard deviation; lower is better.) [P]
18. **The Nut Crusher**: Kicks where it hurts. (Interrupts per pull, counting only pulls where something could be interrupted.) [P+N]
19. **The Janitor**: Cleans up every debuff. (Dispels per pull.) [P+N]
20. **The Sweat** (flip: **Snoozer**): Never stops pressing buttons. (Active time as a share of the pull. The card shows casts per minute compared to his class.) [P]
21. **Comfort Boss**: His favourite punching bag. (Boss where his average performance score is highest.) [T]
22. **The Terrorist**: Friendly fire isn't. (Damage he dealt to other raid members, self-damage excluded, as a share of the raid's damage taken in the pull. Kills and wipes.) [P+N]
23. **Clutch Player**: Shows up when it matters. (Average performance score on the guild's first kills of each boss, compared to his score on farm kills.) [P]
24. **Glow Up**: Look at him now. (Trend of his performance score over the weeks, as the slope of a regression.) [P]

25. **Parse Lord**: Ranked against the whole world, not just Fable. (Warcraft Logs parses on Fable kills: per boss, the average of his best and median parse, then the average over bosses. DPS and healers, at least 5 bosses. The only achievement not measured against the guild.) [P]

## Tank (7)

1. **Damage Sponge**: Eats everything the boss throws. (Share of the pull's tank damage taken, base 100 vs tanks on the same boss. N = pulls tanked.) [P+N]
2. **Brick Wall** (flip: **Paper Tank**): Does not fall over. (Deaths per pull as tank. The card shows his longest kill streak without dying.) [P]
3. **Secret DPS**: Tanking is optional, pumping is not. (Damage done, base 100 vs tanks on the same boss.) [P]
4. **Add Wrangler** (flip: **Boss Hugger**): Collector of adds. (Share of damage taken from adds rather than the boss.) [P]
5. **Pacemaker**: Sets the pace of the kill. (Kill duration when he tanks, compared to the median duration for that boss.) [P]
6. **Attention Seeker**: Look at me. No, ME. (Taunts per minute.) 📋⚙️ [P]
7. **Blamed the Healer**: Had a cooldown up and still died. Must be the healers. (Tank deaths with a defensive cooldown active, such as Shield Wall, Survival Instincts or Icebound Fortitude.) 🔬⚙️ [N]

## Healer (6)

1. **Healing Machine**: Keeps the raid alive. (Effective healing, base 100 vs healers in the pull. N = pulls healed.) [P+N]
2. **Sniper**: Only heals full-health targets. (Overheal share: overheal / (effective healing + overheal).) [P]
3. **Tank's Personal Nurse** (flip: **Raid Healer**): Has eyes for the tanks only. (Share of healing done on tanks. The card shows healing on himself, other healers and pets.) [P]
4. **Smite Lord**: Healer by contract, DPS at heart. (Damage done, base 100 vs healers in the pull.) [P]
5. **Favorite Patient**: His favourite patient. (Player he healed the most, shown as the share of his healing on other raiders that went to him, total in brackets; only patients healed on at least 10 pulls. Ranked from the highest share. Not in the home Hall of fame.) [N]
6. **Parse Fiend**: Stood in the fire to heal it back. For the logs. (Self-healing covering his own avoidable damage: the smaller of avoidable damage taken and self-healing done, base 100 vs healers in the pull.) [P]

## DPS (7)

1. **Big Pumper**: Makes the numbers go up. (Damage done, base 100 vs DPS in the pull. The card shows kills ranked #1 and kills in the top 3.) [P+N]
2. **Main Character Moment**: His moment of glory. (Best single-pull score, with the boss and the date.) [T+N]
3. **Tunnel Vision** (flip: **Pest Control**): Only sees the boss. (Share of damage done on the boss rather than adds.) [P]
4. **One Button Wonder** (flip: **Keyboard Pianist**): Found the best button and kept pressing it. (Share of damage from his top ability, compared to his class.) [P]
5. **Final Boss Energy**: Saves his best for the last boss. (Performance score on final raid bosses: Ragnaros, Illidan, the Lich King, Deathwing, Garrosh…) ⚙️ [P]
6. **Timekeeper** (flip: **The Tourist**): Keeps the trash moving. (Share of the raid's damage done on trash over the night, base 100 vs DPS. The Tourist has the lowest share and enjoys the scenery.) 🆕 [P]
7. **Engineer's Pride**: Boom goes the dynamite. (Damage from bombs, rockets and sappers. The card shows damage taken from his own sapper.) ⚙️ [N]

## Données supplémentaires à crawler

`python -m pipeline.crawl_extra`, après le crawl principal (détail dans `docs/decisions.md`) :
- **The Terrorist** : DamageDone filtré joueur → joueur, par pull.
- **Attention Seeker** 📋 : Casts filtré sur les taunts, par pull (le tableau Casts de niveau 2 ne garde que 5 capacités par joueur). En Era, aussi les consommables (The Junky).
- **Blamed the Healer** 🔬 : événements de buffs des CD défensifs, sur les pulls où un joueur d'une classe tank meurt.
- **Timekeeper / The Tourist** 🆕 : DamageDone sur le trash (`killType: Trash`), par rapport.
- **Parse Lord** : parses WCL des kills, par rapport.

## Reportées en V2

- **Not Even Close!** (tank sous 10 % de PV et survivant) : demande les événements de dégâts subis des tanks avec leurs PV sur chaque kill, trop cher pour la V1.
- Wipe Pumper, Legendary Flex, Necromancer (rez en combat), Bubble Wrap / Gardener (absorbs, HoTs), Threat Dealer, Crazy Pet Lady (dégâts du familier).
- Savior et True Sniper (niveau 3 sur les soins, PV max des cibles à estimer).
