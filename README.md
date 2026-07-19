# vault-cleaner

Tag Destiny 2 vault clutter from [DIM](https://destinyitemmanager.com) CSV
exports, for re-import into DIM. No Bungie API, no credentials — pure file in,
file out. The tool only *tags* (with a reason per item); deletion stays a
manual, in-game step via a `tag:junk` search in DIM.

**Spec:** [PLAN.md](PLAN.md) · **Session history:** [WORKLOG.md](WORKLOG.md) ·
**Agent guide:** [AGENTS.md](AGENTS.md)

## How it works

1. DIM Organizer → export weapons / armor / ghost CSVs into `data/in/`
2. `vault-cleaner` parses them, applies rules (safety rails → wishlists →
   dupes → armor scoring), and writes `data/out/dim-import.csv` with
   `Id, Hash, Tag, Notes` columns
3. DIM Settings → "Import tags/notes from CSV"
4. In game: search `tag:junk`, review, dismantle

`data/` is personal vault data and is gitignored — it never leaves your machine.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/pytest -q

# M1 round trip: tag one item, dry-run by default
.venv/bin/vault-cleaner roundtrip --item "A Good Shout"
.venv/bin/vault-cleaner roundtrip --kind ghosts --item "Aero Dart Shell"
.venv/bin/vault-cleaner roundtrip --id 6917530162665277291 --write
```

## Status

- ✅ M1 — round trip: parse DIM weapon + ghost exports, write a DIM-importable tags CSV
- ✅ M2 — weapon dupe resolver + safety rails (`vault-cleaner dupes`; locked/exotics get review notes, never junk)
- ✅ M3 — wishlists: download/parse (choosy_voltron, Aegis keep + trash) and matching wired into the dupe ranking via the Bungie manifest's perk name→hash map
- ✅ M4 — Armor 3.0 archetype scoring (`vault-cleaner armor`; config-driven build weights, set-bonus favoring, top-N + floor)
- 🔶 M5 — polish: ghost cleanup pass ✅ (`vault-cleaner ghosts`); summary report pending

See the [issue board](https://github.com/tonym999/vault-cleaner/issues) for
ticket-level detail.
