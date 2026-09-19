# Wishlist Evidence Model & Aegis Source Strategy

This document specifies the per-entry wishlist evidence model, DIM scoping rules, curation families, uncertainty invariants, and the selected Aegis source strategy implemented in issue #158 (Child 3 of #140).

## 1. Objective and scope boundary

This is a **data-model and observability ticket, not a policy ticket**. No rule consumes the new evidence in this change. For identical wishlist bytes, weapon decisions, Notes clauses, and conflict counts stay byte-identical to `main`.

The only decision-affecting change in this ticket is the `config.toml` source swap (adopting Ciceron's major-perks S/A keep list and removing Nitaraku), which deliberately changes the input wishlist bytes.

### Fingerprint boundary (Child 5 handoff)

`family`, `activity`, and `tier_format` are not consumed by any rule in this ticket. They are intentionally **excluded** from `WishlistSourceIdentity`, the fingerprint payload, and the report snapshot. Child 5 owns adding them to the fingerprinted identity when a rule first consumes them.

## 2. Evidence model and alignment invariant

Every parsed wishlist entry records its full provenance and associated list metadata in `WishlistEntry`:

```python
@dataclass(frozen=True, slots=True)
class WishlistEntry:
    source: str
    family: str
    polarity: str                 # "keep" | "trash"
    item_hash: int
    perks: frozenset[int]         # exact identity with the roll in keep/trash
    notes: str | None             # effective notes, stripped; None if absent or empty
    tags: tuple[str, ...]         # casefolded tokens in file order, duplicates removed
    section_title: str | None     # most recent title: text, stripped
    activities: frozenset[str]    # subset of {"pve", "pvp"}
    activity_basis: str           # "tags" | "source" | "unknown"
    tier: str | None              # "S".."F"
    tier_status: str              # "parsed" | "unrecognized" | "not-declared"
```

### Alignment invariant

When evidence is enabled, per-entry evidence is mechanically aligned with the existing `keep` and `trash` roll lists:

- `len(keep_evidence[h]) == len(keep[h])` and `keep_evidence[h][i].perks is keep[h][i]` for every item hash `h` and index `i`.
- `len(trash_evidence[h]) == len(trash[h])` and `trash_evidence[h][i].perks is trash[h][i]` for every item hash `h` and index `i`.
- `Wishlist.merge` preserves this 1:1 alignment in lock-step across sources. Merging an evidence-bearing wishlist with an evidence-free wishlist is forbidden and raises `ValueError`.

### Evidence-off path

Evidence parsing is opt-in (`evidence=False` by default). When disabled, no notes, tags, section titles, or entry objects are allocated, and `ignored_note_segments` remains `0`. The report/serve pipeline retains its baseline performance and memory footprint.

## 3. DIM note and tag scoping contract

Scoping rules mirror [DestinyItemManager/DIM](https://github.com/DestinyItemManager/DIM/blob/master/src/app/wishlists/wishlist-file.ts) (`src/app/wishlists/wishlist-file.ts`):

1. **Block notes:** A line starting `//notes:` sets `block_notes`.
2. **Resetting block notes:** An empty line (after stripping whitespace) or any other comment line starting with `//` resets `block_notes` to `None`.
3. **Titles and descriptions:** A line matching `^@?title:(.+)$` updates the current section title (and the first sets `declared_title`). A line matching `^@?description:(.+)$` sets `declared_description`. **Neither title nor description resets block notes.**
4. **Tail precedence:** On a `dimwishlist:` line, a `#notes:` tail takes precedence over `block_notes` **only if its text before the first `|` is longer than one character**. DIM cuts at the pipe first (`(?<wishListNotes>[^|]*)`) before testing length (`length > 1`). For example, `#notes:x|tags:pve` under a block note has pre-pipe text `x` (length 1), so the block note wins and the discarded tail's `tags:pve` is not read. If the pre-pipe text has length > 1, the tail wins and becomes the chosen raw source.
5. **Notes and tags splitting:**
   - The chosen raw source is split at the first `|`. The stripped left part is `notes` (`None` if empty).
   - Only the **first** segment following the first `|` can supply tags, and only if it matches `^\s*tags:([^|]*)$`. Tokens separated by commas or whitespace are casefolded and deduplicated in file order.
   - Any later segment (including repeated `|tags:` segments of perk hashes found in some files) or a non-tags first segment is ignored.
   - Entries whose effective notes carried an ignored pipe segment increment `Wishlist.ignored_note_segments`. The count is produced by the parser and never recomputed from raw text. Only the merged `Wishlist` sums it.

### Line-splitting contract (known difference from DIM)

- `parse_wishlist` splits text with Python's `str.splitlines()`. DIM splits only on `\n` (`fileText.split('\n')`).
- `str.splitlines()` also splits on `\r`, `\v` (`\x0b`), `\f` (`\x0c`), `\x1c`, `\x1d`, `\x1e`, U+0085, U+2028 and U+2029.
- **Effect on evidence:** a note containing one of those characters is cut short at it. Example: `//notes:a<U+2028>b` gives `notes == "a"`, where DIM would keep `a<U+2028>b`.
- Keep/trash matching (`keep`, `trash`, `skipped`, `wildcards`) already used `str.splitlines()` before #158. This ticket does not change line splitting.
- This is a known difference from DIM, listed alongside the per-line whitespace stripping difference.

## 4. Activity basis and tier recognition

### Activity basis

Activities are derived using the strict precedence: `tags` → `source` → `unknown`:

1. If any tag token is `pve`, starts with `pve-`, or is `god-pve`, `pve` is derived.
2. If any tag token is `pvp`, starts with `pvp-`, or is `god-pvp`, `pvp` is derived.
3. If tags supply any activity, `activity_basis = "tags"`.
4. Otherwise, if the source config declares `activity = "pve"` or `"pvp"`, `activities = {spec.activity}` and `activity_basis = "source"`.
5. Otherwise, `activities = frozenset()` and `activity_basis = "unknown"`.

Tag evidence is per-entry. Tags never widen a source-declared scope silently (e.g. a `pvp` tag on a `pve` source records basis `tags`).

### Tier formats and recognition

Tier parsing is strictly opt-in per source to prevent false positives (e.g. Voltron notes containing "tier" in prose). Supported `tier_format` values:

- `"none"`: Tier is always `None` and `tier_status = "not-declared"`.
- `"ciceron-aegis"`: Recognized via polarity-specific regexes applied to stripped `notes`:
  - Keep entries: `^(?:\([^()]{1,40} version\) - )?Aegis Endgame ([SA]) Tier\.`
  - Trash entries: `^([DEF]) Tier\.`
  A match yields `tier_status = "parsed"`. Any non-match (including `notes is None`) yields `tier = None` and `tier_status = "unrecognized"`.

## 5. Curation families, uncertainty, and item evidence

### Uncertainty invariants

- **Absence is uncertainty, not trash evidence:** Uncovered families, weapons lacking keep or trash entries, stale sources, and unknown tiers represent lack of data, never a negative evaluation.
- **Families, not sources:** Multiple converters or variants derived from a single curator are **one curation family**. Supporting evidence collapses by family, never by source count.

### Item evidence queries

`item_evidence(evidence, item_hash, perk_hashes) -> ItemEvidence` provides:

- `keep_matches` / `trash_matches`: matching entries in source and file order. Keep requires `roll <= perk_hashes`; trash requires an empty roll (whole-item) or `roll <= perk_hashes`.
- `trash_kind`: `"whole-item"`, `"roll"`, or `None`, matching `rules.weapons.trash_match`.
- `keep_families` / `trash_families`: sorted unique families with a matching roll.
- `covered_families` / `uncovered_families`: families with any entry for `item_hash` (regardless of perks) vs configured families with no entry.
- `stale_sources`: sources covering `item_hash` whose fetch status is the stale fallback.
- `tiers_by_family`: parsed tiers per covered family in `S..F` order, or `()` if unknown.
- `conflicts`: structured conflicts in order:
  1. `keep-trash-cross-family`: some keep family differs from some trash family (`families` is the sorted union).
  2. `keep-trash-same-family`: family present in both `keep_families` and `trash_families`.
  3. `tier-disagreement`: covered family whose parsed tiers for the item contain more than one distinct value.

### Freshness fields

Fetch freshness tracks cache status and age per source:

- **`FetchResult.status`:** Tracks how the source data was obtained:
  - `"cache"` (CLI: `served from cache`): Cached file was within `max_age_days` and used without a network download attempt.
  - `"downloaded"` (CLI: `downloaded`): Successfully fetched over HTTP and written to cache.
  - `"stale-cache-after-failed-download"` (CLI: `stale cache used after failed download`): A download attempt failed (e.g. network error, timeout, HTTP failure) and an existing cached file was used as fallback. This includes when `--refresh` is passed and the download fails, even if the cached file is within `max_age_days`.
- **`cache_written_at`:** The cache file's `st_mtime` (Unix epoch seconds, float) read after the fetch completes, or `None` if that `stat()` call fails. When no usable cache exists and the download fails, `fetch_with_status` raises `WishlistError` and returns no `FetchResult`.
- **`max_age_days`:** Float from config (`[wishlists] max_age_days`, defaulting to 7.0). A cache counts as fresh when its age is less than `max_age_days × 86400` seconds; a non-positive `max_age_days` always attempts a download.
- **`ItemEvidence.stale_sources`:** Tuple of source names covering the item hash whose fetch status was `"stale-cache-after-failed-download"`. Surfaced as uncertainty rather than negative evidence.
- **`content_revision`:** Always `None`, because the selected source files declare no content revision or generated date.

## 6. Aegis source strategy and swap measurement

### Upstream evaluation and rationale

Aegis spreadsheet feeds were evaluated in #142 and re-measured on 2026-09-19 for #158:

| Source | Items | Parsed Tiers | Notes / Drawbacks |
|---|---|---|---|
| **Nitaraku** (`aegis_wishlist.txt`) | 968 | S 184, A 271, B 180, C 147, D 63, E 59, F 41, untiered 23 | Stale (2026-07-04 commit; 489 tier disagreements with current revision). Carries D/E/F keep entries on 115 Ciceron trash-listed items; a keep entry suppresses that trash verdict only when a weapon's perks match the roll. |
| **JxPv2** (`all.txt`) | 1,711 | S 201, A 333, B 296, C 252, D 178, E 95, F 58 | Automated every 8 h (declares spreadsheet revision 2026-08-19). No trash list; includes non-weapons. |
| **MrCharles** | — | 28 permutation files (443 KB – 36.7 MB) | Multi-perk permutation explosion (7–8 perk entries). Rejected on size and matching semantics. |
| **Ciceron keep** (`major-perks.txt`) | 522 | S 199, A 323 (100% recognized) | Agrees closely with current revision (506 shared S/A items with JxPv2). 2-perk major trait rolls. |
| **Ciceron trash** (`trashlist.txt`) | 286 | D 192, E 83, F 11 (100% recognized) | All whole-item trash entries. Same converter/maintainer. |

**Decision:** Adopt Ciceron's `dim_aegis_endgame_major-perks.txt` (`aegis_keep`) and retain Ciceron's `dim_aegis_endgame-trashlist.txt` (`aegis_trash`) as a single `aegis-endgame` family. Remove Nitaraku (`aegis`).

> **Supersession note:** §6 item 2 of [aggressive-clearout-measurement.md](aggressive-clearout-measurement.md) previously recommended keeping Nitaraku; that recommendation is superseded by this single-converter Ciceron strategy.
>
> The cached file `wishlists/aegis.txt` is left on disk (the tool never deletes user-owned files) and may be removed by hand.

### Provenance and revision alignment

The two Ciceron sources share the same maintainer, converter, and curation family (`aegis-endgame`). Upstream file commits show:

- `dim_aegis_endgame-trashlist.txt`: commit `2de3403c8f` (2026-08-23T21:57:16Z)
- `dim_aegis_endgame_major-perks.txt`: commit `2d380bdd69` (2026-08-23T22:36:58Z)

**Revision alignment is not verified:** Neither file declares a content revision or generation date (reported as `None` / not declared). The files are fetched and cached independently, so one can be fresh while the other is stale (reflected on their separate `fetch:` CLI lines).

### Decision delta in both directions (re-measured on 2026-09-19)

The swap affects decisions in **both** directions. Re-measured on 2026-09-19 from public list bytes (counting item hashes, not vault rows):

```text
Trash items (Ciceron trash ∪ Voltron trash) with a Nitaraku keep roll: 164
Exposing (E1): ≥1 Nitaraku roll not subsumed by any remaining keep roll: 162
Exposing (E2): EVERY Nitaraku roll not subsumed by any remaining keep roll: 157
               Mixed (in E1 but not E2): 5
Exposing (E3): No remaining keep entry at all (Ciceron keep or Voltron): 34
Suppressing (S1): ≥1 new Ciceron keep roll not subsumed by any old keep roll: 1
```

The exposing figures nest ($E3 \subseteq E2 \subseteq E1$) and represent a range:

- **E1 = 162 (upper bound on potential exposure):** At least one Nitaraku roll loses guaranteed coverage (is not a superset of any remaining roll). A proposal *can* appear only if a weapon's other perks do not match a remaining roll.
- **E2 = 157:** Every Nitaraku roll loses guaranteed coverage. This is **not** certain loss: 123 of these 157 items still have keep entries in Voltron or Ciceron that may match a weapon's other perks.
- **E3 = 34 (lower bound; guaranteed loss of all keep protection):** No remaining configured source has any keep entry for the item. Any copy of these 34 items that matched a Nitaraku roll loses all keep protection.
- **S1 = 1 (upper bound on potential suppression):** Exactly one item hash is present on both Ciceron keep and trash lists. On this item, 5 of the 9 Ciceron keep rolls are not covered by any old keep roll. A copy of this item that was whole-item trash *can* become protected if it carries one of those 5 perk pairs and matched no old keep roll. This item is also a working example of a `keep-trash-same-family` conflict within the `aegis-endgame` family.
