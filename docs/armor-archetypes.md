# Armor 3.0 archetypes and stat structure

Domain reference for agents working on armor rules or armor presentation.
Recorded 2026-08-31 from the vault owner's description of live game behaviour,
cross-checked against the real export columns in `tests/fixtures/`.

## Stat structure of a tier-5 piece

Every Legendary and Exotic armor piece rolls with an **archetype**, which fixes
its two highest base stats. The third is random and independent.

| Role | Base value | Source |
| --- | --- | --- |
| Primary | 30 | Fixed by the archetype |
| Secondary | 25 | Fixed by the archetype |
| Tertiary | 20 | Random, independent of archetype |
| Remaining three | 0 | Gain up to 5 each from Masterwork upgrades |

That is 30 + 25 + 20 = **75 base total**, which is the `~75 base total` figure
in AGENTS.md. Masterwork points land outside the `(Base)` columns, so on the
`Total (Base)` scale the other three stats read 0 on every tier-5 piece.

**Consequence for rule design:** only three of the six base stats carry
information on tier-5 armor. The other three discriminate nothing and cannot
serve as tie-breakers on the `(Base)` scale. This is the same measured fact
behind the config note that a generic spike profile "scores everything
identically and discriminates nothing".

## The twelve archetypes

| Archetype | Primary | Secondary |
| --- | --- | --- |
| Siegebreaker | Health | Grenade |
| Bulwark | Health | Class |
| Brawler | Melee | Health |
| Skirmisher | Melee | Weapons |
| Grenadier | Grenade | Super |
| Demolitionist | Grenade | Class |
| Colossus | Super | Health |
| Paragon | Super | Melee |
| Reaver | Class | Melee |
| Specialist | Class | Weapons |
| Gunner | Weapons | Grenade |
| Powerhouse | Weapons | Super |

Exotic class items do not roll a random archetype: it is determined by the
left-column Spirit perk. This is why `rules/armor_dupes.py` treats the Spirit
signature as roll identity for class items.

## Tuning Mod Slot

Tier-5 only, and **random — independent of the archetype**. It grants +5 to one
stat at the cost of 5 from another of the player's choosing.

Tuning is *roll identity*, not socket state: it is set before anything is
socketed. Two pieces differing only in tuning are different pieces. This is why
`rules/armor_dupes.py` includes `Tuning Stat` in the exact-dupe fingerprint,
while `rules/armor_close.py` deliberately excludes it so that same-stat groups
can surface tuning variation for review.

## Export columns

DIM exports both derived values directly, so neither needs recomputing:

- `Archetype` — the archetype name, e.g. `Gunner`, `Paragon`.
- `Tertiary Stat` — the third-highest stat's name.

`Archetype` is a required column in `parse.py`'s armor schema. `Tertiary Stat`
is present in real exports but is **not** currently in the required set or in
any report projection — adding it to a payload is a schema change, not a
presentation detail.

Both are fully derivable from the six base stats (archetype = the top-2 pair,
tertiary = the third-highest), which is why `armor_dupes.py` excludes them from
the fingerprint as redundant rather than as unavailable.

## Terminology collision — read this before touching config

"Archetype" means two unrelated things in this repo, in the same way
"manifest" does:

- **Destiny's armor archetype** — the twelve primary/secondary pairs above,
  carried in the DIM export's `Archetype` column and surfaced as
  `item_archetype` in report projections.
- **vault-cleaner's scoring profile** — the `[armor.archetypes.*]` tables in
  `config.toml` (e.g. `melee_primary`), which are configurable stat weight
  vectors owned by this project and have no relationship to the twelve.

Keep the distinction explicit in names, comments, and user-facing strings.

## Owner's build preference (preference, not a rule)

The vault owner avoids Health-led pieces for PvE — the archetypes
**Siegebreaker**, **Bulwark**, **Brawler**, and **Colossus**. Health governs
health recovered from Orbs of Power, which subclass options already cover.

This is recorded as context for presentation decisions. It is **not** an
implemented rule: no pass demotes or junks a piece for being Health-led, and
making it influence ranking would need its own ticket and its own measurement.
