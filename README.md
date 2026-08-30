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
3. Optionally review the proposals first — in the terminal, or in the local
   browser review server — and let the reviewed CSV replace the raw one
4. DIM Settings → "Import tags/notes from CSV"
5. In game: search `tag:junk`, review, dismantle

`data/` is personal vault data and is gitignored — it never leaves your machine.

Weapon duplicate cleanup is deliberately conservative: it groups only copies
with the same item `Hash` and a proven exact-roll fingerprint from the DIM
export. Different perk rolls under one Hash, or rows whose roll identity is
incomplete, survive independently; wishlist-trash remains a separate rule.
The fingerprint keeps complete named pre-tracker perk cells (including names
beginning with the literal `Enhanced` followed by one separator space),
normalizing only DIM's trailing selected `*` marker.
The measured structural boundary is exactly `Kill Tracker` or `Crucible
Tracker`, compared case-insensitively after removing one trailing marker.
Unknown or future names that merely end in `Tracker` remain part of the
identity until a later measured boundary; without one, the row is left
ungroupable. The `Perks N` header width follows the export: `Perks 0` is the
minimal invariant, and gaps or incomplete tracker boundaries are left
ungroupable. Perk cells are kept whole, including legitimate comma-bearing
names. Comma-bearing cells containing either measured tracker label are left
ungroupable regardless of component order or marker placement.

If your DIM exports land somewhere else, set the default input and output
directories in `config.toml`:

```toml
[paths]
input_dir = "data/in"
output_dir = "data/out"
```

For a WSL workflow that reads directly from your Windows Downloads folder, use
the mounted path:

```toml
[paths]
input_dir = "/mnt/c/Users/<you>/Downloads"
output_dir = "data/out"
```

Explicit command-line paths still take precedence over these defaults.

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

## Review workflow

`vault-cleaner report` shows what the rules *propose*. `vault-cleaner review`
is where you record what you actually approved, and it is the command that
writes the reviewed import CSV.

```bash
# what the rules propose (unchanged; never applies your vetoes)
.venv/bin/vault-cleaner report

# how your saved vetoes line up with a fresh run — no manifest needed
.venv/bin/vault-cleaner review

# validate a review manifest and show what it would change
.venv/bin/vault-cleaner review --manifest data/review.json

# persist the vetoes and write the reviewed CSV
.venv/bin/vault-cleaner review --manifest data/review.json --write
```

`report --write` writes the proposal CSV, while `review --write` writes the
reviewed CSV and updates `data/overrides.json`. None of these terminal commands
changes what another one produces.

### What a veto is

A **veto** suppresses one proposed junk/review row. It does not tag the item
`keep`, change its existing DIM tag, or rerank its dupe group — overrides
apply after the ordered rules pipeline, so vetoing a losing copy just means
one more copy survives this cleanup; the winner the rules picked is
unchanged.

**A veto cannot undo a junk tag you already imported.** If an earlier cleanup
tagged the item and you imported that CSV, the tag lives in DIM now. Vetoing
stops the tool re-proposing it; clearing the tag is a manual step in DIM. The
command warns when a vetoed item is in that state.

Vetoes persist in `data/overrides.json` (gitignored like everything under
`data/`), written atomically so an interrupted run cannot corrupt them.
Applying a manifest is additive: approving an id never removes a veto you
already recorded. To un-veto something, edit the file.

### Refusals and staleness

The manifest names the report run it was produced against. If your exports,
config, wishlists, or the Bungie manifest changed since, the fingerprints
differ and `review` **refuses** rather than warning — applying those verdicts
would suppress rows you never actually looked at. Re-run the report and
review again.

Individual saved vetoes are reported as:

| status | meaning |
| --- | --- |
| `active` | still matches a proposal; it is being suppressed |
| `stale` | the item is still there, but the rules propose something else (or nothing) now — not applied, re-review it |
| `orphaned` | the id is gone from the export; you probably dismantled it |
| `unchecked` | that export was not loaded this run, so nothing can be said about it |

### Review manifest format

