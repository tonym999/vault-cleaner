# Issue #142 baseline measurement evidence

Verbatim command transcripts and raw outputs backing the measurements in
[docs/aggressive-clearout-measurement.md](../../docs/aggressive-clearout-measurement.md).

All commands were run on Windows within Git Bash (`bash 5.2.26`) on Python 3.13.14
with pandas 3.0.5, using `export PYTHONUTF8=1` to enforce UTF-8 streams and avoid
codepage encoding errors on Unicode fixture symbols (such as the emoji in
`tests/fixtures/weapons_hostile.csv`).

Every file capture below was produced using a single combined stdout+stderr
redirection (`> "$OUT/file.txt" 2>&1`) into a disposable `mktemp -d` scratch
directory outside the repository working tree.

---

## 1. Environment and version check

```bash
set -euo pipefail
OUT="$(mktemp -d)"
.venv/bin/python -c "import sys, pandas; print(sys.version); print(pandas.__version__)" > "$OUT/versions.txt" 2>&1
cat "$OUT/versions.txt"
```

Output:

```text
3.13.14 (tags/v3.13.14:fd17997, Jun 10 2026, 13:03:48) [MSC v.1944 64 bit (AMD64)]
3.0.5
```

---

## 2. Export headers by kind

```bash
set -euo pipefail
OUT="$(mktemp -d)"
{ head -1 tests/fixtures/weapons.csv | tr ',' '\n' | nl
  head -1 tests/fixtures/armor.csv   | tr ',' '\n' | nl
  head -1 tests/fixtures/ghosts.csv  | tr ',' '\n' | nl
} > "$OUT/headers.txt" 2>&1
cat "$OUT/headers.txt"
```

Output:

```text
     1	Name
     2	Hash
     3	Id
     4	Tag
     5	Rarity
     6	Tier
     7	Type
     8	Source
     9	Category
    10	Element
    11	Ammo
    12	Power
    13	Archetype
    14	Masterwork Type
    15	Masterwork Tier
    16	Owner
    17	Locked
    18	Equipped
    19	Holofoil
    20	Year
    21	Season
    22	Event
    23	Recoil
    24	AA
    25	Impact
    26	Range
    27	Zoom
    28	Blast Radius
    29	Velocity
    30	Persistence
    31	Stability
    32	ROF
    33	Reload
    34	Mag
    35	Handling
    36	Charge Time
    37	Draw Time
    38	Accuracy
    39	Charge Rate
    40	Guard Resistance
    41	Guard Endurance
    42	Swing Speed
    43	Shield Duration
    44	Airborne Effectiveness
    45	Ammo Generation
    46	Heat Generated
    47	Cooling Efficiency
    48	Crafted
    49	Crafted Level
    50	Kill Tracker
    51	Foundry
    52	Loadouts
    53	Notes
    54	Perks 0
    55	Perks 1
    56	Perks 2
    57	Perks 3
    58	Perks 4
    59	Perks 5
    60	Perks 6
    61	Perks 7
    62	Perks 8
    63	Perks 9
    64	Perks 10
    65	Perks 11
    66	Perks 12
    67	Perks 13
    68	Perks 14
    69	Perks 15
    70	Perks 16
    71	Perks 17
    72	Perks 18
    73	Perks 19
    74	Perks 20
     1	Name
     2	Hash
     3	Id
     4	Tag
     5	Rarity
     6	Tier
     7	Type
     8	Source
     9	Equippable
    10	Power
    11	Energy Capacity
    12	Archetype
    13	Tertiary Stat
    14	Tuning Stat
    15	Masterwork Tier
    16	Owner
    17	Locked
    18	Equipped
    19	Holofoil
    20	Year
    21	Season
    22	Event
    23	Weapons
    24	Health
    25	Class
    26	Grenade
    27	Super
    28	Melee
    29	Total
    30	Weapons (Base)
    31	Health (Base)
    32	Class (Base)
    33	Grenade (Base)
    34	Super (Base)
    35	Melee (Base)
    36	Total (Base)
    37	Seasonal Mod
    38	Loadouts
    39	Notes
    40	Perks 0
    41	Perks 1
    42	Perks 2
    43	Perks 3
    44	Perks 4
    45	Perks 5
    46	Perks 6
    47	Perks 7
    48	Perks 8
     1	Name
     2	Hash
     3	Id
     4	Tag
     5	Rarity
     6	Tier
     7	Source
     8	Energy Capacity
     9	Masterwork Tier
    10	Owner
    11	Locked
    12	Equipped
    13	Holofoil
    14	Year
    15	Season
    16	Event
    17	Loadouts
    18	Notes
    19	Perks 0
    20	Perks 1
    21	Perks 2
    22	Perks 3
    23	Perks 4
    24	Perks 5
```

