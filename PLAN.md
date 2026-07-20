# Vault Cleaner — Initial Plan

A CLI tool that ingests DIM CSV exports, tags weapons and armor as keep/junk/infuse according to configurable rules, and writes a CSV that DIM can re-import. Mass deletion then happens in-game via a `tag:junk` search in DIM.

## Goals

- Cut vault clutter with no account access: no API keys, no OAuth, no credentials, no live inventory reads. Vault data enters only via DIM CSV exports. Unauthenticated static game-content downloads (wishlist files; the Bungie manifest's public item definitions, used for perk name→hash mapping) are permitted and cached locally: the first wishlist-enabled run needs network access to populate the caches, subsequent runs work offline, and `dupes --no-wishlists` is the zero-network fallback.
- Encode *my* rules: Armor 3.0 stat priorities (Melee-primary Titan builds first), wishlist-driven weapon judgement, dupe resolution.
- Every junk decision is explainable — the output includes a reason per item, and nothing is deleted by the tool itself. DIM import + in-game dismantle remain the manual confirmation steps.

## Non-goals (v1)

- No authenticated Bungie API access: no API keys, OAuth, or live inventory/account reads. (Unauthenticated static content — the public manifest definitions — is explicitly in scope; decided in PR #13.)
- No automatic deletion or item moves.
- No GUI — CLI first; a local web UI is a possible later phase.

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

Python 3.12, pandas for CSV handling, `tomllib` for config, `pytest` for tests. No other runtime dependencies for v1.

## Repo layout

```
vault-cleaner/
├── src/vault_cleaner/
│   ├── parse.py          # DIM CSV ingestion, header-name mapping
│   ├── wishlist.py       # download, cache, parse wishlist files
│   ├── rules/            # armor.py, weapons.py, dupes.py
│   ├── report.py         # output CSV + human-readable summary
│   └── cli.py
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

## Risks & mitigations

- **DIM CSV format drift** — header-name access, a schema-sanity check on load that fails loudly, fixture tests pinned to a real export.
- **Wishlist format edge cases** — the format is informal; parse defensively, log-and-skip malformed lines rather than crash.
- **Over-aggressive junking** — safety rails first, tool never deletes, dry-run mode default until `--write` is passed.
- **Stat column changes (Armor 3.0 naming)** — map stat names through one lookup table so a rename is a one-line fix.

## Later ideas (explicitly out of scope for now)

- Bungie API mode for live data (read-only).
- Streamlit/Flask review UI with per-item override before writing output.
- Generating a personal wishlist file from kept rolls (hosted as a public Gist for DIM to subscribe to).
