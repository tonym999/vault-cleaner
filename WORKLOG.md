# Worklog

Newest first. One entry per working session: what happened, decisions made,
surprises the next agent should know about.

## 2026-07-18 (night) — M3 complete: wishlist matching in the rules (#5)

- **Perk name→hash resolved via the Bungie manifest** (`manifest.py`):
  DestinyInventoryItemDefinition is public static JSON (no key/OAuth — still
  inside the no-API-integration rule, which is about live inventory).
  ~200MB one-time download reduced to a ~1MB name→hashes cache in
  `data/cache/`; on staleness only the small index is re-checked, the big
  file re-fetched only when Bungie's manifest *version* changes. One name
  maps to several hashes (base + enhanced variants) — kept deliberately so
  wishlist entries citing either variant match.
- `rules/weapons.py`: full pipeline rails → wishlist pass → dupes. Trash
  match (whole-item or roll ⊆ item perks) → junk / review-if-soft, unless a
  keep roll also matches. Keep matches feed `dupes.resolve` as the
  top-ranked key (match count). Perk names from `Perks N` columns, trailing
  `*` (DIM's selected marker) stripped.
- `dupes` CLI now runs the wishlist pass by default; `--no-wishlists`
  opts out; wishlist/manifest failures error cleanly with that hint.
- Real vault: 679 weapons → 186 junk, 97 review; 23 wishlist-trash calls.

## 2026-07-18 (evening) — M3 part 1: wishlist download/cache/parse (#3, #4)

- `wishlist.py`: `fetch` (cache in `wishlists/`, re-download after
  `wishlists.max_age_days`, stale-cache fallback with warning when offline,
  `WishlistError` only when there's no copy at all) and `parse_wishlist`
  (defensive: non-`dimwishlist:` lines ignored, malformed entries counted
  in `.skipped`, DIM's `-69420` wildcard entries counted but unsupported).
- Sources in `config.toml`: 48klocs choosy_voltron (keep + trash entries)
  and Nitaraku/dim-wishlists aegis_wishlist.txt (auto-generated from the
  Aegis PvE tierlist, actively updated). Real parse: 252k keep rolls + 53
  trash entries (choosy), 5k keep (aegis).
- **Decision:** `wishlists/` stays gitignored — choosy_voltron alone is
  26MB of refreshable third-party content.
- Review follow-up: added the Aegis **trash** list (Ciceron14/
  dim-extra-wishlists, 291 whole-item entries for D-tier-or-lower; updates
  less often than the keep lists). That list writes whole-item trash as
  `&perks=` (present, empty) — the parser now accepts that deliberately
  while still rejecting separator-only `perks=,` as malformed. Also:
  digit runs bounded to uint32 length (huge numbers can't crash `int()`),
  and malformed URLs fall back to stale cache like any download failure.
- **Open question for #5:** wishlist perks are hashes; the DIM export has
  perk *names*. Matching needs a name→hash bridge (or a hash-bearing
  export) — investigate before building the matcher.

## 2026-07-18 (later) — M2: safety rails + dupe resolver

- **Design change from the plan (user decision):** rails are now two-tier.
  Hard (never touched): favorite/keep/archive tags, equipped, crafted ≥
  `rails.crafted_level_protect` (config, default 10). Soft (never tagged
  junk, `#vc-review` note when outranked as a dupe, existing tag/notes
  preserved): **locked and exotic items** — the user wanted recommendations
  on those rather than blanket protection. PLAN.md rule 1 updated.
- `rules/rails.py` (protection classifier), `rules/dupes.py` (group by
  Hash, rank: gear Tier > masterwork > crafted level > stat total; ranking
  takes a pluggable `wishlist_key` for M3 to prepend), `config.py`
  (tomllib + defaults), `vault-cleaner dupes` CLI (dry-run default).
- Output rows append our hashtag to *existing* DIM notes rather than
  replacing them; review rows carry the item's existing tag so import is a
  tag no-op.
- Real-vault dry run: 684 weapons → 184 junk, 89 review.

## 2026-07-18 — Repo bootstrap, M1, ghosts, published

- Initialized repo from PLAN.md; `data/` gitignored from the first commit.
  Layout: `src/vault_cleaner/` (parse, report, cli, rules/), `tests/`,
  `wishlists/`, `data/in|out/`, `config.toml` stub.
- **M1 done.** `vault-cleaner roundtrip` parses a DIM export by header name
  (loud `SchemaError` on drift), tags one sacrificial item, writes a DIM
  `Id/Hash/Tag/Notes` import CSV. Dry-run default, `--write` to emit.
  Verified against a real export (684 weapons). **Round trip confirmed in
  DIM**: imported CSV set tag=junk + note on the target item (screenshot
  check by user). M1 fully done.
- **Ghost support added** (`--kind ghosts`). Ghost exports lack the `Type`
  column, which forced per-kind schema sets — see AGENTS.md gotchas.
- **Finding:** "A Good Shout" exists under two different item hashes
  (seasonal reissue). Dupe resolution (M2) must group by `Hash`, not name.
- Published to https://github.com/tonym999/vault-cleaner (public). Verified
  no vault data anywhere in git history first.
- Decisions: pandas as the only runtime dep; fixtures pinned to real export
  headers with fake rows; `wishlists/` gitignored for now (PLAN.md marks it
  TBD).