`schema_version`, the snapshot versions, and the fingerprint must all match
the current build and run. Unknown keys are rejected outright — a manifest
comes from a browser, and no filesystem path is ever read out of one.

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-25T12:00:00Z",
  "snapshot": { "schema_version": 1, "ruleset_version": 1, "fingerprint": "<from the report run>" },
  "decisions": [
    { "id": "6917529027641981542", "kind": "weapons", "hash": "500",
      "name": "Dupe Rifle", "action": "junk", "reason": "dupe-lower",
      "verdict": "vetoed" }
  ]
}
```

`verdict` is `approved` or `vetoed`. `id` and `hash` are opaque strings —
never JSON numbers, which have already lost 64-bit precision by the time
they parse. An id may appear only once. The remaining fields are display
metadata for explaining stale entries later; identity is `id` alone, and the
run itself is trusted over the manifest for everything else.

The format is intended for CLI, scripting, and backup workflows. The local
review server does not import or export review manifests; it keeps its
acknowledged verdicts in the authenticated session and finalises them directly.

### Reviewing in a browser

For the complete local browser workflow, start the server and open the one-use
URL it prints:

```bash
.venv/bin/vault-cleaner serve --no-wishlists
```

The server binds only to `127.0.0.1`. Treat the bootstrap URL as a local secret:
it carries a short-lived, one-use token that establishes the authenticated
browser session. Upload any combination of DIM weapons, armor, and ghost CSVs;
the browser submits file bytes and never submits a filesystem path. The report
uses the shared search, filters, grouping, sorting, detail, armor-scoring, and
count views.

Review proposals with **Approve**, **Veto**, and **Unset** (or <kbd>a</kbd>,
<kbd>v</kbd>, and <kbd>u</kbd> from a focused row). Acknowledged verdicts live
in this authenticated local server session until finalisation; they are not a
DIM import and are not yet durable. Existing durable vetoes from
`data/overrides.json` may already suppress proposals, and approving a proposal
does not remove such a veto.

Choose **Finalise review** to persist this session's new vetoes, produce the
reviewed CSV, and download it as `dim-import.csv`. **Download again** retrieves
the same finalised bytes without repeating finalisation. **Reset / Start new
review** clears the live report and session verdicts without deleting exports
or durable overrides. **Shutdown** terminates the server session; <kbd>Ctrl-C</kbd>
in its terminal is also available.

> **Privacy:** vault exports, report data, verdicts, and generated CSV bytes
> remain on your machine. The server has no Bungie credentials, account login,
> API key, or authenticated account access. Optional wishlist and public Bungie
> manifest downloads fetch static game content; that is separate from uploading
> vault data anywhere. Use `--no-wishlists` when you want the server workflow to
> make no wishlist or manifest network requests.

## Status

- ✅ M1 — round trip: parse DIM weapon + ghost exports, write a DIM-importable tags CSV
- ✅ M2 — weapon dupe resolver + safety rails (`vault-cleaner dupes`; locked/exotics get review notes, never junk)
- ✅ M3 — wishlists: download/parse (choosy_voltron, Aegis keep + trash) and matching wired into wishlist-trash protection via the Bungie manifest's perk name→hash map
- ✅ M4 — Armor 3.0 archetype scoring (`vault-cleaner armor`; config-driven build weights, set-bonus favoring, top-N + floor)
- ✅ M5 — polish: ghost cleanup pass (`vault-cleaner ghosts` — junks every shell not equipped/locked/tagged/in a loadout) and the all-passes dry-run summary (`vault-cleaner report`)
- ✅ M6 — armor dupes: exact-dupe pass, review-only close-dupe pass, and the last-of-archetype score guard
- ✅ M7 — review UI: reusable report snapshot ✅ and persistent vetoes + reviewed export (`vault-cleaner review`) ✅; the unreleased static prototype was retired after server parity
- 🚧 M8 — local review server: authenticated loopback upload, review, finalisation, and download workflow complete; armor what-if follow-ups remain

See the [issue board](https://github.com/tonym999/vault-cleaner/issues) for
ticket-level detail.

## License

[MIT](LICENSE)