---

## 3. Fixture row counts and critical cell populations

```bash
set -euo pipefail
OUT="$(mktemp -d)"
.venv/bin/python - <<'PY' > "$OUT/fixtures.txt" 2>&1
import pandas as pd, glob, os
for path in sorted(glob.glob("tests/fixtures/*.csv")):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = set(df.columns)
    nz = lambda c: int(df[c].str.strip().ne("").sum()) if c in cols else None
    print(os.path.basename(path), "rows=", len(df),
          "| Loadouts nonempty=", nz("Loadouts"),
          "| Equipped=", sorted(set(df["Equipped"])) if "Equipped" in cols else None,
          "| Owner=", sorted(set(df["Owner"])) if "Owner" in cols else None,
          "| Tag=", sorted(set(df["Tag"])) if "Tag" in cols else None)
PY
cat "$OUT/fixtures.txt"
```

Output:

```text
armor.csv rows= 15 | Loadouts nonempty= 0 | Equipped= ['false'] | Owner= ['Vault'] | Tag= ['', 'keep']
armor_classes.csv rows= 4 | Loadouts nonempty= 0 | Equipped= ['false'] | Owner= ['Hunter(550)', 'Titan(550)', 'Vault'] | Tag= ['']
armor_close.csv rows= 34 | Loadouts nonempty= 0 | Equipped= ['false', 'true'] | Owner= ['Vault'] | Tag= ['']
armor_dupes.csv rows= 32 | Loadouts nonempty= 2 | Equipped= ['false', 'true'] | Owner= ['Vault'] | Tag= ['', 'keep']
armor_duplicates_ui.csv rows= 3 | Loadouts nonempty= 0 | Equipped= ['false', 'true'] | Owner= ['Hunter(550)', 'Vault'] | Tag= ['', 'keep']
armor_same_stat_four_ui.csv rows= 4 | Loadouts nonempty= 1 | Equipped= ['false'] | Owner= ['Titan(415)', 'Vault'] | Tag= ['']
armor_same_stat_ui.csv rows= 2 | Loadouts nonempty= 0 | Equipped= ['false'] | Owner= ['Vault'] | Tag= ['']
ghosts.csv rows= 2 | Loadouts nonempty= 0 | Equipped= ['false', 'true'] | Owner= ['Hunter(506)', 'Vault'] | Tag= ['', 'favorite']
ghosts_cleanup.csv rows= 7 | Loadouts nonempty= 1 | Equipped= ['false', 'true'] | Owner= ['Titan(550)', 'Vault'] | Tag= ['', 'favorite', 'keep']
weapons.csv rows= 3 | Loadouts nonempty= 0 | Equipped= ['false', 'true'] | Owner= ['Titan', 'Vault'] | Tag= ['', 'favorite', 'keep']
weapons_dupes.csv rows= 18 | Loadouts nonempty= 0 | Equipped= ['false', 'true'] | Owner= ['Vault'] | Tag= ['', 'keep']
weapons_hostile.csv rows= 10 | Loadouts nonempty= 0 | Equipped= ['false'] | Owner= ['Vault'] | Tag= ['']
weapons_slammer_like.csv rows= 5 | Loadouts nonempty= 0 | Equipped= ['false'] | Owner= ['Vault'] | Tag= ['']
```

---

## 4. Semantic `Owner` reads in codebase

```bash
set -euo pipefail
OUT="$(mktemp -d)"
grep -rn "Owner" src/vault_cleaner --include=*.py > "$OUT/owner.txt" 2>&1
wc -l < "$OUT/owner.txt" > "$OUT/owner-count.txt" 2>&1
cat "$OUT/owner-count.txt"
cat "$OUT/owner.txt"
```

