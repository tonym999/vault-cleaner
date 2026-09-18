# Issue #158 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#158 — Child 3: wishlist evidence model, curation families, and Aegis source strategy`

**Milestone:** `None — deliberately unassigned; cross-cutting child of #140, consistent with #148 and #155`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** Google `gemini-3.8-flash`, native `thinking_level = high` (justified below)

**Plan baseline:** `main` at `032d78ad7541bb517de9176f19cc6b15f7f516da` (2026-09-15)

**Allocated implementation branch:** `feat/issue-158-wishlist-evidence`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Give every parsed wishlist entry its provenance and the metadata the lists
already carry. Make each source's curation family, freshness, coverage,
conflicts, and parse confidence explicit instead of discarded. Adopt one Aegis
source strategy.

This is a **data-model ticket, not a policy ticket**. No rule consumes the new
evidence. For identical wishlist bytes, every weapon decision, Notes clause,
`keep_trash_conflicts` count, snapshot, and fingerprint stays byte-identical to
`main`. The only intended decision-affecting change is the `config.toml` source
swap. It changes input bytes, which the existing wishlist fingerprint already
covers.

Invariants carried from #140 that this model must encode rather than weaken:

- Wishlist absence, missing coverage, a stale source, or an unknown tier is
  **uncertainty**, never trash evidence.
- Several conversions of the Aegis spreadsheet are **one curation family**. The
  model counts supporting *families*, never sources.
- Aegis ratings are PvE-endgame ratings. The model records activity with an
  explicit basis and never infers PvP value from PvE evidence or from absence.

## Context & Measurement

All commands ran from the repository root on 2026-09-15 on Linux, Python 3.14.4.
`$S` is a scratch directory outside the repository. Third-party list bytes were
downloaded to `$S` only and are not committed. Only aggregate counts appear here.

### Current parser and discard seams

