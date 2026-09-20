# Issue #34 measurement evidence

Verbatim command transcripts backing the measured design in
[handoffs/issue-34-implementation-plan.md](../../../handoffs/issue-34-implementation-plan.md)
and the rescoped body of [#34](https://github.com/tonym999/vault-cleaner/issues/34).
Every block below is a command and the output that command produced; nothing here
has been edited after capture.

**Real-export authorisation.** These measurements read
`data/in/2026-09-01T-current/weapons.csv`, a real DIM weapons export. The owner
authorised real-export measurement for this ticket on 2026-09-20, permitting
aggregate counts, distributions and item names in committed findings. The scripts
below print only those; instance `Id` values, verbatim CSV rows and `Notes` cell
contents are never printed, so no capture required redaction. The export itself
is never committed.

Environment: Linux 7.0.0-31-generic, Python 3.14.4, pandas 3.0.5, measured on
2026-09-20 against `main` at `775f662`.

```bash
set -euo pipefail
.venv/bin/python -c "import sys, pandas; print('python', sys.version.split()[0]); print('pandas', pandas.__version__)"
uname -sr
```

```text
python 3.14.4
pandas 3.0.5
Linux 7.0.0-31-generic
```

Both fences below set `wishlists.max_age_days` in memory so the configured
sources are read from the existing cache rather than re-downloaded. The first
run of section 1 in this session did download `wishlists/aegis_keep.txt`, which
the cache did not yet hold after #158 replaced the Nitaraku source; the capture
below is from a later run, and reports `fetch=cache` for all three sources.

---

## 1. Same-Hash useful-combination coverage relations

This is the measurement the plan's comparison rule, yield table and consensus
findings are taken from. It reproduces the pipeline position of the proposed
pass — wishlist-trash junk removed, exact-roll groups resolved — before
classifying every ordered pair of distinct rolls within one `Hash`. Block `[7]`
re-classifies the same pairs on subsumption-collapsed sets — the wrong basis — so
the cost of that mistake is measured rather than asserted.

```bash
set -euo pipefail
OUT="$(mktemp -d)"
cat > "$OUT/coverage_measure.py" <<'PY'
"""Same-Hash useful-combination coverage measurement for issue #34.

Prints aggregates, distributions and weapon names only: no instance Ids, no
verbatim CSV rows, no Notes cell contents.
"""
import sys
from collections import Counter, defaultdict

from vault_cleaner.config import load_config
from vault_cleaner.manifest import load_perk_map_data
from vault_cleaner.parse import load_weapons
from vault_cleaner.rules import rails
from vault_cleaner.rules.dupes import exact_roll_fingerprint, rank_key
from vault_cleaner.rules.id_order import instance_id_order
from vault_cleaner.rules.weapons import row_perk_hashes, trash_match
from vault_cleaner.wishlist import load_all_with_evidence

cfg = load_config("config.toml")
cfg["wishlists"]["max_age_days"] = 1e9          # measure the cached bytes
evidence = load_all_with_evidence(cfg)
wl = evidence.merged
perk = load_perk_map_data(cfg["paths"]["manifest_cache_dir"], 1e9)
perk_map = perk.names
weapons = load_weapons(sys.argv[1])
clp = cfg["rails"]["crafted_level_protect"]

print("[1] inputs")
print(f"  export rows={len(weapons)} unique_hash={weapons['Hash'].nunique()}")
print(f"  manifest_version={perk.version} perk_names={len(perk_map)}")
for status in evidence.statuses:
    print(f"  source={status.spec.name} family={status.spec.family} "
          f"keep_rolls={status.keep_entries} keep_items={status.keep_items} "
          f"trash_rolls={status.trash_entries} fetch={status.fetch.status}")

# Collapse base/enhanced display-name variants onto one deterministic token.
canon = {}
for name in sorted(perk_map):
    token = min(perk_map[name])
    for perk_hash in perk_map[name]:
        canon.setdefault(perk_hash, token)


def canonical(roll):
    return frozenset(canon.get(perk_hash, perk_hash) for perk_hash in roll)


def maximal(rolls):
    """Drop recommendations subsumed by a more specific matched one."""
    return {roll for roll in rolls if not any(roll < other for other in rolls)}


rows = []
for _, row in weapons.iterrows():
    item_hash = int(row["Hash"])
    perks = row_perk_hashes(row, perk_map)
    curated = wl.keep.get(item_hash, [])
    matched = {canonical(roll) for roll in curated if roll <= perks}
    level, reason = rails.protection(row, clp)
    rows.append({
        "id": str(row["Id"]), "hash": item_hash, "name": row["Name"],
        "fingerprint": exact_roll_fingerprint(row), "matched": matched,
        "collapsed": maximal(matched), "protection": level or "unprotected",
        "trash": trash_match(item_hash, perks, wl), "rank": rank_key(row),
        "loadout": bool(str(row.get("Loadouts", "")).strip()),
    })

print("[2] groupability and coverage")
print(f"  rows without an exact-roll fingerprint (never compared)="
      f"{sum(1 for r in rows if r['fingerprint'] is None)}")
print(f"  rows with >=1 matched keep roll={sum(1 for r in rows if r['matched'])}")
print(f"  rows with curated rolls for their Hash but no match="
      f"{sum(1 for r in rows if not r['matched'] and wl.keep.get(r['hash']))}")
print(f"  rows whose Hash has no curated keep roll="
      f"{sum(1 for r in rows if not wl.keep.get(r['hash']))}")
print("  matched rolls per row (uncollapsed):",
      sorted(Counter(len(r["matched"]) for r in rows if r["matched"]).items()))
print("  combinations per row (subsumption-collapsed):",
      sorted(Counter(len(r["collapsed"]) for r in rows if r["collapsed"]).items()))
print(f"  rows where collapsing reduced the count="
      f"{sum(1 for r in rows if len(r['collapsed']) < len(r['matched']))}")

family_rolls = defaultdict(list)
for item_hash, entries in (wl.keep_evidence or {}).items():
    for entry in entries:
        family_rolls[item_hash].append((canonical(entry.perks), entry.family))
exact_agreement, subsumption_agreement = Counter(), Counter()
for row in rows:
    for combination in row["collapsed"]:
        exact_agreement[len({
            family for roll, family in family_rolls[row["hash"]]
            if roll == combination
        })] += 1
        subsumption_agreement[len({
            family for roll, family in family_rolls[row["hash"]]
            if roll <= combination and roll in row["matched"]
        })] += 1
print("[3] family consensus per collapsed combination")
print("  exact-roll-identity agreement:", sorted(exact_agreement.items()))
print("  subsumption-aware agreement:  ", sorted(subsumption_agreement.items()))

# Reproduce the pipeline position: wishlist-trash junk leaves the pool, the
# exact pass resolves its groups, and the coverage pass sees what is left.
trash_junked = {
    r["id"] for r in rows
    if r["trash"] and not r["matched"] and r["protection"] == "unprotected"
}
pool = [r for r in rows if r["id"] not in trash_junked]
exact_groups = defaultdict(list)
for row in pool:
    if row["fingerprint"] is not None:
        exact_groups[(str(row["hash"]), row["fingerprint"])].append(row)
exact_losers = set()
for members in exact_groups.values():
    if len(members) < 2:
        continue
    best_rank = max(member["rank"] for member in members)
    winner = min((m for m in members if m["rank"] == best_rank),
                 key=lambda m: instance_id_order(m["id"]))
    exact_losers |= {m["id"] for m in members if m["id"] != winner["id"]}
survivors = [r for r in pool
             if r["id"] not in exact_losers and r["fingerprint"] is not None]
by_hash = defaultdict(list)
for row in survivors:
    by_hash[row["hash"]].append(row)
multi_roll = {h: v for h, v in by_hash.items()
              if len({m["fingerprint"] for m in v}) >= 2}
print("[4] pipeline position")
print(f"  wishlist-trash junk removed from the pool={len(trash_junked)}")
print(f"  exact-roll groups with >=2 members="
      f"{sum(1 for m in exact_groups.values() if len(m) > 1)} "
      f"losers={len(exact_losers)}")
print(f"  coverage-pass input (undecided, groupable)={len(survivors)}")
print(f"  Hashes with >=2 distinct rolls={len(multi_roll)} "
      f"instances={sum(len(v) for v in multi_roll.values())}")
print("  distinct rolls per such Hash:", sorted(Counter(
    len({m['fingerprint'] for m in v}) for v in multi_roll.values()).items()))

relations = Counter()
dominated, uncovered = {}, {}
trade_off, equal, neither = set(), set(), set()
for members in multi_roll.values():
    for a in members:
        for b in members:
            if a["id"] == b["id"] or a["fingerprint"] == b["fingerprint"]:
                continue
            ca, cb = a["matched"], b["matched"]
            if not ca and not cb:
                relations["both-uncovered"] += 1
                neither.add(a["id"])
            elif not ca:
                relations["A-uncovered-B-covered"] += 1
                gain = len(b["collapsed"])
                best = uncovered.get(a["id"])
                if best is None or gain > best[0] or (
                        gain == best[0]
                        and instance_id_order(b["id"])
                        < instance_id_order(best[1]["id"])):
                    uncovered[a["id"]] = (gain, b, a)
            elif not cb:
                continue
            elif ca == cb:
                relations["equal-coverage"] += 1
                equal.add(a["id"])
            elif ca < cb:
                relations["A-strict-subset-of-B"] += 1
                gain = len(b["collapsed"] - a["collapsed"])
                best = dominated.get(a["id"])
                if best is None or gain > best[0] or (
                        gain == best[0]
                        and instance_id_order(b["id"])
                        < instance_id_order(best[1]["id"])):
                    dominated[a["id"]] = (gain, b, a)
            elif ca > cb:
                continue
            else:
                relations["mutual-trade-off"] += 1
                trade_off.add(a["id"])
print("[5] ordered pair relations among distinct rolls of one Hash")
for relation, count in sorted(relations.items()):
    print(f"  {relation}={count}")

print("[6] distinct instances that would receive advice")
for label, found in (("coverage-dominated by", dominated),
                     ("coverage-uncovered vs", uncovered)):
    eligible = {i: v for i, v in found.items() if v[2]["protection"] != "hard"}
    print(f"  {label}: candidates={len(found)} "
          f"after hard-rail exclusion={len(eligible)}")
    print("    protection="
          f"{Counter(v[2]['protection'] for v in found.values()).most_common()}"
          f" in_loadout={sum(1 for v in found.values() if v[2]['loadout'])}")
    print(f"    collapsed gain |B\\A|="
          f"{sorted(Counter(v[0] for v in found.values()).items())}")
    print(f"    distinct names={len({v[2]['name'] for v in found.values()})}")
    print(f"    names={sorted({v[2]['name'] for v in found.values()})}")
print(f"  mutual trade-off (kept by the rule)={len(trade_off)}"
      f" equal-coverage={len(equal)} both-uncovered={len(neither)}")
print(f"  instances in both advice sets={len(set(dominated) & set(uncovered))}")

# The same ordered pairs classified on the subsumption-collapsed sets. This is
# the wrong basis for comparison and is measured only to show what it costs.
collapsed_relations = Counter()
collapsed_dominated = set()
for members in multi_roll.values():
    for a in members:
        for b in members:
            if a["id"] == b["id"] or a["fingerprint"] == b["fingerprint"]:
                continue
            ca, cb = a["collapsed"], b["collapsed"]
            if not ca and not cb:
                collapsed_relations["both-uncovered"] += 1
            elif not ca:
                collapsed_relations["A-uncovered-B-covered"] += 1
            elif not cb:
                continue
            elif ca == cb:
                collapsed_relations["equal-coverage"] += 1
            elif ca < cb:
                collapsed_relations["A-strict-subset-of-B"] += 1
                collapsed_dominated.add(a["id"])
            elif ca > cb:
                continue
            else:
                collapsed_relations["mutual-trade-off"] += 1
print("[7] the same pairs classified on collapsed sets (the wrong comparison basis)")
for relation, count in sorted(collapsed_relations.items()):
    print(f"  {relation}={count}")
print(f"  coverage-dominated by candidates={len(collapsed_dominated)}"
      f" (uncollapsed={len(dominated)})")
missed = set(dominated) - collapsed_dominated
print(f"  dominance relations a collapsed comparison would miss={len(missed)}")
print("  missed names="
      f"{sorted({dominated[i][2]['name'] for i in missed})}")
print(f"  dominance relations only a collapsed comparison would claim="
      f"{len(collapsed_dominated - set(dominated))}")
PY
.venv/bin/python "$OUT/coverage_measure.py" data/in/2026-09-01T-current/weapons.csv > "$OUT/coverage_measure.txt" 2>&1
cat "$OUT/coverage_measure.txt"
```

`$OUT/coverage_measure.txt`:

```text
[1] inputs
  export rows=665 unique_hash=438
  manifest_version=244213.26.06.29.2000-1-bnet.65583 perk_names=10627
  source=choosy_voltron family=choosy-voltron keep_rolls=255373 keep_items=1234 trash_rolls=53 fetch=cache
  source=aegis_keep family=aegis-endgame keep_rolls=2610 keep_items=522 trash_rolls=0 fetch=cache
  source=aegis_trash family=aegis-endgame keep_rolls=0 keep_items=0 trash_rolls=286 fetch=cache
[2] groupability and coverage
  rows without an exact-roll fingerprint (never compared)=0
  rows with >=1 matched keep roll=301
  rows with curated rolls for their Hash but no match=128
  rows whose Hash has no curated keep roll=236
  matched rolls per row (uncollapsed): [(1, 87), (2, 92), (3, 23), (4, 54), (5, 10), (6, 16), (7, 2), (8, 5), (9, 4), (10, 5), (14, 2), (18, 1)]
  combinations per row (subsumption-collapsed): [(1, 99), (2, 91), (3, 17), (4, 59), (5, 9), (6, 9), (8, 8), (9, 4), (10, 3), (12, 1), (14, 1)]
  rows where collapsing reduced the count=46
[3] family consensus per collapsed combination
  exact-roll-identity agreement: [(1, 823)]
  subsumption-aware agreement:   [(1, 724), (2, 99)]
[4] pipeline position
  wishlist-trash junk removed from the pool=11
  exact-roll groups with >=2 members=1 losers=2
  coverage-pass input (undecided, groupable)=652
  Hashes with >=2 distinct rolls=116 instances=339
  distinct rolls per such Hash: [(2, 62), (3, 30), (4, 11), (5, 4), (6, 4), (7, 3), (8, 2)]
[5] ordered pair relations among distinct rolls of one Hash
  A-strict-subset-of-B=31
  A-uncovered-B-covered=93
  both-uncovered=296
  equal-coverage=24
  mutual-trade-off=306
[6] distinct instances that would receive advice
  coverage-dominated by: candidates=30 after hard-rail exclusion=30
    protection=[('unprotected', 21), ('soft', 9)] in_loadout=4
    collapsed gain |B\A|=[(1, 15), (2, 5), (3, 5), (4, 3), (5, 1), (12, 1)]
    distinct names=19
    names=['Blast Furnace', 'Cynosure', 'DECATUR 02', 'DIABLERETS 06', 'Eighty-Six', 'Gizmo Weft', 'Motif-41', 'Perfect Paradox', 'Positive Outlook', 'Punching Out', 'Refusal of the Call', "Reghusk's Pledge", 'Service Revolver', 'Stars in Shadow', "Stryker's Sure-Hand", "Temptation's Hook", 'The Recluse', 'The Ringing Nail', 'The Slammer']
  coverage-uncovered vs: candidates=53 after hard-rail exclusion=50
    protection=[('unprotected', 28), ('soft', 22), ('hard', 3)] in_loadout=3
    collapsed gain |B\A|=[(1, 16), (2, 18), (3, 1), (4, 10), (5, 1), (6, 2), (8, 2), (9, 1), (10, 2)]
    distinct names=37
    names=['Adamantite', 'Aurora Dawn', 'Cynosure', 'DECATUR 02', 'Eighty-Six', "Elsie's Rifle", 'Ergo Sum', 'Evening SI4', "Felwinter's Lie", 'Fimbulwinter Stitch', 'Forced Memorializer', "Horror's Least", 'IRONWOOD 03', "Joxer's Longsword", 'King Orfeo', 'Mercury-A', 'Mint Retrograde', 'Mistral Lift', 'Phoneutria Fera', 'Precipial', 'Pro Memoria', 'Punching Out', 'Riptide', 'Roar of the Bear', 'Sarpedon-D', 'Service Revolver', 'Tarnation', "Temptation's Hook", 'The Recluse', 'The Slammer', 'The Time-Worn Spire', 'The Wizened Rebuke', 'Trachinus', 'Uncivil Discourse', 'Unending Tempest', 'Vouchsafe', 'Wilderflight']
  mutual trade-off (kept by the rule)=148 equal-coverage=13 both-uncovered=114
  instances in both advice sets=0
[7] the same pairs classified on collapsed sets (the wrong comparison basis)
  A-strict-subset-of-B=28
  A-uncovered-B-covered=93
  both-uncovered=296
  equal-coverage=24
  mutual-trade-off=312
  coverage-dominated by candidates=27 (uncollapsed=30)
  dominance relations a collapsed comparison would miss=3
  missed names=['Gizmo Weft', "Reghusk's Pledge", 'Stars in Shadow']
  dominance relations only a collapsed comparison would claim=0
```

---

## 2. Perk scope equivalence

The proposed pass reuses `rules.weapons.row_perk_hashes`, which reads every
`Perks N` cell, rather than restricting matching to #31's immutable pre-tracker
prefix. This fence measures whether that choice changes any match.

```bash
set -euo pipefail
OUT="$(mktemp -d)"
cat > "$OUT/perk_scope.py" <<'PY'
"""Does coverage matching change if it reads only #31's immutable roll prefix?

Aggregates only: no instance Ids, no verbatim CSV rows, no Notes contents.
"""
import sys
from collections import Counter

from vault_cleaner.config import load_config
from vault_cleaner.manifest import load_perk_map_data
from vault_cleaner.parse import load_weapons
from vault_cleaner.rules.dupes import exact_roll_display_prefix
from vault_cleaner.rules.weapons import row_perk_hashes
from vault_cleaner.wishlist import load_all

cfg = load_config("config.toml")
cfg["wishlists"]["max_age_days"] = 1e9
wl = load_all(cfg)
perk_map = load_perk_map_data(cfg["paths"]["manifest_cache_dir"], 1e9).names
weapons = load_weapons(sys.argv[1])


def prefix_hashes(row):
    """Perk hashes reachable from the measured pre-tracker roll prefix only."""
    hashes = set()
    for name in exact_roll_display_prefix(row):
        key = name.strip().removesuffix("*").strip().casefold()
        hashes |= perk_map.get(key, frozenset())
    return frozenset(hashes)


differing = 0
lost = Counter()
whole_row_total = prefix_total = 0
for _, row in weapons.iterrows():
    curated = wl.keep.get(int(row["Hash"]), [])
    if not curated:
        continue
    whole_row = row_perk_hashes(row, perk_map)
    prefix_only = prefix_hashes(row)
    matched_whole = {frozenset(r) for r in curated if r <= whole_row}
    matched_prefix = {frozenset(r) for r in curated if r <= prefix_only}
    whole_row_total += len(matched_whole)
    prefix_total += len(matched_prefix)
    if matched_whole != matched_prefix:
        differing += 1
        lost[len(matched_whole - matched_prefix)] += 1

print(f"rows whose matched set differs between the two scopes: {differing}")
print(f"total matched rolls: whole-row={whole_row_total} "
      f"pre-tracker-prefix={prefix_total}")
print(f"per-row matches lost by restricting to the prefix: {sorted(lost.items())}")
PY
.venv/bin/python "$OUT/perk_scope.py" data/in/2026-09-01T-current/weapons.csv > "$OUT/perk_scope.txt" 2>&1
cat "$OUT/perk_scope.txt"
```

`$OUT/perk_scope.txt`:

```text
rows whose matched set differs between the two scopes: 0
total matched rolls: whole-row=929 pre-tracker-prefix=929
per-row matches lost by restricting to the prefix: []
```