Output:

```text
13
src/vault_cleaner/cli.py:151:        print(f"  would tag {args.tag!r}: {r['Name']} (id {r['Id']}, location {r.get('Owner', '?')})")
src/vault_cleaner/duplicate_reference.py:184:    location = safe_fragment(row.get("Owner", ""))
src/vault_cleaner/duplicate_reference.py:212:    location = safe_fragment(row.get("Owner", ""))
src/vault_cleaner/rules/armor.py:163:                    location=row.get("Owner", ""),
src/vault_cleaner/rules/armor.py:214:                location=row.get("Owner", ""), guardian_class=row["Equippable"],
src/vault_cleaner/rules/armor.py:223:                location=row.get("Owner", ""), guardian_class=row["Equippable"],
src/vault_cleaner/rules/armor_close.py:246:                    location=row.get("Owner", ""),
src/vault_cleaner/rules/armor_close.py:306:                    location=str(row.get("Owner", "")),
src/vault_cleaner/rules/armor_dupes.py:227:        location=str(row.get("Owner", "")),
src/vault_cleaner/rules/armor_dupes.py:410:                    location=row.get("Owner", ""),
src/vault_cleaner/rules/dupes.py:268:                    location=row.get("Owner", ""), guardian_class="",
src/vault_cleaner/rules/ghosts.py:50:                location=row.get("Owner", ""), guardian_class="",
src/vault_cleaner/rules/weapons.py:95:                location=row.get("Owner", ""), guardian_class="",
```

---

## 5. Baseline `report` runs on fake fixture data

### Run A — mixed inputs (`weapons.csv`, `armor.csv`, `ghosts.csv`)

```bash
set -euo pipefail
export PYTHONUTF8=1
OUT="$(mktemp -d)"
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons.csv --armor tests/fixtures/armor.csv --ghosts tests/fixtures/ghosts.csv --no-wishlists > "$OUT/runA.txt" 2>&1
cat "$OUT/runA.txt"
```

Output:

```text
would junk 1 item(s) and flag 5 for review

JUNK ghost-unprotected-surplus (ghosts) — 1 item(s)
  Fake Shell (id 2000000000000000001, class ghosts; location Vault)

REVIEW armor-similar to (armor) — 3 item(s)
  Guard Plate A (id 4051, class Titan; location Vault) — review: armor-similar to; compare [id 4052; location Vault]; max stat delta 1, total 2; partner deterministic id tie-break; Candidate Tuning Mod Slot: none/unknown; Partner Tuning Mod Slot: none/unknown
  Guard Plate B (id 4052, class Titan; location Vault) — review: armor-similar to; compare [id 4051; location Vault]; max stat delta 1, total 2; partner deterministic id tie-break; Candidate Tuning Mod Slot: none/unknown; Partner Tuning Mod Slot: none/unknown
  Guard Plate C (id 4053, class Titan; location Vault) — review: armor-similar to; compare [id 4051; location Vault]; max stat delta 1, total 2; partner deterministic id tie-break; Candidate Tuning Mod Slot: none/unknown; Partner Tuning Mod Slot: none/unknown

REVIEW armor-last-archetype (armor) — 1 item(s)
  Bad Plate (id 4005, class Titan; location Vault)

REVIEW armor-score (armor) — 1 item(s)
  Bad Locked Plate (id 4006, class Titan; location Vault)

dry run — pass --write to write the combined import CSV
```

### Run B — weapon duplicates fixture (`weapons_dupes.csv`)

```bash
set -euo pipefail
export PYTHONUTF8=1
OUT="$(mktemp -d)"
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_dupes.csv --no-wishlists > "$OUT/runB.txt" 2>&1
cat "$OUT/runB.txt"
```

Output:

