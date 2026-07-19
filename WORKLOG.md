# Worklog

Newest first. One entry per working session: what happened, decisions made,
surprises the next agent should know about.

## 2026-07-19 (M6, part 2) — armor close-dupe pass (#18)

- `rules/armor_close.py`: review-only — dominated (`armor-dominated by
  <id> (+N total)`) and similar (`armor-similar to <id>`), compared within
  Hash + Tier only. The measured collapse (#16): every vault legendary is
  in a manifest set and every set has exactly one hash per class×slot, so
  class+slot+tier+set-signature ⇔ Hash + Tier — no set table, no manifest,
  no network. A dominated pair is never also "similar" (either direction of
  domination excludes the pair); one note per piece, best partner
  (closest, then lowest id — order-independent, tested by CSV reversal).
- Caps in `[armor.close_dupes]` (`max_stat_delta = 5`, `max_total_delta =
  12`), validated non-negative-int with a named error on partial override.
  Measured bimodality means any cap 1–9/1–19 picks the same pairs today.
- Pipeline: rails → exact dupes → close dupes → score. **Deliberate
  consequence:** junk dropped 227 → 175 on the real vault, because ~52
  near-twin pieces the score pass used to junk now get a close-dupe
  review note instead — earlier passes win, and a near-dupe deserves
  human eyes over a blind score junk.
- Real vault: 124 close-dupe reviews (mostly "identical stats, tuning X
  vs Y" — the tuning-twin cluster measured in #16), 0 dominated (as
  measured: structurally impossible at tier 5's fixed 75 totals).
- Review follow-ups: `Tier` schema-required (the close pass groups on it —
  drift was a KeyError, now a SchemaError). Score pass no longer junks a
  piece cited as a close-pass dominator ("only kept pieces dominate" —
  under a strict-but-valid config the old code reviewed 6002 as "dominated
  by 6001" then junked 6001; similar partners never needed the shield
  because their notes are symmetric, so both sides are already decided or
  hard-protected).
- Round 2 (owner call, follows the #17 spiritless guard): the Spirit
  signature joined the close-pass compatibility bucket — two exotic class
  items with different Spirit combos are functionally different pieces
  (same rule as set bonuses), and a spiritless copy is an unknown roll,
  compared with nothing. Real vault: 124 → 115 close reviews; the 9
  removed notes were cross-spirit "similar" advice, i.e. misleading.

## 2026-07-19 (M6) — armor measurement spike + exact-dupe pass (#16, #17)

- **Spike first (#16), and it rewrote both designs** — full numbers in the
  issue comments. Highlights: the Perks columns are a masterwork-gated
  socket dump (unupgraded copies export almost nothing), so raw perk
  hashing is unusable; but Hash already implies the set perk — the
  manifest's DestinyEquipableItemSetDefinition has 56 sets × exactly one
  hash per class×slot, covering every legendary in the vault. Tuning Stat
  is roll identity, not socket state (present before anything is socketed;
  a socketed '+X/-Y' always matches it on legendaries; always empty on
  exotics — and one tier-5 legendary quirk-exports it empty). No tuning
  leak into base stats: every tier-5 piece totals exactly 75 base.
  Tertiary Stat/Archetype are derivable from base stats. Exotic class item
  Spirit perks are roll identity and visible on every copy.
- `rules/armor_dupes.py` (#17): fingerprint = Hash + 6 base stats +
  Tuning Stat + Seasonal Mod + Holofoil + Spirit signature. Survivor:
  hard > loadout > locked > masterwork > power, then lowest id — reversing
  the CSV changes nothing (tested). Loadout losers review-only (loadouts
  pin instance ids). Fingerprint + ranking columns are now
  schema-required; PLAN.md rules list amended (exact + close dupes).
- Armor pipeline is now rails → exact dupes → score via `_resolve_armor`
  (shared by `armor` and `report`); earlier passes win, one decision per
  item.
- Real vault: 7 exact-dupe rows — 1 junk, 1 loadout review (the rule fired
  on real data: an identical twin survives but the loser is in a loadout),
  5 exotic reviews. Small by design; the volume lives in the close-dupe
  pass (#18): dominated is structurally impossible within tier 5 (fixed 75
  totals) and "similar" is bimodal — 65 pairs differ only in Tuning Stat,
  then nothing until far-apart archetypes.
- Review follow-ups: Masterwork Tier / Power cells validated
  empty-or-digits at load (to_int would coerce garbage to 0 and silently
  flip a survivor; strict `\d+` would repeat the ghost-pass mistake — the
  measured export is all digits, but empty legitimately means
  unmasterworked). `Perks 0` is schema-required, so the Spirit identity source
  can't vanish silently; and (owner call, round 2) the belt-and-braces
  guard is in too — an exotic class item exporting no Spirit perks is an
  unknown roll and is never grouped. Round 3 closed the guard's own gap:
  a complete roll is exactly two Spirits (measured, 38/38 copies), so a
  one-Spirit signature is truncated identity — two rolls sharing their
  first Spirit must not merge — and anything shorter than
  `SPIRIT_ROLL_SIZE` is now treated as unknown. The guards only fire on
  data we haven't seen — better silent than wrong. Ordinary exotics (no
  spirits by design) still group normally.

## 2026-07-19 (wrap-up) — v1 chores (#21)

- AGENTS.md gotchas absorbed the durable worklog lessons (empty ghost rank
  columns, fixed Armor 3.0 spikes, manifest name→hash, stacked hashtags,
  csv CRLF, build/ artifacts) so future agents get them up front.
- ruff added to CI (one finding: unused import, autofixed).
- Older fixtures (weapons/ghosts/weapons_dupes) normalized to LF.
- pandas pinned `>=3.0,<4` — the venv and CI actually run pandas 3.0.3;
  the old `>=2.0` floor advertised an untested major version.
- After merge: tag v0.1.0 on main — all five milestones + full board done.

## 2026-07-19 (late) — MIT license (#10, PR #20)

- **Owner decision: MIT.** LICENSE file (copyright Tony M), PEP 639
  metadata in pyproject (`license = "MIT"`, `license-files`, setuptools
  ≥77.0.3), README section. All five PLAN.md milestones plus the board
  are now complete; v1 wrap-up chores tracked in #21.
- Review note: kept the README heading "License" (en-US) — repo prose
  follows ecosystem convention and DIM's own en-US terms; an en-GB sweep
  would belong in #21 if ever wanted.

## 2026-07-19 (evening) — M5: dry-run summary report (#9)

- `vault-cleaner report`: runs weapons (wishlist-aware), armor, and ghost
  passes dry, prints "would junk N item(s) and flag M for review" grouped
  by action + reason with per-item lines beneath (junk groups first,
  largest first). `--write` emits one combined import CSV. Missing exports
  are skipped with a warning; item sets are disjoint across passes so
  concatenation is safe.
- `report.reason_slug` parses the reason out of the `#vc-` hashtags —
  the notes remain the single source of truth for reasons.
- `_resolve_weapons` helper extracted so `dupes` and `report` share the
  wishlist/manifest setup.
- Real vault: 430 junk + 135 review across 1,580 items.
- PLAN.md's `--profile pvp|pve` stretch idea intentionally not done —
  file a ticket if wanted.

## 2026-07-19 (later) — Ghost pass redesigned: protection-only (#8, PR #15)

- **Owner decision during review: no ranking at all.** The ranking design
  below went through two review rounds (empty rank columns → tie-breaks →
  determinism) before the honest conclusion: ghosts carry no quality
  signal, and "top N" was an arbitrary policy wearing a ranking costume.
  Final policy: keep only shells that are equipped, **locked (the lock IS
  the keep signal for ghosts — no #vc-review)**, tagged
  favorite/keep/archive, or **referenced by a saved DIM loadout**
  (`Loadouts` column, now schema-required); junk everything else as
  `#vc-junk: ghost-unprotected-surplus`. Rarity still irrelevant.
  Rationale: mods move freely, Collections reacquires dismantled shells,
  and dry-run + DIM review + in-game dismantle remain the gates.
- Removed: `ghosts.keep_top_n`, rank-column schema/validation, tie-breaks.
  Ghosts take no config — lock/tag shells in DIM to keep them.
- Real vault: 29 shells → 17 junk, 12 protected.

## 2026-07-19 — Ghost cleanup pass (#8) — superseded, see above

- `rules/ghosts.py` + `vault-cleaner ghosts`. **Measured data reshaped the
  ticket sketch:** zero duplicate hashes exist, ghost mods move freely
  between shells (the mod carries the utility), and 28/29 shells are
  Exotic *rarity* — cosmetic for ghosts. So: rank all shells by Energy
  Capacity then Masterwork Tier, keep top `ghosts.keep_top_n` (default 6),
  junk the surplus with rank in the note.
- **Deliberate rails deviation:** exotic rarity is NOT a soft rail for
  ghosts (it would flag everything and clean nothing). Locked still
  reviews — checked directly because `rails.protection` reports exotic
  before locked. Tags/equipped hard-protect as usual.
- Real vault: 29 shells → 15 junk, 5 review, top 6 + 3 protected kept.
- New fixtures now written LF-only (csv module defaults to CRLF).
- Review follow-up + finding: **current DIM exports leave Energy Capacity
  and Masterwork Tier EMPTY on every shell** (retired system) — ranking
  ties at (0,0) and falls back to export order. Rank columns are now
  schema-required, cells validated empty-or-digits (strict `\d+` à la
  armor would reject the real export!), and notes say "no
  energy/masterwork data" instead of fabricating "energy 0" rankings.

## 2026-07-18 (late night) — M4: armor loader + archetype scorer (#6, #7)

- `load_armor` on the shared loader; **`ARMOR_STATS` in parse.py is THE
  stat lookup table** (canonical name → `(Base)` column) — an Armor 3.0
  rename is a one-line fix there. Weapons schema now also requires `Ammo`
  because an armor export otherwise satisfies it silently.
- `rules/armor.py`: score every legendary against each configured
  archetype, take the best; favored-set perks (matched by name in Perks
  columns, e.g. "Erebos Glance") add `set_bonus`. Keep top-N per slot per
  class OR anything ≥ floor; junk only both-outside, with reason
  (`#vc-junk: armor-score 56 < floor 65 (best: melee_primary, rank 26/50
  titan gauntlets)`). Rails as usual; exotics never scored.
- **Design finding (measured, not assumed):** every Armor 3.0 tier-5
  piece has the same fixed 30+25 stat spike and ~75 base total, so the
  planned "generic spike profile" scores everything identically (165) and
  discriminates nothing. Dropped from defaults (mechanism `top_stats = N`
  remains for legacy armor); scoring is entirely build-alignment weights.
  Scores are normalized to the Total (Base) scale.
- Real vault: 872 pieces, 559 legendaries scored → 227 junk, 38 review.

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
- Review follow-ups: **PLAN.md amended (user-approved)** — the no-API rule
  now precisely bans authenticated access (keys/OAuth/live inventory)
  while permitting unauthenticated static content like the manifest.
  Keep-over-trash conflicts are counted and reported by the CLI (15 in
  the real vault). Cache validation checks every name→hash entry. The
  unwritable-cache test monkeypatches the write instead of chmod (which
  silently doesn't block writes on Windows-backed mounts — it failed on
  the user's WSL setup while passing in CI).

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
