# Vault Cleaner — Initial Plan

A CLI tool that ingests DIM CSV exports, tags weapons and armor as keep/junk/infuse according to configurable rules, and writes a CSV that DIM can re-import. Mass deletion then happens in-game via a `tag:junk` search in DIM.

## Goals

- Cut vault clutter with no account access: no API keys, no OAuth, no credentials, no live inventory reads. Vault data enters only via DIM CSV exports. Unauthenticated static game-content downloads (wishlist files; the Bungie manifest's public item definitions, used for perk name→hash mapping) are permitted and cached locally: the first wishlist-enabled run needs network access to populate the caches, subsequent runs work offline, and `dupes --no-wishlists` is the zero-network fallback.
- Encode *my* rules: Armor 3.0 stat priorities (Melee-primary Titan builds first), wishlist-driven weapon judgement, dupe resolution.
- Every junk decision is explainable — the output includes a reason per item, and nothing is deleted by the tool itself. DIM import + in-game dismantle remain the manual confirmation steps.

## Non-goals (v1)

- No authenticated Bungie API access: no API keys, OAuth, or live inventory/account reads. (Unauthenticated static content — the public manifest definitions — is explicitly in scope; decided in PR #13.)
- No automatic deletion or item moves.
- No hosted, multi-user, or packaged desktop GUI. A loopback-only local web UI is in scope from M8; it binds `127.0.0.1`, is started and stopped by the user, and serves one authenticated session.

## Architecture

```
DIM Organizer                    vault-cleaner                     DIM Settings
─────────────                    ─────────────                     ────────────
export CSVs ──► data/in/ ──► parse ──► rules engine ──► data/out/ ──► "Import tags/
(weapons,                      │            │                          notes from CSV"
 armor)                        │            ├─ armor scorer
                               │            ├─ wishlist matcher
                     wishlists/│            ├─ dupe resolver
                     (voltron, └────────────┴─ report writer
                      aegis, cached)
```

- **Input:** DIM weapon + armor CSV exports. Access columns **by header name, never position** — DIM's format changes between releases.
- **Output:** CSV with `Id`, `Hash`, `Tag`, `Notes` columns (DIM ignores extras). `Notes` carries the reason string (e.g. `#vc-junk: dupe-lower, no wishlist match`), which doubles as a searchable hashtag in DIM.
- **Wishlists:** download and cache `choosy_voltron.txt` (keep + thumbs-down rolls) and the Aegis endgame/trash lists. Parse `dimwishlist:item=HASH&perks=...` lines; negative item hash prefix = trash entry.

**M7 boundary:** `pipeline.py` owns ordered rule execution; `report_run.py`
loads available exports into a reusable structured result and produces a
versioned, JSON-safe snapshot. The CLI and the local review server are
presentation adapters over that API. Snapshot schema and ruleset versions advance independently, and source
paths are reduced to non-sensitive basenames within snapshots. Python remains
the only authoritative rules engine and DIM CSV writer.

## Rules engine

Order matters — earlier rules win:

1. **Safety rails — two tiers.** *Hard* (tool never touches them): anything already tagged favorite/keep/archive in DIM, equipped items, crafted/enhanced weapons above a level threshold. *Soft* (never tagged junk, but a losing dupe gets a `#vc-review` note recommending manual review, existing tag preserved): exotics, locked items.
2. **Weapons — wishlist pass:** trash-list or thumbs-down match → candidate junk. Keep-roll match → protected from junk (but not blanket "keep" — dupes among matched rolls still resolve to best copy).
3. **Weapons — dupe pass:** group by item Hash (never name — reissues collide); rank copies (wishlist match > gear tier > masterwork tier > crafted level > stat total); best copy survives, rest → junk. Ties are still junked (keep one of N identical rolls) but noted as `dupe-tie` rather than `dupe-lower`; soft-protected copies get `#vc-review` notes instead of tags.
4. **Armor — exact-dupe pass (M6):** group by fingerprint (Hash + six base stats + Tuning Stat + Seasonal Mod + Holofoil + exotic Spirit signature — all roll identity, measured in #16); one deterministic survivor per group (hard-protected > loadout-referenced > locked > masterwork > power, then lowest id — never CSV order), rest → junk. Loadout-referenced losers are review-only: DIM loadouts pin instance ids, so junking a twin breaks the loadout.
5. **Armor — close-dupe pass (M6, review-only):** flag dominated and near-identical pieces among the survivors for manual review; never tags junk.
6. **Armor — score pass:** score each legendary piece against configurable stat archetypes (v1 ships with Melee-primary and a generic spike profile). Keep top-N per slot per class; set-bonus armor gets a configurable score bonus so mediocre-stat pieces from active sets survive. Below floor → junk — except the vault's last kept copy of a (set-piece, archetype) combination, which is demoted to review instead (#30): scoring alone must never foreclose a set/build option.
7. **Everything unmatched:** left untagged — the tool only tags what it has a reason for.

All thresholds (top-N, score floors, archetype weights, set bonuses to favor) live in a single `config.toml`.

## Tech stack

Python 3.12, pandas for CSV handling, `tomllib` for config, `pytest` for tests. Runtime dependencies are pandas and (from M8, added by the server ticket) Flask 3.1 — exactly; anything further needs a ticket amending this line. Dev/test tooling (pytest, ruff, Playwright) stays out of the runtime set.

## Repo layout

```
vault-cleaner/
├── src/vault_cleaner/
│   ├── parse.py          # DIM CSV ingestion, header-name mapping
│   ├── wishlist.py       # download, cache, parse wishlist files
│   ├── rules/            # one module per ordered rule pass
│   ├── pipeline.py       # reusable ordered weapons/armor pipelines
│   ├── report_run.py     # all-passes result + versioned snapshot/fingerprint
│   ├── report.py         # output CSV + human-readable summary
│   └── cli.py            # presentation and explicit --write boundary
├── wishlists/            # cached downloads (gitignored or committed — TBD)
├── data/                 # in/ and out/ — gitignored, personal vault data
├── config.toml
├── tests/                # fixture CSVs with fake items
└── PLAN.md               # this file
```

Public repo; `data/` gitignored from the first commit.

## Milestones

1. **M1 — Round trip:** parse DIM CSVs, write a valid tags/notes CSV, verify DIM imports it (tag one sacrificial item). Proves the pipeline before any rules exist.
2. **M2 — Weapon dupes:** dupe resolver + safety rails. First real cleanup value.
3. **M3 — Wishlists:** choosy_voltron + Aegis download/parse/match, integrated with dupe ranking.
4. **M4 — Armor scoring:** Armor 3.0 archetype scorer, set-bonus handling, config-driven thresholds.
5. **M5 — Polish:** dry-run summary report ("would junk 214 items: …"), per-item reasons, maybe a `--profile pvp|pve` switch.
6. **M6 — Armor dupes:** measured exact-dupe cleanup, close-dupe review, and last-of-archetype score guard.
7. **M7 — Review UI:** reusable report snapshot → persistent vetoes/review manifest → self-contained static HTML review.
8. **M8 — Local review server:** loopback-only authenticated HTTP server (Flask 3.1); the browser uploads exports and downloads the reviewed CSV, so no input/output filesystem paths are required. Python owns rules, validation, persistence, and CSV generation; the page renders server data and collects verdicts. With the server-only review path and static-page cleanup complete, bounded armor threshold what-if variants are produced in Python as an M8 follow-up.

### M8 schema-version-1 session states

The local review server's schema-version-1 session envelope admits five
states: `idle` (no report), `exports-loaded` (a report with no session
verdicts), `reviewing` (a report with at least one verdict), `finalized` (the
#67-owned durable finalize state), and terminal `closed` (shutdown has cleared
all live report, upload, snapshot, fingerprint, and verdict data). Revisions
remain monotonic across reset and shutdown; `closed` cannot be revived by any
mutation.

## Risks & mitigations

- **DIM CSV format drift** — header-name access, a schema-sanity check on load that fails loudly, fixture tests pinned to a real export.
- **Wishlist format edge cases** — the format is informal; parse defensively, log-and-skip malformed lines rather than crash.
- **Over-aggressive junking** — safety rails first, tool never deletes, dry-run mode default until `--write` is passed.
- **Stat column changes (Armor 3.0 naming)** — map stat names through one lookup table so a rename is a one-line fix.
- **The review server creates a new local network attack surface** — constrain it deliberately: loopback-only binding, authenticated session bootstrap, exact `Host` validation, same-origin enforcement for state-changing requests, no-store/no-referrer responses, strict and bounded upload validation, no request-supplied filesystem paths, and cleanup of session state and temporary files. Nothing is intentionally exposed off-machine, but this is a narrower risk than "no network code", not an unchanged posture.
- **The browser/server boundary still needs a contract** — the server removes the duplicated manifest parser, but upload, report, verdict, session, and download schemas remain cross-runtime boundaries. Specify them before implementation and bind mutations to the exact report revision/fingerprint.
- **Two interactive review surfaces would recreate the maintenance problem** — the static review page (never released; decided on #48) and its browser-side validator/parity suite were retired after the server UI proved parity; `serve` is the sole browser workflow.

## Later ideas (explicitly out of scope for now)

- Bungie API mode for live data (read-only).
- Generating a personal wishlist file from kept rolls (hosted as a public Gist for DIM to subscribe to).