```text
skipping armor: data\in\destiny-armor.csv not found; expected destiny-armor.csv or a browser-numbered copy such as destiny-armor (1).csv
skipping ghosts: data\in\destiny-ghost.csv not found; expected destiny-ghost.csv or a browser-numbered copy such as destiny-ghost (1).csv
would junk 4 item(s) and flag 3 for review

JUNK dupe-lower (weapons) — 3 item(s)
  Dupe Rifle (id 3002, class weapons; location Vault) — junk: dupe-lower; keep [id 3001; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  Crafted Pulse (id 3022, class weapons; location Vault) — junk: dupe-lower; keep [id 3020; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  Tiered Sidearm (id 3032, class weapons; location Vault) — junk: dupe-lower; keep [id 3031; location Vault; Tier 5; MW0; roll Mag B / Trait A]; winner higher Tier

JUNK dupe-tie (weapons) — 1 item(s)
  Twin SMG (id 3042, class weapons; location Vault) — junk: dupe-tie; keep [id 3041; location Vault; Tier 5; MW0; roll Mag B / Trait A]; winner deterministic id tie-break

REVIEW dupe-lower (weapons) — 2 item(s)
  Dupe Rifle (id 3003, class weapons; location Vault) — review: dupe-lower (locked); keep [id 3001; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  Fake Exotic HC (id 3012, class weapons; location Vault) — review: dupe-lower (exotic); keep [id 3011; location Vault; Tier 5; MW8; roll Mag Exotic B / Trait Exotic]; winner higher Masterwork Tier

REVIEW dupe-tie (weapons) — 1 item(s)
  Tied Exotic GL (id 3052, class weapons; location Vault) — review: dupe-tie (exotic); keep [id 3051; location Vault; Tier 5; MW0; roll Mag Exotic B / Trait Exotic]; winner deterministic id tie-break

dry run — pass --write to write the combined import CSV
```

### Run C — hostile input strings fixture (`weapons_hostile.csv`)

```bash
set -euo pipefail
export PYTHONUTF8=1
OUT="$(mktemp -d)"
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_hostile.csv --no-wishlists > "$OUT/runC.txt" 2>&1
cat "$OUT/runC.txt"
```

Output:

```text
skipping armor: data\in\destiny-armor.csv not found; expected destiny-armor.csv or a browser-numbered copy such as destiny-armor (1).csv
skipping ghosts: data\in\destiny-ghost.csv not found; expected destiny-ghost.csv or a browser-numbered copy such as destiny-ghost (1).csv
would junk 5 item(s) and flag 0 for review

JUNK dupe-lower (weapons) — 5 item(s)
  </script><img src=x onerror=alert(1)> (id 18446744073709551615, class weapons; location Vault) — junk: dupe-lower; keep [id 7001; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  =cmd|' /C calc'!A0 (id 7004, class weapons; location Vault) — junk: dupe-lower; keep [id 7003; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  Ünïcödé 💀 gnorts (id 7006, class weapons; location Vault) — junk: dupe-lower; keep [id 7005; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  __proto__ (id 7008, class weapons; location Vault) — junk: dupe-lower; keep [id 7007; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA… (id 7010, class weapons; location Vault) — junk: dupe-lower; keep [id 7009; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier

dry run — pass --write to write the combined import CSV
```

### Run D — slammer-like exotic duplicate fixture (`weapons_slammer_like.csv`)

```bash
set -euo pipefail
export PYTHONUTF8=1
OUT="$(mktemp -d)"
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_slammer_like.csv --no-wishlists > "$OUT/runD.txt" 2>&1
cat "$OUT/runD.txt"
```

Output:

```text
skipping armor: data\in\destiny-armor.csv not found; expected destiny-armor.csv or a browser-numbered copy such as destiny-armor (1).csv
skipping ghosts: data\in\destiny-ghost.csv not found; expected destiny-ghost.csv or a browser-numbered copy such as destiny-ghost (1).csv
would junk 1 item(s) and flag 0 for review

JUNK dupe-lower (weapons) — 1 item(s)
  Fake Slammer (id 6104, class weapons; location Vault) — junk: dupe-lower; keep [id 6101; location Vault; Tier 5; MW10; roll Collective Demolition / Bait and Switch]; winner higher Masterwork Tier

dry run — pass --write to write the combined import CSV
```

---

## 6. Deterministic capture byte-stability proof

