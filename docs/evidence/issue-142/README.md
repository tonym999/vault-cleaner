# Issue #142 baseline measurement evidence

Verbatim command transcripts and raw outputs backing the measurements in
[docs/aggressive-clearout-measurement.md](../../aggressive-clearout-measurement.md),
with two exceptions noted individually below: the two real-export `report` captures
in §8 have had instance `Id`s redacted post-capture under an explicit owner privacy
decision, so they are not byte-verbatim against the original command's actual
output (see the note directly above each one, and §14 item 7 in the measurement
document).

Sections 1–8 were run on Windows within Git Bash (`bash 5.2.26`) on Python 3.13.14
with pandas 3.0.5, using `export PYTHONUTF8=1` to enforce UTF-8 streams and avoid
codepage encoding errors on Unicode fixture symbols (such as the emoji in
`tests/fixtures/weapons_hostile.csv`). This correction round's re-verification of
§9 (and the new measurements added to §5's "Measured source detail" in the
measurement document) ran on Linux, in this session, on 2026-09-06; the reproduced
values are identical, so no divergence is recorded.

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

Re-run in this correction round (2026-09-06, this session's Linux environment —
a different machine and cache than round 1's Windows capture). This is the one
capture the plan holds to a different standard than byte-for-byte reproduction
(measurement document, §1 "Reproduction commands" and C4): it must execute
successfully and record cache mtimes and download-or-fallback state, and a content
difference is only a finding if that recorded state does not explain it. Here the
parsed keep/trash counts are byte-identical to round 1's capture; only the cache
file sizes and mtimes differ (different machine, different fetch), which the
recorded mtimes below fully explain.

```bash
set -euo pipefail
OUT="$(mktemp -d)"
.venv/bin/vault-cleaner wishlists > "$OUT/wishlists.txt" 2>&1
ls -l wishlists/ > "$OUT/wishlists_ls.txt" 2>&1
cat "$OUT/wishlists.txt"
cat "$OUT/wishlists_ls.txt"
```

Output (`wishlists.txt`):

```text
choosy_voltron: 255373 keep rolls across 1234 items, 53 trash entries across 53 items
aegis: 5022 keep rolls across 968 items, 0 trash entries across 0 items
aegis_trash: 0 keep rolls across 0 items, 286 trash entries across 286 items
total: 260395 keep rolls, 339 trash entries
```

Output (`wishlists_ls.txt`):

```text
total 26472
-rw-rw-r-- 1 raver raver   346965 Sep  6 14:23 aegis.txt
-rw-rw-r-- 1 raver raver    29281 Sep  6 14:23 aegis_trash.txt
-rw-rw-r-- 1 raver raver 26723730 Sep  6 14:23 choosy_voltron.txt
```

No `warning: ... download failed` line appears in `wishlists.txt`, and the three
files' mtime (`Sep 6 14:23`) was already current at the start of this session,
before this command ran — confirmed by comparing this `ls -l` capture (run after
the `vault-cleaner wishlists` call above) against an identical `ls -la wishlists/`
run at the very start of this session, which showed the same three mtimes. The
command therefore **served all three sources from cache**, not by downloading, in
this session.

---

## 8. Aggregate-only real-export analysis (authorized session data)

An actual DIM weapon export (`destiny-weapon (12).csv`) was supplied and authorized
for measurement by the repository owner on 2026-09-06.

**Privacy record (corrected):** No `Hash` values, instance `Id`s, or individual raw
CSV rows are stored, quoted, or committed anywhere in this document. **Item names**
are the one exception: the two `report` captures below were additionally, explicitly
authorized for publication by the repository owner on 2026-09-06 (see
[docs/aggressive-clearout-measurement.md](../../aggressive-clearout-measurement.md)
§1 and §14, and `WORKLOG.md`). Every instance `Id` that originally appeared in those
two captures has been **redacted to `id <redacted>` after capture** — see the note
directly above each one. Because of that redaction, those two blocks are **not**
byte-verbatim command output, unlike every other capture in this file.

### Derivation script and output

This fence takes the export path as `$EXPORT`, defaulting to the original
implementer's own path if unset — **that default resolves on no other machine**.
A reader reproducing this capture must supply their own copy of the identical file
(verified against the recorded SHA-256 below) as `EXPORT=/path/to/export.csv`. See
§14 in the measurement document: this file is not obtainable by any reader other
than its owner, so this fence is auditable only by the owner against the recorded
hash — that is a defect independent of privacy, and this parameterization is the
fix (round 1 hardcoded `C:/Users/raver/Downloads/destiny-weapon (12).csv` directly
into the script, which nobody else could ever run).

```bash
set -euo pipefail
OUT="$(mktemp -d)"
EXPORT="${EXPORT:-C:/Users/raver/Downloads/destiny-weapon (12).csv}"

.venv/bin/python - "$EXPORT" <<'PY' > "$OUT/real_export_summary.txt" 2>&1
import hashlib
import pandas as pd
import csv
import sys

path = sys.argv[1]
with open(path, "rb") as f:
    content = f.read()
    sha256 = hashlib.sha256(content).hexdigest()

csv_rows = list(csv.reader(content.decode("utf-8", errors="replace").splitlines()))
header = csv_rows[0]
data_rows = csv_rows[1:]
df = pd.read_csv(path, dtype=str, keep_default_na=False)

print("=== 1. Export identity & integrity ===")
print("Export file: destiny-weapon (12).csv")
print(f"File size: {len(content)} bytes")
print(f"SHA-256: {sha256}")
print(f"Header columns: {len(header)}")
print(f"Data rows (csv.reader): {len(data_rows)}")
print(f"Data rows (pandas): {len(df)}")
print(f"Unique instance IDs: {df['Id'].nunique()}")
print(f"Unique weapon Hashes: {df['Hash'].nunique()}")

print("\n=== 2. Location & equipped breakdown ===")
owner_counts = df["Owner"].value_counts().to_dict()
for k, v in owner_counts.items():
    print(f"  Owner '{k}': {v}")
total_char = sum(v for k, v in owner_counts.items() if k != "Vault")
print(f"Total on characters: {total_char}")
eq_count = (df["Equipped"] == "true").sum()
print(f"Equipped (true): {eq_count}")
print(f"Unequipped on characters (C = total_char - equipped): {total_char - eq_count}")

tag_prot = df["Tag"].isin(["favorite", "keep", "archive"])
eq_prot = df["Equipped"] == "true"
crafted_prot = (df["Crafted"] == "crafted") & ((df["Crafted Level"] == "") | (df["Crafted Level"].astype(int) >= 10))
loadout_prot = df["Loadouts"].str.strip().ne("")

exotic = df["Rarity"] == "Exotic"
locked = df["Locked"] == "true"

# Current rules: Tag, Equipped, Crafted (no loadout rail)
hard_cur = tag_prot | eq_prot | crafted_prot
soft_cur = (exotic | locked) & ~hard_cur
unprot_cur = ~hard_cur & ~exotic & ~locked

print("\n=== 3. Current-rules world (no loadout rail) ===")
print(f"Hard-protected: {hard_cur.sum()}")
print(f"  - Tag protected: {tag_prot.sum()}")
print(f"  - Equipped: {eq_prot.sum()}")
print(f"  - Crafted (level >= 10 or unknown): {crafted_prot.sum()}")
print(f"Soft-protected (exotic or locked, not hard): {soft_cur.sum()}")
print(f"  - Exotic (not hard): {(exotic & ~hard_cur).sum()}")
print(f"  - Locked Legendary (not hard): {(locked & ~exotic & ~hard_cur).sum()}")
print(f"Completely unprotected: {unprot_cur.sum()}")
in_vault = df["Owner"] == "Vault"
on_char_uneq = (df["Owner"] != "Vault") & ~eq_prot
print(f"  - Unprotected in Vault: {(unprot_cur & in_vault).sum()}")
print(f"  - Unprotected on characters (unequipped): {(unprot_cur & on_char_uneq).sum()}")

# Proposed rules: Add loadouts rail
hard_prop = hard_cur | loadout_prot
soft_prop = (exotic | locked) & ~hard_prop
unprot_prop = ~hard_prop & ~exotic & ~locked

print("\n=== 4. Proposed-rules world (with loadouts rail) ===")
print(f"Hard-protected: {hard_prop.sum()}")
print(f"  - Loadouts non-empty: {loadout_prot.sum()}")
print(f"  - Incremental protection from loadouts: {hard_prop.sum() - hard_cur.sum()}")
print(f"Soft-protected (exotic or locked, not hard): {soft_prop.sum()}")
print(f"  - Exotic (not hard): {(exotic & ~hard_prop).sum()}")
print(f"  - Locked Legendary (not hard): {(locked & ~exotic & ~hard_prop).sum()}")
print(f"Completely unprotected: {unprot_prop.sum()}")
print(f"  - Unprotected in Vault: {(unprot_prop & in_vault).sum()}")
print(f"  - Unprotected on characters (unequipped): {(unprot_prop & on_char_uneq).sum()}")

print("\n=== 5. Capacity model calculation ===")
f_est = 10
c_val = total_char - eq_count
print(f"Estimated baseline free vault spaces (F): {f_est}")
print(f"Unequipped character items to clear (C): {c_val}")
print(f"Net vault capacity before removals (F - C): {f_est - c_val} (shortfall of {abs(f_est - c_val)} spaces)")
target_free = 100
req_removals = target_free - f_est + c_val
print(f"Required total unique removals (Dv + Dc >= target_free - F + C): {req_removals}")
PY

cat "$OUT/real_export_summary.txt"
```

Output:

```text
=== 1. Export identity & integrity ===
Export file: destiny-weapon (12).csv
File size: 323610 bytes
SHA-256: 35c9ee801b73a64c641dfe7a0f556c05d244f96a52902083e7a2fff7e0fb5571
Header columns: 74
Data rows (csv.reader): 664
Data rows (pandas): 664
Unique instance IDs: 664
Unique weapon Hashes: 440

=== 2. Location & equipped breakdown ===
  Owner 'Vault': 555
  Owner 'Titan(451)': 43
  Owner 'Warlock(550)': 35
  Owner 'Hunter(550)': 31
Total on characters: 109
Equipped (true): 9
Unequipped on characters (C = total_char - equipped): 100

=== 3. Current-rules world (no loadout rail) ===
Hard-protected: 56
  - Tag protected: 8
  - Equipped: 9
  - Crafted (level >= 10 or unknown): 41
Soft-protected (exotic or locked, not hard): 323
  - Exotic (not hard): 125
  - Locked Legendary (not hard): 198
Completely unprotected: 285
  - Unprotected in Vault: 239
  - Unprotected on characters (unequipped): 46

=== 4. Proposed-rules world (with loadouts rail) ===
Hard-protected: 169
  - Loadouts non-empty: 136
  - Incremental protection from loadouts: 113
Soft-protected (exotic or locked, not hard): 223
  - Exotic (not hard): 82
  - Locked Legendary (not hard): 141
Completely unprotected: 272
  - Unprotected in Vault: 231
  - Unprotected on characters (unequipped): 41

=== 5. Capacity model calculation ===
Estimated baseline free vault spaces (F): 10
Unequipped character items to clear (C): 100
Net vault capacity before removals (F - C): -90 (shortfall of 90 spaces)
Required total unique removals (Dv + Dc >= target_free - F + C): 190
```

### Dry-run pipeline yield on real export

Same `$EXPORT` parameterization as above; this default is likewise only reachable on
the original implementer's machine.

```bash
set -euo pipefail
export PYTHONUTF8=1
OUT="$(mktemp -d)"
EXPORT="${EXPORT:-C:/Users/raver/Downloads/destiny-weapon (12).csv}"

.venv/bin/vault-cleaner report --weapons "$EXPORT" --no-wishlists > "$OUT/real_nowishlists.txt" 2>&1
cat "$OUT/real_nowishlists.txt"

# Supplementary wishlist-enabled run using local Bungie manifest cache
# Note: Manifest version 244213.26.06.29.2000-1-bnet.65864; environment-dependent.
# This session could not re-verify that version string as command output — see
# docs/aggressive-clearout-measurement.md §14 item 1 for the genuine command output
# this session recorded instead, from this machine's own (different) cache.
.venv/bin/vault-cleaner report --weapons "$EXPORT" > "$OUT/real_wishlists.txt" 2>&1
cat "$OUT/real_wishlists.txt"
```

**Instance IDs redacted post-capture** (owner authorization covers item names only,
not `Id`s — see the privacy record above). This block is therefore not byte-verbatim
against the live command's actual output.

Output (`real_nowishlists.txt`):

```text
skipping armor: data\in\destiny-armor.csv not found; expected destiny-armor.csv or a browser-numbered copy such as destiny-armor (1).csv
skipping ghosts: data\in\destiny-ghost.csv not found; expected destiny-ghost.csv or a browser-numbered copy such as destiny-ghost (1).csv
would junk 0 item(s) and flag 2 for review

REVIEW dupe-lower (weapons) — 2 item(s)
  Praxic Blade (id <redacted>, class weapons; location Warlock(550)) — review: dupe-lower (exotic); keep [id <redacted>; location Vault; Tier 0; MW10; roll Balanced Grip / Cormorant Reversal]; winner higher stat total
  Praxic Blade (id <redacted>, class weapons; location Vault) — review: dupe-lower (exotic); keep [id <redacted>; location Vault; Tier 0; MW10; roll Balanced Grip / Cormorant Reversal]; winner higher stat total

dry run — pass --write to write the combined import CSV
```

**Instance IDs redacted post-capture**, same basis as above; not byte-verbatim.

Output (`real_wishlists.txt`):

```text
skipping armor: data\in\destiny-armor.csv not found; expected destiny-armor.csv or a browser-numbered copy such as destiny-armor (1).csv
skipping ghosts: data\in\destiny-ghost.csv not found; expected destiny-ghost.csv or a browser-numbered copy such as destiny-ghost (1).csv
would junk 5 item(s) and flag 6 for review

JUNK wishlist-trash whole-item (weapons) — 5 item(s)
  Avalanche (id <redacted>, class weapons; location Vault)
  Coriolis Force (id <redacted>, class weapons; location Vault)
  Qua Furor V (id <redacted>, class weapons; location Vault)
  Survivor's Epitaph (id <redacted>, class weapons; location Vault)
  Whistler's Whim (id <redacted>, class weapons; location Vault)

REVIEW wishlist-trash whole-item (weapons) — 4 item(s)
  Crowd Pleaser (id <redacted>, class weapons; location Vault)
  Frozen Orbit (id <redacted>, class weapons; location Vault)
  THE SWARM (Adept) (id <redacted>, class weapons; location Hunter(550))
  Truthteller (id <redacted>, class weapons; location Vault)

REVIEW dupe-lower (weapons) — 2 item(s)
  Praxic Blade (id <redacted>, class weapons; location Warlock(550)) — review: dupe-lower (exotic); keep [id <redacted>; location Vault; Tier 0; MW10; roll Balanced Grip / Cormorant Reversal]; winner higher stat total
  Praxic Blade (id <redacted>, class weapons; location Vault) — review: dupe-lower (exotic); keep [id <redacted>; location Vault; Tier 0; MW10; roll Balanced Grip / Cormorant Reversal]; winner higher stat total

note: 21 weapon(s) matched both keep and trash lists — keep outranked trash; normal dupe rules still apply to these items

dry run — pass --write to write the combined import CSV
```

---

## 9. Upstream wishlist repository metadata

Queries re-executed on 2026-09-06 via GitHub CLI / API to verify candidate source
freshness, under the fence contract (`set -euo pipefail`, a fresh `OUT="$(mktemp -d)"`,
capture to a file, `cat` that file last). `gh`'s `--jq` output is genuinely compact
single-line JSON — round 1's blocks below were pretty-printed by hand and are
replaced here with the literal captured bytes.

### Choosy Voltron (`48klocs/dim-wish-list-sources`)

```bash
set -euo pipefail
OUT="$(mktemp -d)"
gh api repos/48klocs/dim-wish-list-sources --jq '{default_branch: .default_branch, pushed_at: .pushed_at, description: .description}' > "$OUT/gh_48klocs.txt" 2>&1
cat "$OUT/gh_48klocs.txt"
```

`$OUT/gh_48klocs.txt`:

```text
{"default_branch":"master","description":"Source files for wish lists for DIM","pushed_at":"2026-08-03T22:53:37Z"}
```

### Ciceron (`Ciceron14/dim-extra-wishlists`)

```bash
set -euo pipefail
OUT="$(mktemp -d)"
gh api repos/Ciceron14/dim-extra-wishlists --jq '{default_branch: .default_branch, pushed_at: .pushed_at, description: .description}' > "$OUT/gh_ciceron.txt" 2>&1
cat "$OUT/gh_ciceron.txt"
```

`$OUT/gh_ciceron.txt`:

```text
{"default_branch":"main","description":"Collection of DIM Wishlists for Destiny 2 Weapons, based on Aegis's Spreadsheets","pushed_at":"2026-08-27T20:25:09Z"}
```

### MrCharles (`charlesxcaliber/DIMAegisWeaponWishlist`)

```bash
set -euo pipefail
OUT="$(mktemp -d)"
gh api repos/charlesxcaliber/DIMAegisWeaponWishlist --jq '{default_branch: .default_branch, pushed_at: .pushed_at, description: .description}' > "$OUT/gh_mrcharles.txt" 2>&1
cat "$OUT/gh_mrcharles.txt"
```

`$OUT/gh_mrcharles.txt`:

```text
{"default_branch":"main","description":"Based on Aegis's Endgame PvE Analysis, this wishlist labels all the best perks on all weapons, making it easier for you to determine whether to keep or dismantle weapons.","pushed_at":"2026-08-15T00:45:01Z"}
```

### Nitaraku (`Nitaraku/dim-wishlists`)

```bash
set -euo pipefail
OUT="$(mktemp -d)"
gh api repos/Nitaraku/dim-wishlists --jq '{default_branch: .default_branch, pushed_at: .pushed_at, description: .description}' > "$OUT/gh_nitaraku.txt" 2>&1
cat "$OUT/gh_nitaraku.txt"
```

`$OUT/gh_nitaraku.txt`:

```text
{"default_branch":"main","description":"Wishlists for DIM (Destiny Item Manager) based on Aegis Endgame Analysis","pushed_at":"2026-07-04T08:37:05Z"}
```

All four values reproduced exactly against the round 1 capture (`default_branch`,
`description`, `pushed_at` all identical) — only the formatting was wrong before.