- `LINE_RE` ([wishlist.py:29](../src/vault_cleaner/wishlist.py#L29)) matches
  `(?:#.*)?$` and discards any `#notes:` tail.
- `parse_wishlist` ([wishlist.py:69-100](../src/vault_cleaner/wishlist.py#L69-L100))
  skips every non-`dimwishlist:` line at
  [wishlist.py:73-74](../src/vault_cleaner/wishlist.py#L73-L74), including
  `//notes:` blocks and `title:` lines.
- `Wishlist.merge` ([wishlist.py:51-57](../src/vault_cleaner/wishlist.py#L51-L57))
  folds all sources into one `keep` and one `trash` map, which destroys
  attribution.
- `fetch` ([wishlist.py:129-157](../src/vault_cleaner/wishlist.py#L129-L157))
  returns only a `Path`. A stale-cache fallback is visible only as the stderr
  warning at [wishlist.py:152](../src/vault_cleaner/wishlist.py#L152).
- Rules consume only `keep`/`trash`:
  [weapons.py:46-56](../src/vault_cleaner/rules/weapons.py#L46-L56) (subset
  match; an empty trash set means the whole item) and
  [weapons.py:79](../src/vault_cleaner/rules/weapons.py#L79) (any keep match
  suppresses trash).
- `pipeline.resolve_weapons` calls `load_all_with_sources`
  ([pipeline.py:146](../src/vault_cleaner/pipeline.py#L146)). Fingerprints cover
  each source as `(name, url, sha256)`
  ([pipeline.py:108-118](../src/vault_cleaner/pipeline.py#L108-L118),
  [report_run.py:237-256](../src/vault_cleaner/report_run.py#L237-L256)).
- `vault-cleaner wishlists` is
  [cli.py:532-567](../src/vault_cleaner/cli.py#L532-L567). No test currently
  asserts its output (`grep -rn "keep rolls across" tests` returns nothing).
- `load_config` ([config.py:127-146](../src/vault_cleaner/config.py#L127-L146))
  does not validate `[wishlists.sources]` at all. Tests build config dicts with
  plain string URLs (`tests/test_pipeline.py:22`, `tests/test_wishlist.py:196`,
  `tests/test_cli_serve.py:164`).

### DIM's own note-scoping contract (upstream source)

Retrieved 2026-09-15 with
`gh api repos/DestinyItemManager/DIM/contents/src/app/wishlists/wishlist-file.ts`:

- `//notes:` lines set `blockNotes`. **Empty lines and any other line starting
  `//` reset it.** `title:`/`description:` lines (optional leading `@`) do not
  reset it.
- Block-note text is `^//notes:([^|]*)`, so it ends at the first `|`.
- On a `dimwishlist:` line, the `#notes:` tail is captured as `[^|]*` — cut at
  the first `|` — and only then wins over block notes if that cut text is longer
  than one character. The cut happens **before** the length test.
- The file's first `title:`/`description:` is the list info. Each roll also
  records the most recent `title`.

vault-cleaner strips each line before classifying it
([wishlist.py:72](../src/vault_cleaner/wishlist.py#L72)), so a whitespace-only
line counts as empty. That is the one intentional deviation from DIM's
unstripped `split('\n')`. Keep it.

### Measured note/tag/tier forms (local cache, byte-identical to upstream where re-downloaded)

Scoping script (DIM rules above), run over `wishlists/*.txt` and the
downloaded candidate files:

```text
wishlists/aegis.txt          rolls 5022   block_only 5022   tail_only 0    both 0   no_notes 0     items 968
wishlists/aegis_trash.txt    rolls 286    block_only 286    tail_only 0    both 0   no_notes 0     items 286
wishlists/choosy_voltron.txt rolls 255426 block_only 251463 tail_only 2456 both 270 no_notes 1237  items 1258  titles 286
$S/dim_aegis_endgame_major-perks.txt rolls 2610 block_only 2610 no_notes 0 items 522
```

- **Ciceron keep** (`dim_aegis_endgame_major-perks.txt`): 282 note blocks. 269
  start `Aegis Endgame S Tier.`/`Aegis Endgame A Tier.`. The other 13 start
  `(Pantheon version) - `, `(RotN version) - ` or `(BRAVE version) - ` before
  the same phrase. Every entry has exactly two perks.
- **Ciceron trash** (`dim_aegis_endgame-trashlist.txt`): 156 note blocks, all
  starting `D Tier.`, `E Tier.` or `F Tier.` (one is `D Tier. Weak Combo: …`).
  All 286 entries are whole-item (`&perks=`).
- **Nitaraku** (`aegis_wishlist.txt`): `[Tier: X, Rank: N]` blocks for all tiers
  S–F, plus 12 free-text blocks with no tier.
- **Choosy Voltron:** the tier regexes find nothing. However, 980 of its
  `//notes:` lines contain the word "tier" in prose. **A generic
  "tier-looking but unrecognized" heuristic would therefore raise 980 false
  uncertainty flags.** Tier parsing must be opt-in per source.
- **Voltron `|tags:`:** 175,332 of 255,426 entries carry a `|tags:` segment in
  their effective notes. Tokens are separated by commas and/or whitespace, in
  mixed case (`pve`, `PvE-God`, `god-pvp`, `m+kb`, `controller`, …).
  Classification by casefolded token (`pve`/`pvp`, `pve-*`/`pvp-*`,
  `god-pve`/`god-pvp`) gives PvE 118,435, PvP 56,024, both 806, neither 67,
  untagged 80,094. JxPv2 writes `| tags:` with a space.

### Aegis feed comparison (downloaded 2026-09-15)

Upstream latest repository commits (`gh api repos/<r>/commits?per_page=1`):
Nitaraku `2026-07-04` (`v26.7.4.1`); MrCharles `2026-08-15`; JxPv2
`2026-09-15` (automated every 8 h; header declares spreadsheet revision
`2026-08-19`); Voltron `2026-08-03`.

Ciceron is dated **per file**, because its latest repository commit
(`f6dd04da04`, 2026-08-27) touched only `README.md`. Measured 2026-09-18 with
`gh api -X GET repos/Ciceron14/dim-extra-wishlists/commits -f path=<file>`:

```text
dim_aegis_endgame-trashlist.txt     2026-08-23T21:57:16Z  2de3403c8f  "Endgame Analysis wishlists now support Barrels & Mags, and MW in notes"
dim_aegis_endgame_major-perks.txt   2026-08-23T22:36:58Z  2d380bdd69  "Filtered out Enhanced perks"
```

The two selected files were last changed in **different commits**. The keep
list was regenerated 40 minutes after the trash list, by a commit whose message
describes a converter change rather than a spreadsheet update. A shared
spreadsheet revision is therefore plausible, but it is an inference from commit
messages. It is **not verified**: neither file declares a revision, and nothing
the loader reads records one. (Corrected in plan review round 5: rounds 1–4
cited the README commit's 2026-08-27 as the files' date and claimed a shared
revision.)

Item-hash sets by parsed tier (coverage script over the downloaded files):

```text
nitaraku       items 968  S 184 A 271 B 180 C 147 D 63 E 59 F 41 untiered 23
jxpv2_all      items 1711 S 201 A 333 B 296 C 252 D 178 E 95 F 58 untiered 419 (exotic armor etc.), 0 trash entries
ciceron_major  items 522  S 199 A 323
ciceron_trash  items 286  D 192 E 83 F 11   (all whole-item)
S/A agreement: ciceron_major∩jx 506, jx-only 28, ciceron-only 16;  nitaraku∩jx 331, jx-only 203, nitaraku-only 124
tier disagreements nitaraku vs jx on shared items: 489
ciceron_trash items also listed as nitaraku keep, by nitaraku tier: S 1 A 2 B 17 C 29 D 30 E 45 F 40  (164 total)
ciceron_trash ∩ ciceron_major items: 1
ciceron_trash items also present in choosy_voltron: 202
```

Interpretation:

- Today, Nitaraku's all-tier keep rolls can suppress Ciceron's trash rating on
  the same weapon ([weapons.py:79](../src/vault_cleaner/rules/weapons.py#L79)).
  115 trash-listed items carry a D/E/F Nitaraku keep entry, so a low-tier
  "recommended roll" is protecting the same family's own trash verdict.
- Nitaraku is stale against the current spreadsheet revision. Ciceron's files
  (last changed 2026-08-23, after JxPv2's declared 2026-08-19 revision) agree
  closely with that revision: 506 shared S/A items, 16 and 28 unique. That
  agreement is the evidence Ciceron is current; no revision identity is
  recorded or verified.
- MrCharles: 28 permutation files of 443,282–36,724,539 bytes (#142 §5), with
  multi-perk permutation entries (the `MRS_PPC3` header shows 7–8 perk entries).
  Rejected on size and matching semantics.

**The swap changes decisions in both directions** (corrected in plan review
round 1). The item-level bounds below come from the public list bytes
(`parse_wishlist` over the cached Nitaraku, Voltron and Aegis trash files and
the downloaded Ciceron keep file). They count item hashes, not vault rows:

```text
trash items (Ciceron trash ∪ Voltron trash) with a Nitaraku keep roll:           164
exposing (E1): ≥1 Nitaraku roll not subsumed by any remaining keep roll           162
exposing (E2): EVERY Nitaraku roll not subsumed by any remaining keep roll        157
               mixed, i.e. in E1 but not E2                                         5
exposing (E3): no remaining keep entry at all (Ciceron keep or Voltron)            34
suppressing (S1): ≥1 new Ciceron keep roll not subsumed by any old keep roll        1
```

The three exposing predicates answer different questions and must not be
conflated (corrected in plan review round 2; round 1 printed E2's number
against E1's wording):

- **E1 = 162** — at least one Nitaraku roll loses *guaranteed* coverage. This
  is the **upper bound** on "a `wishlist-trash` proposal can appear".
- **E2 = 157** — every Nitaraku roll loses *guaranteed* coverage. This does
  **not** mean every weapon loses protection: the predicate only says no
  remaining keep roll is a subset of an individual Nitaraku roll, and a
  weapon's other perks can still satisfy a different remaining roll. For
  example, old roll `{11,22}`, remaining roll `{11,33}` and weapon perks
  `{11,22,33}` meet E2's predicate while both rolls match the weapon. 123 of
  the 157 E2 items still have keep entries in some source.
- **E3 = 34** — no configured source keeps any entry for the item at all. This
  is the only predicate that **guarantees no keep protection remains** for any
  copy of the item. It is the **lower bound**. (A copy only *loses* protection
  if it matched a Nitaraku roll before the swap; a copy that never matched had
  none to lose.)

The figures nest: E3 ⊆ E2 ⊆ E1. Report them as a range — 34 trash items are
left with no keep protection for any copy, and up to 162 can have copies whose
protection is lost — never as a single figure. `E1` is the headline upper bound the implementer re-measures;
all three are recorded with their predicates. (Corrected in plan review round
4: round 3 described E2 as guaranteed loss.)

- **Exposing:** for a weapon whose only keep match was a Nitaraku roll, a
  trash match stops being suppressed, so a `wishlist-trash` proposal can
  appear. That is why #155 is a blocking dependency.
- **Suppressing:** exactly one item hash is on both Ciceron's keep and trash
  lists. On it, 5 of the 9 Ciceron keep perk pairs are not covered by any
  current Nitaraku or Voltron keep roll. A copy carrying one of those pairs
  that is `junk` today (whole-item trash) **can** become keep-protected after
  the swap — only if no old keep roll already matched its other perks. Like E1
  and E2, S1 is an upper bound, not a guaranteed flip. (Corrected in plan
  review round 4, the same overstatement as E2.)
  No Voltron trash item overlaps Ciceron's keep list, so this is the only
  suppressing case. It is also a `keep-trash-same-family` conflict inside the
  chosen strategy, and the docs must use it as a worked example.
- "Not subsumed" means no remaining roll is a subset of the roll in question.
  That makes every subsumption-based figure (E1, E2, S1) an **upper bound**: a
  real weapon's other perks can still match a different roll. E3 does not use
  subsumption — it asks whether any keep entry remains at all — so it is the
  only guaranteed figure (no keep protection remains), a **lower bound**.

**NOT MEASURED:** the decision delta on the owner's real vault. No real export
accompanies this ticket and none is authorized.

### Parse cost baseline

```text
parse_wishlist(choosy_voltron.txt): 2.71 s, 3.66 s, 1.96 s (three runs); tracemalloc peak 144.4 MB
```

A per-entry evidence object for 255k Voltron entries is a real memory cost.
Evidence parsing is therefore **opt-in**. The report/serve pipeline keeps the
existing evidence-off path.

### Model verification and selection

Official Google documentation was rechecked on 2026-09-15:
[Gemini models](https://ai.google.dev/gemini-api/docs/models) lists
`gemini-3.8-flash` as **Stable**, and
[Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking) lists its
levels as `low`, `medium` (default), and `high`, with `minimal` unsupported.

`gemini-3.8-flash` at `thinking_level = high` **is suitable**, on the condition
that the scope stays as cut here. The work is a parser extension, frozen
dataclasses, config validation, one pure query function, CLI copy and tests.
Every format, regex, data shape, output string and invariant is pinned below,
and nothing touches rules, snapshots, the server or the UI. `high` is warranted
by the alignment invariant between evidence and match lists, DIM scoping edge
cases, strict config validation, and the decision-invariance proof. If
implementation reveals the need to change rule or snapshot seams, that is a
stop condition, not a reason to escalate the model in place.

The orchestrator must still verify that its runtime can instantiate this model
and effort. If it cannot, the orchestrator prepares the reusable prompt below
for manual cross-provider execution and records the actual
provider/model/effort.

## Dependencies and assumptions

- **#142** is closed and landed. Its §5 measurements still hold (the local cache
  bytes match upstream for `aegis.txt` and `aegis_trash.txt`: same sizes, same
  first lines). **§6 strategy item 2 is superseded by this plan.** It chose
  Nitaraku mainly because no new source entry was needed; this remeasurement
  shows Nitaraku is stale and conflicts with the family's own trash list. §6
  item 4 claimed tiers come from `#notes:` tokens; they are actually standalone
  `//notes:` blocks (§5 already corrected this). §12 row 3 recommended standard
  review, but #140's workflow rule requires independent adversarial review for
  parser changes, and this plan follows #140.
- **#155 (approval-only finalization) must be implemented and landed before
  this branch starts.** At planning time #155 is open, its plan is merged, and
  it has no implementation branch. Without it, newly surfaced wishlist-trash
  `junk` proposals would reach the finalized CSV unless someone vetoes them.
  The orchestrator verifies #155 is closed with its implementation on `main`
  before dispatch. Dependency links (`blocked by #142, #155`) are recorded on
  #158.
- #148 and #150 are landed and unaffected. #34 / Child 4 and Child 5 are future
  consumers of the model. This ticket adds no consumer.
- **Fingerprint boundary:** `family`, `activity`, and `tier_format` are not
  consumed by any rule in this ticket. They must **not** enter
  `WishlistSourceIdentity`, the fingerprint, or the snapshot here, because
  that would change the snapshot schema for no decision effect. **Child 5 owns
  adding them to the fingerprinted identity when a rule first consumes them.**
  Record this handoff note in `docs/wishlist-evidence.md`.
- The `[wishlists]` config table is an explicit exclusion from
  `_decision_config`
  ([report_run.py:173-224](../src/vault_cleaner/report_run.py#L173-L224)), and
  no key is added to `DEFAULTS`. The DEFAULTS coverage test in
  `tests/test_report_run.py:722` therefore needs no change.
- The renamed source `aegis_keep` gets a new cache file. `wishlists/aegis.txt`
  is left on disk untouched (the tool never deletes user-side files) and is
  documented as safe to remove by hand.
- Upstream bytes can drift before implementation. If a re-download shows that
  either Ciceron file's `ciceron-aegis` tier recognition covers less than 100%
  of its entries, that is a stop condition.

## Proposed Plan & Scope

### Source specifications and config validation

#### [MODIFY] [wishlist.py](../src/vault_cleaner/wishlist.py)

Add:

```python
FAMILY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ACTIVITIES = ("any", "pve", "pvp")
TIER_FORMATS = ("none", "ciceron-aegis")
SOURCE_KEYS = frozenset({"url", "family", "activity", "tier_format"})

class WishlistConfigError(ValueError): ...

@dataclass(frozen=True)
class WishlistSourceSpec:
    name: str
    url: str
    family: str
    activity: str      # one of ACTIVITIES
    tier_format: str   # one of TIER_FORMATS

def source_specs(sources: Mapping[str, object]) -> tuple[WishlistSourceSpec, ...]:
```

`source_specs` normalizes both forms, in config order:

- `name = "url"` becomes `family = name`, `activity = "any"`,
  `tier_format = "none"`. The family token is the source name as written, and
  the `FAMILY_RE` check does **not** apply to it, so existing configs such as
  `choosy_voltron = "…"` stay valid.
- A table form requires a non-empty string `url` and a string `family` matching
  `FAMILY_RE`. `activity` and `tier_format` are optional, with defaults `"any"`
  and `"none"`.
- Raise `WishlistConfigError` with the source name and offending key for: a
  non-mapping `sources`; a value that is neither a string nor a table; an
  unknown key (list the unknown keys sorted); a missing or empty `url`; a
  non-string value; a family that fails `FAMILY_RE`; an activity or
  tier_format outside its tuple; a bool masquerading as a string (not possible
  in TOML, but reject non-`str` generally).

#### [MODIFY] [config.py](../src/vault_cleaner/config.py#L127-L146)

In `load_config`, after `_validate_armor`, call
`source_specs(merged["wishlists"]["sources"])` and re-raise
`WishlistConfigError` as `ConfigError(f"{path}: [wishlists.sources] {e}")`.
Leave `cfg["wishlists"]["sources"]` **unmodified** (raw strings or tables).
Every consumer normalizes through `source_specs`, which is the single
implementation. `wishlist.py` must not import `config.py`, so no import cycle
is introduced.

#### [MODIFY] [wishlist.py](../src/vault_cleaner/wishlist.py#L160-L184) `load_all_with_sources`, [cli.py](../src/vault_cleaner/cli.py#L532-L567)

Wherever `sources.items()` is read as `name → url`
(`wishlist.load_all_with_sources`, `_cmd_wishlists`), iterate
`source_specs(...)` instead. Truthiness checks (`if not cfg["wishlists"]["sources"]`)
need no change (`pipeline.py` and `server/app.py` `prewarm` stay untouched). `WishlistSourceData` and `WishlistSourceIdentity` keep
exactly `(name, url, content)` and `(name, url, sha256)`.

### Evidence-bearing parse

#### [MODIFY] [wishlist.py](../src/vault_cleaner/wishlist.py#L24-L100)

1. **`LINE_RE`:** change only the tail group to a capture:
   `r"^dimwishlist:item=(-?\d{1,10})(?:&perks=([\d,]*))?(#.*)?$"`. The set of
   matching lines is unchanged. Add a test that every committed fixture line
   gets the same match/skip outcome before and after.

2. **Entry evidence:**

   ```python
   @dataclass(frozen=True, slots=True)
   class WishlistEntry:
       source: str
       family: str
       polarity: str                 # "keep" | "trash"
       item_hash: int
       perks: frozenset[int]         # the same object stored in keep/trash
       notes: str | None             # effective notes, stripped; None if absent or empty after strip
       tags: tuple[str, ...]         # casefolded tokens in file order, duplicates removed
       section_title: str | None     # most recent title: text, stripped
       activities: frozenset[str]    # subset of {"pve", "pvp"}
       activity_basis: str           # "tags" | "source" | "unknown"
       tier: str | None              # "S".."F"
       tier_status: str              # "parsed" | "unrecognized" | "not-declared"
   ```

3. **`Wishlist`** gains:
   - `family: str = ""`;
   - `keep_evidence: dict[int, list[WishlistEntry]] | None = None`;
   - `trash_evidence: dict[int, list[WishlistEntry]] | None = None`;
   - `section_titles: int = 0`;
   - `ignored_note_segments: int = 0` — entries whose effective notes carried an
     ignored pipe segment. Populated only when `evidence=True` and left `0`
     otherwise, so the evidence-off path does no segment work. Only the
     **merged** `Wishlist` sums it, exactly as it sums `skipped` and
     `wildcards`. Each `WishlistSourceStatus` copies the value from **its own
     source's** parsed `Wishlist`, never from the merged one, so a per-source
     CLI line never reports the aggregate. It is never recomputed from raw
     text;
   - `declared_title: str | None = None` and
     `declared_description: str | None = None` (first `title:`/`description:`,
     DIM `info` semantics).

   **Alignment invariant:** when evidence is present,
   `len(keep_evidence[h]) == len(keep[h])` and
   `keep_evidence[h][i].perks is keep[h][i]` for every `h` and `i`, and the
   same holds for trash. `merge` extends evidence lists in lock-step. If exactly
   one side has evidence, `merge` raises `ValueError`, because silently dropping
   evidence is forbidden. `merge` never changes a merged `Wishlist.family`.

4. **Signature:** `parse_wishlist(text, name="", *, spec: WishlistSourceSpec | None = None, evidence: bool = False) -> Wishlist`.
   With `evidence=False`, the loop body keeps its current behaviour and
   allocations. It must not build notes, tags or entries (the performance
   invariant). With `evidence=True`, `spec` is required (`ValueError` if it is
   missing), and the loop also tracks:
   - `block_notes`: set by a stripped line starting `//notes:`, to
     `line[len("//notes:"):]`. It is reset to `None` by an empty stripped line
     or any other line starting `//`.
   - `title`: set by `^@?title:(.+)$`. The first match also sets
     `declared_title`, and every match increments `section_titles`. `^@?description:(.+)$`
     sets `declared_description` once. Neither resets `block_notes`.
   - **Choose the raw notes source, cutting at the first `|` before the length
     test.** DIM captures `(?<wishListNotes>[^|]*)` and only then applies
     `length > 1`, so the note text is cut at the pipe first
     (`wishlist-file.ts`, retrieved 2026-09-15). Therefore: if `m.group(3)`
     starts with `#notes:`, let `tail = m.group(3)[len("#notes:"):]` and
     `tail_head = tail.split("|", 1)[0]`. The tail wins only if
     `len(tail_head) > 1`; the raw notes source is then the **whole** `tail`.
     Otherwise the source is the whole `block_notes` string, including its own
     pipe segments. Worked case: for `#notes:x|tags:pve` under a block note,
     `tail_head` is `x`, so the block note wins and its own segments supply the
     tags — the discarded tail's `tags:pve` must not be read. (Corrected in plan
     review round 2: testing the uncut tail would wrongly select it.)
   - Split the chosen raw source at the first `|`. The left part, stripped, is
     `notes` (`None` if empty). Split the remainder at `|` into segments. If the
     **first** segment matches `^\s*tags:([^|]*)$`, then
     `tags = unique(t.casefold() for t in re.split(r"[,\s]+", group) if t)`.
     Ignore every later segment. Measured: 8 Voltron note blocks (100 entries)
     carry a second `|tags:` segment of perk hashes, such as
     `…|tags: PvE, …|tags:1015611457 4082225868`, which must never become tag
     tokens. When the effective notes had an ignored segment (a first segment
     that isn't `tags:`, or any later segment), increment
     `Wishlist.ignored_note_segments` — see item 3. The count cannot live only
     on `WishlistSourceStatus`: nothing downstream of `parse_wishlist` can
     recompute it without duplicating this scoping logic (corrected in plan
     review round 2).
   - Activities from tags: a token contributes `pve` if it is `pve`, starts
     with `pve-`, or is `god-pve`, and `pvp` by the same rules. If any
     activity is derived, `activity_basis = "tags"`. Otherwise, if
     `spec.activity` is `pve` or `pvp`, then `activities = {spec.activity}` and
     `activity_basis = "source"`. Otherwise `activities = frozenset()` and
     `activity_basis = "unknown"`. Tags never widen a source-declared scope
     silently: a `pvp` tag on a `pve` source still yields basis `tags`, and
     the doc must say that tag evidence is per-entry.
   - Tier, only when `spec.tier_format == "ciceron-aegis"`, applied to the
     stripped `notes`:
     - keep polarity: `^(?:\([^()]{1,40} version\) - )?Aegis Endgame ([SA]) Tier\.`
     - trash polarity: `^([DEF]) Tier\.`

     A match gives `tier_status = "parsed"`. No match (including `notes is None`)
     gives `tier` `None` and `tier_status = "unrecognized"`. When
     `tier_format == "none"`, `tier_status = "not-declared"` always.
   - Reuse one `notes` string and one `tags` tuple object per distinct raw
     notes string: cache on the last raw string, since block notes repeat
     consecutively. This keeps memory bounded.

5. **Fetch status:**

   ```python
   @dataclass(frozen=True)
   class FetchResult:
       path: Path
       status: str                 # "cache" | "downloaded" | "stale-cache-after-failed-download"
       cache_written_at: float | None  # st_mtime after the call; None if stat fails
       error: str | None           # download error text for the stale fallback
   def fetch_with_status(name, url, cache_dir="wishlists", max_age_days=7, refresh=False) -> FetchResult
   ```

   `fetch` becomes `return fetch_with_status(...).path`. The existing stderr
   warning, `WishlistError` cases and every current `fetch` test keep passing
   unchanged. `load_all_with_sources` keeps calling module-level `fetch`,
   because `tests/test_pipeline.py:54` monkeypatches it.

6. **Evidence loader:**

   ```python
   @dataclass(frozen=True)
   class WishlistSourceStatus:
       spec: WishlistSourceSpec
       fetch: FetchResult
       max_age_days: float
       declared_title: str | None
       declared_description: str | None
       keep_entries: int
       keep_items: int
       trash_entries: int
       trash_items: int
       skipped: int
       wildcards: int
       noted_entries: int
       tagged_entries: int
       tier_counts: tuple[tuple[str, int], ...]   # S,A,B,C,D,E,F order, zero counts omitted
       unrecognized_tier_entries: int
       ignored_note_segment_entries: int  # this source's own Wishlist.ignored_note_segments, never the merged sum
       content_revision: None = None  # never declared by the selected files; always None in this ticket

   @dataclass(frozen=True)
   class WishlistEvidenceSet:
       merged: Wishlist                         # evidence-bearing
       sources: tuple[WishlistSourceData, ...]  # identical to load_all_with_sources
       statuses: tuple[WishlistSourceStatus, ...]

   def load_source_with_evidence(spec, cfg, refresh=False) -> tuple[Wishlist, WishlistSourceData, WishlistSourceStatus]
   def load_all_with_evidence(cfg, refresh=False) -> WishlistEvidenceSet
   ```

   Both use `fetch_with_status` and read bytes exactly as
   `load_all_with_sources` does
   ([wishlist.py:177-181](../src/vault_cleaner/wishlist.py#L177-L181)), with
   the same `WishlistError` text. Do **not** wire `load_all_with_evidence` into
   `pipeline.py`, `report_run.py` or the server.

### Item evidence query

#### [NEW] [wishlist_evidence.py](../src/vault_cleaner/wishlist_evidence.py)

A pure module. It imports `wishlist`, performs no I/O, and has no rule
imports.

```python
@dataclass(frozen=True)
class EvidenceConflict:
    kind: str                     # "keep-trash-cross-family" | "keep-trash-same-family" | "tier-disagreement"
    families: tuple[str, ...]     # sorted, unique
    tiers: tuple[str, ...] = ()   # sorted in S..F order; only for tier-disagreement

@dataclass(frozen=True)
class ItemEvidence:
    item_hash: int
    keep_matches: tuple[WishlistEntry, ...]   # source order, then file order
    trash_matches: tuple[WishlistEntry, ...]
    trash_kind: str | None                    # "whole-item" | "roll" | None — same result as weapons.trash_match
    keep_families: tuple[str, ...]            # sorted unique families with a keep match
    trash_families: tuple[str, ...]
    covered_families: tuple[str, ...]         # families with ANY entry for item_hash, regardless of perks
    uncovered_families: tuple[str, ...]       # configured families with no entry for item_hash
    stale_sources: tuple[str, ...]            # sources whose fetch status is the stale fallback AND that cover item_hash
    tiers_by_family: tuple[tuple[str, tuple[str, ...]], ...]  # every covered family; () means tier unknown
    conflicts: tuple[EvidenceConflict, ...]   # in the kind order above

def item_evidence(evidence: WishlistEvidenceSet, item_hash: int, perk_hashes: frozenset[int]) -> ItemEvidence
```

Semantics:

- Matching is copied exactly from
  [weapons.py:46-56](../src/vault_cleaner/rules/weapons.py#L46-L56). A keep
  match means `roll <= perk_hashes`. A trash match means an empty roll (whole
  item) or `roll <= perk_hashes`. `trash_kind` is `"whole-item"` if the first
  matching trash entry in list order is empty and `"roll"` otherwise, which
  mirrors `trash_match`'s first-hit loop. Do **not** import or modify
  `rules/weapons.py`. Parity is proven by test instead.
- `keep-trash-cross-family`: some keep family differs from some trash family.
  `families` is the sorted union of `keep_families` and `trash_families`.
- `keep-trash-same-family`: one per family present in both `keep_families` and
  `trash_families`, with `families = (family,)`.
- `tier-disagreement`: one per covered family whose parsed tiers (over **all**
  entries for `item_hash`, regardless of perks) contain more than one distinct
  value.
- Configured families come from `statuses` in config order, de-duplicated.
- The module docstring states: *absence, uncovered families, stale sources and
  unknown tiers are uncertainty, never trash evidence; supporting evidence is
  counted by family, never by source.*

### CLI surface

#### [MODIFY] [cli.py](../src/vault_cleaner/cli.py#L532-L567)

`_cmd_wishlists` iterates `source_specs`. Per source it calls
`load_source_with_evidence`, keeping the current fail-fast: print
`error: {e}` and return `1` on `WishlistError`. Output copy is exact. The first
line keeps today's **template and wording exactly**, and so does the `total:`
line. The interpolated source names and counts change with the configured
sources (for example `aegis` becomes `aegis_keep`). Four indented lines follow
the first line:

```text
{name}: {keep} keep rolls across {n} items, {trash} trash entries across {m} items{parse_suffix}
  family: {family}; activity: {activity}; tier format: {tier_format}
  fetch: {fetch_label}; cache written {when}
  declared title: {title}
  notes: {noted} of {entries} entries have notes, {tagged} have tags; tiers: {tiers}
```

- `parse_suffix` is today's existing malformed/wildcard suffix, built exactly as
  [cli.py:560-565](../src/vault_cleaner/cli.py#L560-L565) builds it now. It is
  unrelated to the ignored-note-segment suffix on the `notes:` line below.
- `fetch_label`: `served from cache` | `downloaded` |
  `stale cache used after failed download`.
- `when`: `%Y-%m-%dT%H:%M:%SZ` (UTC) from `cache_written_at`, then
  ` ({age:.1f} days old; refresh after {max_age_days:g} days)`, where `age` uses
  the current time. If `cache_written_at is None`: `unknown`.
- `title`: `declared_title` or `(none)`. Replace each character where
  `ch.isprintable()` is false with `\\u{ord:04x}`. If longer than 100
  characters, truncate to 100 and append `…`.
- `entries = keep + trash`. `tiers`: `not declared` when
  `tier_format == "none"`; otherwise space-joined `S=199 A=323` (zero counts
  omitted, or `none recognized`), then `, {k} unrecognized` only when `k > 0`.
Append `; {j} entries had ignored note segments` to the `notes:` line only when
`ignored_note_segment_entries > 0`.

After all sources and before the unchanged `total:` line:

```text
families: {family} = {source} + {source}; {family} = {source}
```

Families are sorted by name, sources within a family by name, and families
are separated by `; `. For the adopted config, the expected line is
`families: aegis-endgame = aegis_keep + aegis_trash; choosy-voltron = choosy_voltron`.

`--refresh` behaviour is unchanged. Add no new flags.

### Source strategy

#### [MODIFY] [config.toml](../config.toml#L64-L71)

Replace lines 64–71 with sub-tables (TOML 1.0 inline tables cannot span lines):

```toml
[wishlists.sources.choosy_voltron]
# Community god/recommended rolls + thumbs-down trash; per-entry |tags: carry PvE/PvP
url = "https://raw.githubusercontent.com/48klocs/dim-wish-list-sources/master/choosy_voltron.txt"
family = "choosy-voltron"
activity = "any"

[wishlists.sources.aegis_keep]
# Aegis PvE Endgame Analysis, S/A tier, major (trait) perks only — Ciceron conversion.
# One curation family with aegis_trash: same maintainer and converter.
# Revision alignment with aegis_trash is not verified: neither file declares a
# revision, and the two are fetched and cached independently.
url = "https://raw.githubusercontent.com/Ciceron14/dim-extra-wishlists/main/Aegis%20Spreadsheets%20Wishlists/Aegis%20Endgame%20Analysis/dim_aegis_endgame_major-perks.txt"
family = "aegis-endgame"
activity = "pve"
tier_format = "ciceron-aegis"

[wishlists.sources.aegis_trash]
# Aegis PvE Endgame Analysis trash list: whole-item entries for D tier or lower
url = "https://raw.githubusercontent.com/Ciceron14/dim-extra-wishlists/main/Aegis%20Spreadsheets%20Wishlists/Aegis%20Endgame%20Analysis/dim_aegis_endgame-trashlist.txt"
family = "aegis-endgame"
activity = "pve"
tier_format = "ciceron-aegis"
```

Keep the `[wishlists]` table and `max_age_days = 7` above it. Nitaraku's
`aegis` entry is removed.

### Documentation

#### [NEW] [wishlist-evidence.md](../docs/wishlist-evidence.md)

Cover:

- the entry model and alignment invariant;
- DIM scoping rules with a link to the upstream file;
- the activity basis rules;
- `tier_format` values and both regexes;
- item-evidence fields and the three conflict kinds;
- the uncertainty invariants;
- freshness fields, stating plainly that content revision and generated date
  are **not declared** by the selected files;
- the selected Aegis strategy and rejected alternatives, with the measured
  table from this plan;
- the decision change from the swap in **both** directions, giving E1, E2, E3
  and S1 with their exact predicates (never one number under another's
  wording), stated as a range — E3 no keep protection remains, E1 possible loss — and with S1
  described as possible rather than certain, re-measured by the implementer, and the one suppressing item
  described as a same-family conflict worked example (count only, no item name
  or hash);
- the provenance of the two Ciceron sources, stated no more strongly than the
  evidence: same maintainer, converter and curation family; **revision
  alignment not verified**, because neither file declares a revision; the two
  are fetched and cached independently, so one can be refreshed while the other
  is stale, which their separate `fetch:` lines show; and the per-file upstream
  dates from this plan (2026-08-23), not the repository's README commit date;
- that `wishlists/aegis.txt` may be removed by hand;
- the Child 5 fingerprint handoff note;
- that §6 item 2 of `aggressive-clearout-measurement.md` is superseded.

No third-party content beyond short format examples (at most one line per form).

#### [MODIFY] [aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md#strategy-recommendation)

Insert one line at the top of §6 "Strategy recommendation":
`> **Superseded in part (2026-09-15, #158):** item 2's Nitaraku recommendation is replaced by the single-converter Ciceron strategy in [wishlist-evidence.md](wishlist-evidence.md).`
Make no other edits to the historical report.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

Add a dated implementation entry: decisions, measured parse time/memory with
evidence on and off, the actual provider/model/effort, and any surprise.

### Tests

#### [NEW] [tests/fixtures/wishlist_evidence.txt](../tests/fixtures/wishlist_evidence.txt)

Synthetic only (fake hashes, fake prose). Write it with LF endings and no
trailing whitespace. It must include:

- a `title:`, then a `description:`, then a second `title:` section;
- a block note with `|tags:PvE, controller` applying to two entries;
- a blank-line reset followed by an un-noted entry;
- a `// comment` reset;
- a `#notes:` tail overriding a block note;
- a `#notes:x` tail (one character, which falls back to block notes);
- a `#notes:x|tags:pve` tail under a block note carrying its own `|tags:`: the
  pre-pipe tail is one character, so the block note wins and the tail's
  `tags:pve` must not appear in `tags`;
- a `#notes:xy|tags:pvp` tail, whose pre-pipe text is two characters, so the
  tail wins and supplies `pvp`;
- `| tags: pvp god-pvp` with a space;
- `(Foo version) - Aegis Endgame S Tier.` and `Aegis Endgame A Tier.` keep blocks;
- `D Tier.` and `F Tier. Weak Combo: …` trash blocks;
- a tier-less note under a `ciceron-aegis` spec;
- a whitespace-only line;
- a `title:` line between a block note and its entry (the note still applies);
- a wildcard entry and a malformed line;
- a block note with two pipe segments, `|tags:PvE|tags:111 222`, whose second
  segment must not add tags `111`/`222`, and a note whose first segment after
  `|` is not `tags:`. Both must increment `ignored_note_segments`.

#### [MODIFY] [tests/test_wishlist.py](../tests/test_wishlist.py)

- Parametrized scoping and notes/tags/title/activity assertions per fixture
  case.
- Tier recognizer truth table for both polarities, including `tier_format="none"`
  yielding `not-declared` on identical text.
- **Invariance:** for every file in `tests/fixtures/*.txt`, and for each spec
  variant, `parse_wishlist(..., evidence=True)` has `keep`, `trash`, `skipped`
  and `wildcards` equal to `evidence=False`, and `evidence=False` leaves
  `ignored_note_segments` at `0`.
- Only the merged `Wishlist` sums `ignored_note_segments` across sources. Each
  `WishlistSourceStatus` copies the value from its own source's parsed
  `Wishlist` — never the merged sum, and never by rescanning text. Assert both:
  the merged total equals the sum of two sources with different counts, and
  each status holds its own source's count.
- The alignment invariant holds, including the `is` identity of perks, after
  `merge`.
- `merge` raises on mixed evidence presence.
- The `LINE_RE` match/skip outcome is unchanged per fixture line.
- `fetch_with_status` covers each of the three statuses and `cache_written_at`
  via `os.utime`. Existing `fetch` tests stay untouched and passing.
- `source_specs` covers both forms plus every rejection listed above.
  `load_config` wraps rejections as `ConfigError`, and the committed
  `config.toml` validates to the three expected specs.

#### [NEW] [tests/test_wishlist_evidence.py](../tests/test_wishlist_evidence.py)

- Two sources in one family plus one other family: `keep_families` counts the
  family once.
- Uncovered, covered-but-no-perk-match, and stale-source cases.
- Each conflict kind, and no conflict when there is only keep or only trash.
- `tier-disagreement` within a family.
- **Parity with rules:** for `tests/fixtures/weapons_dupes.csv` and
  `tests/fixtures/weapons.csv` with a synthetic perk map, `bool(keep_matches)`
  equals `weapons.keep_match_count(...) > 0` and `trash_kind` equals
  `weapons.trash_match(...)` for every row.
- **Decision invariance:** `weapons_rules.run` over the fixture weapons gives
  identical decisions and `keep_trash_conflicts` whether given
  `load_all_with_sources(cfg)[0]` or `load_all_with_evidence(cfg).merged`
  (local cache files written under `tmp_path`; no network).

#### [NEW] [tests/test_cli_wishlists.py](../tests/test_cli_wishlists.py)

Use `tmp_path` caches with a fixed `os.utime` and a monkeypatched clock. Cover:

- exact full stdout for a two-family config (string-form and table-form
  sources);
- the stale fallback label (with `_download` raising) and its stderr warning;
- two sources with different ignored-segment counts, proving each line prints
  its own count rather than the merged total;
- a non-printable/overlong title escaped and truncated;
- `families:` line ordering;
- first per-source lines and the `total:` line keep the pre-change template and
  wording exactly: build the expected lines with the old f-string for the same
  counts;
- the `ignored note segments` suffix appears only when the count is non-zero;
- a `WishlistError` exit code of `1`.

## Mechanical inclusion test

A proposed change is **in scope** if and only if **all** of these hold:

- it lives in `wishlist.py`, the new `wishlist_evidence.py`, the `source_specs`
  call in `config.py`, the name/url iteration swaps listed above,
  `_cmd_wishlists`, `config.toml` `[wishlists.sources]`, the two docs, the
  WORKLOG, or the listed tests/fixture;
- for identical wishlist bytes, it leaves every value `rules/`, `pipeline.py`,
  `report_run.py`, `report.py`, `review*.py`, `note_history.py` and
  `server/` compute unchanged;
- any metadata it records comes from bytes the source file actually contains,
  or from explicit per-source config, never from item names, weapon columns,
  counts, or guesses; and
- it does not change `WishlistSourceData`, `WishlistSourceIdentity`, the
  fingerprint payload, the snapshot, `RULESET_VERSION`,
  `SNAPSHOT_SCHEMA_VERSION`, or the report golden.

Worked examples:

- **IN SCOPE:** `parse_wishlist(text, "aegis_trash", spec=…, evidence=True)`
  records `tier="D"`, `tier_status="parsed"`, `activity_basis="source"` for an
  entry under `//notes:D Tier. Aegis Recommended alternative(s): X`.
- **IN SCOPE:** `item_evidence` on an item keep-listed by `aegis_keep` and
  trash-listed by `aegis_trash` reports `keep_families == trash_families == ("aegis-endgame",)`
  and one `keep-trash-same-family` conflict, without changing what
  `weapons.run` decides.
- **IN SCOPE:** `vault-cleaner wishlists` printing
  `  fetch: stale cache used after failed download; cache written …`.
- **IN SCOPE:** removing Nitaraku from `config.toml` and adding `aegis_keep`
  with the exact URL above.
- **OUT OF SCOPE:** skipping trash when the only keep match is tier D–F, adding
  `#vc-review: aegis-trash-voltron-keep`, or any tier threshold. That is Child 5.
- **OUT OF SCOPE:** adding `family` to `WishlistSourceIdentity`, the snapshot or
  the fingerprint, or rendering evidence in the review UI or Notes.
- **OUT OF SCOPE:** inferring an Aegis tier for a Voltron entry from the word
  "tier" in its prose, or inferring PvP value from a missing Aegis rating.
- **OUT OF SCOPE:** a `jxpv2`/`nitaraku`/`mrcharles` `tier_format`, DIM-style
  duplicate-roll de-duplication, wildcard support, parsing revision dates, or
  deleting `wishlists/aegis.txt`.
- **OUT OF SCOPE:** validating source *names* as filenames, or other hardening
  of `fetch` beyond `fetch_with_status`.

### Stop conditions

Stop implementation and return to the orchestrator if:

- #155 is not closed with its implementation on `main` at dispatch or branch
  time;
- any committed fixture's weapon decisions, Notes, `keep_trash_conflicts`,
  snapshot golden, or fingerprint differ from `main` for identical wishlist
  bytes;
- the alignment invariant cannot be kept without changing how `keep`/`trash`
  are built or consumed;
- a re-downloaded Ciceron file gets less than 100% `ciceron-aegis` tier
  recognition, a candidate URL returns non-200, or its header/format no longer
  matches this plan's measurement;
- the evidence-off Voltron parse time exceeds 1.25× the recorded baseline
  median (re-measure baseline on `main` on the same machine first), or its
  tracemalloc peak grows by more than 5%;
- evidence-on Voltron parse exceeds a tracemalloc peak of 600 MB;
- any rule, pipeline, report, review, server, UI, snapshot, or version file
  appears to need editing; or
- DIM's upstream scoping rules have changed since 2026-09-15 in a way that
  conflicts with this plan.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Evidence-off path quietly pays for evidence:** notes/tag slicing or entry
   construction happens before the `evidence` check. This shows up as a
   Voltron time/memory regression in report/serve.
2. **Alignment drift:** `merge`, a `continue` branch (malformed, wildcard,
   separator-only perks), or whole-item trash appends to `keep`/`trash` without
   the evidence list, or the reverse. Lengths then match on the happy-path
   fixture but not on the hostile lines.
3. **Scoping off-by-one with DIM:** `title:` wrongly resets block notes, a
   `#notes:x` one-character tail wins (or `#notes:x|tags:pve` wins because the
   length test ran on the uncut tail), the tag capture runs past the next `|`
   (for example `(.*)` swallowing a second `|tags:` segment of perk hashes), or a
   `//notes:` line with leading whitespace behaves inconsistently after strip.
5. **Swap delta stated one-way or under the wrong predicate:** docs or WORKLOG
   describe the source swap as only surfacing proposals, omit the measured
   suppressing case, print one exposing figure under another's wording (the
   E1/E2 confusion this plan already made once), or describe a subsumption
   figure (E1, E2, S1) as a certain loss or gain of protection (the
   overstatement this plan made in round 3).
6. **Ignored-segment counter recomputed or aggregated:** the loader or the CLI
   rescans raw text to derive `ignored_note_segment_entries` instead of reading
   the parser's own counter, or copies the merged sum so every per-source line
   prints the same aggregate.
4. **Config normalization leak:** `load_config` rewrites
   `cfg["wishlists"]["sources"]` to specs, which breaks string-URL tests and
   `WishlistSourceIdentity`. Alternatively, table-form URLs reach `fetch` as a
   dict, or the family regex rejects legacy underscore source names in string
   form.

# Reusable implementer execution prompt

Implement issue #158 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-158-implementation-plan.md
```

Read the entire handoff, issue #158, #140's tracking comment (item 3), `docs/aggressive-clearout-measurement.md` §5–§6, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- first verify #155 is closed and its implementation is on `main`; if not, stop;
- work on `feat/issue-158-wishlist-evidence`; branch from latest `main` and record the base SHA;
- use Google `gemini-3.8-flash` with native `thinking_level = high`; if the orchestration runtime cannot instantiate it, stop for the documented manual cross-provider handoff rather than silently substituting a model;
- before editing, record on `main` the evidence-off baseline: three timed runs and a tracemalloc peak of `parse_wishlist` over `wishlists/choosy_voltron.txt` (run `vault-cleaner wishlists` first if the cache is missing);
- apply the plan's mechanical inclusion test to every production hunk;
- never commit third-party wishlist content, anything under `data/`, or `wishlists/`;
- re-download both Ciceron files to a scratch directory outside the repo and confirm 100% tier recognition before changing `config.toml`;
- re-measure the swap's item-level delta from public list bytes only, reporting all four figures the plan defines (E1 ≥1 roll loses guaranteed coverage — upper bound; E2 every roll loses guaranteed coverage; E3 no keep entry left — lower bound, no keep protection remains; S1 suppressing — upper bound) with their predicates, and record them in `docs/wishlist-evidence.md` and the handoff;
- update `WORKLOG.md` with a dated entry that includes the evidence-off and evidence-on time/memory measurements;
- run focused tests (`tests/test_wishlist.py`, `tests/test_wishlist_evidence.py`, `tests/test_cli_wishlists.py`, `tests/test_pipeline.py`, `tests/test_config.py`, `tests/test_report_run.py`) before the full gates;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `git diff --check origin/main...HEAD`, `test -z "$(git ls-files data/ wishlists/)"`, `git diff origin/main...HEAD --stat -- src/vault_cleaner/rules src/vault_cleaner/report_run.py src/vault_cleaner/report.py src/vault_cleaner/server src/vault_cleaner/ui src/vault_cleaner/pipeline.py tests/fixtures/report_snapshot_v2.json` (must be empty), and `git status --short`;
- run `.venv/bin/vault-cleaner wishlists` against the real configured sources and include its stdout in the handoff (public third-party list stats only);
- commit with `Refs #158` (no closing keywords), push only the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, provide the orchestrator with:

- the requested and actual provider/model/native effort;
- the branch, and the base and head SHAs;
- the changed files;
- invariance-test evidence (decisions, conflicts, and `LINE_RE` outcome);
- alignment-invariant tests, including the hostile lines;
- baseline and post-change parse time/memory numbers;
- the Ciceron re-download recognition counts;
- the re-measured swap delta as all four figures (E1, E2, E3, S1) with their predicates;
- the real `vault-cleaner wishlists` stdout;
- complete command outputs;
- the stop conditions considered, and all deviations.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**

The change extends an untrusted-input parser, adds strict config validation on
every `load_config`, and swaps a decision-affecting input source. The main risk
is silent: an alignment or scoping bug gives wrong attribution while every
existing test stays green, because no rule consumes the evidence yet. Child 5
would then build removal policy on corrupted evidence. The decision-invariance
guarantee also has to be proven independently rather than trusted, and
#140's workflow rule names parser changes as requiring independent adversarial
review. (#142 §12 row 3's "standard review" predates that rule and is
superseded.)

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time. A non-Gemini reviewer is preferred when available.

# Review checklist

- [ ] #155 was landed before the branch base. The base SHA is recorded.
- [ ] `git diff base...head` touches no file under `rules/`, `report_run.py`, `report.py`, `review*.py`, `note_history.py`, `pipeline.py`, `server/`, `ui/`, or `tests/fixtures/report_snapshot_v2.json`. `RULESET_VERSION` stays `4` and `SNAPSHOT_SCHEMA_VERSION` stays `2`.
- [ ] `WishlistSourceData`/`WishlistSourceIdentity` fields and `compute_fingerprint` payload are unchanged. The existing pipeline identity test passes unmodified.
- [ ] `LINE_RE` still accepts/rejects exactly the same lines. `evidence=False` does no notes/tag/entry work, as confirmed by reading the loop and by the recorded time/memory numbers.
- [ ] The alignment invariant (length and `perks is`) is tested after parse and after `merge`, including for malformed, wildcard, separator-only, and whole-item lines. Mixed-evidence `merge` raises.
- [ ] `ignored_note_segments` is produced by `parse_wishlist`, summed only on the merged `Wishlist`, copied into each status from that source's own parsed result (never the merged sum, and never recomputed), and stays `0` with `evidence=False`.
- [ ] DIM scoping matches the plan: blank and `//` lines reset block notes, `title:` does not, a tail wins only if its text **before the first `|`** is longer than one character (`#notes:x|tags:pve` falls back to the block note, whose own segments then supply the tags), notes end at the first `|`, tags come only from the first following segment captured with `([^|]*)`, later segments (including a second `tags:`) are ignored and counted, and `| tags:` with a space works.
- [ ] Tier regexes are exactly as specified and applied only under `tier_format = "ciceron-aegis"`. Voltron text containing "tier" yields `not-declared`, never `unrecognized`.
- [ ] Activity basis follows the precedence `tags` → `source` → `unknown`. Nothing infers PvP value from PvE or from absence.
- [ ] `item_evidence` matching is parity-tested against `weapons.keep_match_count`/`trash_match` on fixture rows. Families, not sources, are counted. All three conflict kinds and the uncovered, stale, and unknown-tier fields are tested.
- [ ] `source_specs` rejects every listed invalid shape, and `load_config` surfaces a `ConfigError`. Raw `cfg["wishlists"]["sources"]` is not mutated. String-form legacy configs still load.
- [ ] `vault-cleaner wishlists` output matches the specified copy exactly. Existing first lines and `total:` are unchanged. Titles are escaped and truncated.
- [ ] `config.toml` holds exactly the three specified sources, and the Nitaraku entry is gone. The recorded Ciceron re-download shows 100% tier recognition.
- [ ] `docs/wishlist-evidence.md` states the uncertainty invariants, the strategy with its measured rationale, the swap's decision change in both directions as E1/E2/E3/S1 with their predicates and re-measured counts, framed as a range (E3 no keep protection remains, E1 possible loss) with no subsumption figure described as certain, the Child 5 fingerprint handoff, "not declared" revision dates, and Ciceron provenance as same maintainer/converter/family with revision alignment **not verified** (no "same revision" claim anywhere, in docs or `config.toml` comments). The §6 supersession note is the only edit to the #142 report.
- [ ] No third-party wishlist bytes, `data/`, or `wishlists/` are tracked. Fixtures are synthetic with LF endings.
- [ ] Ruff, full pytest, diff check, branch-only push, clean worktree, and WORKLOG entry (with the actual model/effort and measurements) are all present.

# Dispatch comment draft

Planned #158 in [handoffs/issue-158-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-158-implementation-plan.md) on `main`.

- **Scope decision:** per-entry wishlist evidence (source, curation family, notes, tags, section title, activity with basis, tier with parse status), structured fetch/freshness, and an item-evidence query with family-deduplicated support and explicit conflicts and uncertainty. No rule consumes it yet, and decisions are byte-identical for identical wishlist bytes. Aegis strategy: Ciceron major-perks S/A keep plus the Ciceron trash list as one `aegis-endgame` family; Nitaraku removed (stale, and its all-tier keep rolls overlap 164 of 286 Aegis trash items).
- **Blocked by:** #155 implementation landing.
- **Implementer tier & effort:** Google `gemini-3.8-flash`, native `thinking_level = high`
- **Implementation branch:** `feat/issue-158-wishlist-evidence`
- **Recommended review path:** independent adversarial review (parser, config validation, input-source swap).
- **Likely findings:** evidence-off path regresses performance; evidence/match list alignment drifts on hostile lines or `merge`; DIM note-scoping off-by-one (title reset, the one-character tail test applied before the pipe cut, tag parsing running past the next `|`); swap delta stated one-way or under the wrong predicate; config normalization mutates raw sources or breaks legacy string form.