```bash
set -euo pipefail
export PYTHONUTF8=1
OUT="$(mktemp -d)"
for i in 1 2 3 4 5; do
  .venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_dupes.csv --no-wishlists > "$OUT/runB.$i.txt" 2>&1
done
for i in 2 3 4 5; do cmp "$OUT/runB.1.txt" "$OUT/runB.$i.txt"; done
md5sum "$OUT"/runB.*.txt | awk '{print $1}' | sort -u | wc -l > "$OUT/digests.txt" 2>&1
cat "$OUT/digests.txt"
```

Output:

```text
1
```

---

## 7. Wishlists command output and local cache state

```bash
set -euo pipefail
OUT="$(mktemp -d)"
.venv/bin/vault-cleaner wishlists > "$OUT/wishlists.txt" 2>&1
cat "$OUT/wishlists.txt"
```

Output:

```text
choosy_voltron: 255373 keep rolls across 1234 items, 53 trash entries across 53 items
aegis: 5022 keep rolls across 968 items, 0 trash entries across 0 items
aegis_trash: 0 keep rolls across 0 items, 286 trash entries across 286 items
total: 260395 keep rolls, 339 trash entries
```

Cache mtimes in `wishlists/` directory:
- `aegis.txt`: `354,210 bytes`, mtime `2026-09-03 21:27`
- `aegis_trash.txt`: `30,195 bytes`, mtime `2026-09-03 21:27`
- `choosy_voltron.txt`: `27,014,559 bytes`, mtime `2026-09-03 21:27`

Because the cached files were 3 days old (well under `config.toml`'s 7-day `max_age_days`),
`vault-cleaner wishlists` served all three files from cache without re-downloading.

---

## 8. Aggregate-only real-export analysis (authorized session data)

An actual DIM weapon export was supplied and authorized for aggregate measurement
in this session (`2026-09-06`). In strict accordance with the repository privacy
rules, **no item names, hashes, instance IDs, or individual rows** are stored,
quoted, or committed.

### Inventory population and location breakdown

- **Total weapon rows:** 664
- **Unique weapon hashes:** 440
- **Unique instance IDs:** 664 (all distinct 64-bit identifiers)
- **Location breakdown (`Owner`):**
  - `Vault`: 555
  - `Titan(451)`: 43
  - `Warlock(550)`: 35
  - `Hunter(550)`: 31
  - Total on characters: 109
- **Equipped state (`Equipped`):**
  - `false`: 655
  - `true`: 9 (exactly 3 weapons equipped per character × 3 characters)
- **Unequipped character weapons (`C`):** `109 - 9 = 100`

### Protection state breakdown (N=664)

- **Hard-protected under current rules:** 56
  - Tag in `{'favorite', 'keep', 'archive'}`: 8 (7 keep, 1 favorite)
  - `Equipped == 'true'`: 9
  - Crafted level >= 10: 41 (out of 43 total crafted weapons; 2 are level < 10)
- **Hard-protected with loadouts rail (settled decision):** 169
  - Non-empty `Loadouts` cell: 136 weapons
  - Incremental protection added by loadouts: 113 weapons
- **Soft-protected (not hard-protected):** 223
  - Exotic weapons: 82
  - Locked Legendary weapons: 141 (out of 326 total locked weapons)
- **Completely unprotected weapons:** 272
  - In vault: 231
  - On characters (unequipped): 41

### Capacity equation validation on real data

Given the owner's estimate of current free vault spaces `F ≈ 10`:
- Unequipped character weapons to clear into vault: `C = 100`
- Raw vault impact before removals: `F - C = 10 - 100 = -90` (a shortfall of 90 spaces)
- Required removals across vault (`Dv`) and characters (`Dc`) to achieve `projected_free >= 100`:
  `projected_free = F + Dv - (C - Dc) >= 100`
  `10 + Dv - (100 - Dc) >= 100`
  `Dv + Dc >= 190`

The clear-out workflow requires **at least 190 approved removals** across vault and
character inventories to achieve 100 free spaces after clearing character inventories.
With 272 completely unprotected weapons (and 141 locked legendary weapons available
for manual review), the goal is mechanically feasible, but current baseline rules
yield only 5 removals.
