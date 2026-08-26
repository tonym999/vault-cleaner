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
3. Optionally review the proposals first — in the terminal, or in the
   [static HTML review page](#reviewing-in-a-browser) — and let the reviewed
   CSV replace the raw one
4. DIM Settings → "Import tags/notes from CSV"
5. In game: search `tag:junk`, review, dismantle

`data/` is personal vault data and is gitignored — it never leaves your machine.

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

# a browsable review page for the same proposals (dry run by default)
.venv/bin/vault-cleaner review-html --write

# how your saved vetoes line up with a fresh run — no manifest needed
.venv/bin/vault-cleaner review

# validate a review manifest and show what it would change
.venv/bin/vault-cleaner review --manifest data/review.json

# persist the vetoes and write the reviewed CSV
.venv/bin/vault-cleaner review --manifest data/review.json --write
```

Each command owns exactly one output. `report --write` writes the proposal
CSV, `review-html --write` writes the review page, and `review --write` writes
the reviewed CSV (and updates `data/overrides.json`). None of them ever
changes what another one produces.

### Reviewing in a browser

`vault-cleaner review-html` generates one self-contained HTML file — inline
CSS and JavaScript, the report snapshot embedded as inert JSON, and no fonts,
scripts, styles, analytics, or network requests of any kind. Open it straight
off disk; there is no server, port, or process to run.

```bash
# describe what would be generated, write nothing
.venv/bin/vault-cleaner review-html

# generate it (default: data/out/vault-review.html, gitignored)
.venv/bin/vault-cleaner review-html --write

# then: open it, approve/veto, export a review manifest, and apply it
.venv/bin/vault-cleaner review --manifest ~/Downloads/vault-review-manifest.json --write
```

> **Privacy:** the page embeds personal vault metadata — item names, instance
> ids, notes, and character names. Treat it like your DIM export: keep it
> local, and do not publish, paste, or attach it anywhere. It cannot leak on
> its own (a `default-src 'none'` policy blocks every outbound request), but
> the file itself is as sensitive as `data/in/`.

In the page you get overall junk/review counts and counts after vetoes, the
same action/kind/reason grouping the terminal summary prints, search by name
or instance id, filters for action, reason, kind, owner, protection state and
verdict, sortable columns, expandable per-item detail (including armor
scoring), and individual or bulk approve/veto. Unsaved changes are called out
explicitly, and with focus inside a row <kbd>a</kbd> approves, <kbd>v</kbd>
vetoes, and <kbd>u</kbd> unsets.

Verdicts are autosaved to browser storage, namespaced by the report
fingerprint, purely as a convenience — **export is the durable handoff**. The
page cannot write your DIM CSV, edit `config.toml`, or run the rules; it only
produces a manifest, and Python re-validates that from scratch before
anything is written.

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

`vault-cleaner review-html` is what generates these — see
[Reviewing in a browser](#reviewing-in-a-browser). The format is simple enough
to hand-write from a report run if you would rather script it.

### Local review server

For a local browser session, start the loopback-only server and open the one-use
URL it prints:

```bash
.venv/bin/vault-cleaner serve --no-wishlists
```

Upload any combination of DIM weapons, armor, and ghost CSVs in the page. The
report view reuses the search, filters, grouping, sorting, detail,
armor-scoring, and count views from `review-html`; it is read-only and never
accepts a filesystem path. Stop the server with <kbd>Ctrl-C</kbd> when done.

## Status

- ✅ M1 — round trip: parse DIM weapon + ghost exports, write a DIM-importable tags CSV
- ✅ M2 — weapon dupe resolver + safety rails (`vault-cleaner dupes`; locked/exotics get review notes, never junk)
- ✅ M3 — wishlists: download/parse (choosy_voltron, Aegis keep + trash) and matching wired into the dupe ranking via the Bungie manifest's perk name→hash map
- ✅ M4 — Armor 3.0 archetype scoring (`vault-cleaner armor`; config-driven build weights, set-bonus favoring, top-N + floor)
- ✅ M5 — polish: ghost cleanup pass (`vault-cleaner ghosts` — junks every shell not equipped/locked/tagged/in a loadout) and the all-passes dry-run summary (`vault-cleaner report`)
- ✅ M6 — armor dupes: exact-dupe pass, review-only close-dupe pass, and the last-of-archetype score guard
- 🚧 M7 — review UI: reusable report snapshot ✅, persistent vetoes + reviewed export (`vault-cleaner review`) ✅, static HTML review UI (`vault-cleaner review-html`) ✅
- 🚧 M8 — local review server: authenticated loopback server with browser CSV uploads and a read-only report view; verdict/finalization APIs exist, while their browser controls remain follow-up work

See the [issue board](https://github.com/tonym999/vault-cleaner/issues) for
ticket-level detail.

## License

[MIT](LICENSE)
