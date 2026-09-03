# Duplicate review: count and hierarchy design

Decision record and implementation handoff for
[#113](https://github.com/tonym999/vault-cleaner/issues/113). Implementation is
[#119](https://github.com/tonym999/vault-cleaner/issues/119).

This is a design pass. It changes no Python rules and no report or server
contract. Everything below is presentation.

Baseline captures and how they were produced:
[docs/evidence/issue-113](evidence/issue-113/README.md).

---

## 1. Problem

The Armor duplicates view counts three different things — groups, pieces of
armor, and proposals — and never states which is which.

**The report tile row mixes nouns.** `PROPOSED`, `AFTER VETOES`, `REVIEWED` and
`UNREVIEWED` count items. `SHOWN` counts groups, but only on the duplicates
surface (`review_server.js:832-839`); the label and its visual weight are
identical either way, and only a small sub-caption changes.

**`Showing N of M groups` has an already-filtered denominator**
(`review_server.js:996`). `M` is `selectedArmorGroups.length`, the count *after*
the kind selector. Rendered: unfiltered gives `Showing 2 of 2 groups`; filtered
to Exact gives `Showing 1 of 1 groups`. Both numbers move together, so the
string can never reveal that groups of another kind exist. The
`Showing 2 of 74 groups` in the issue description therefore means "2 of the 74
groups *of the currently selected kind*".

**Nothing states a piece total.** A reviewer cannot answer "how many armor
pieces is this screen about?" from anywhere on the surface.

**Facet counts are not all the same noun.** `countArmorGroups`
(`review_ui.js:626-645`) counts groups, except for `tuningModSlot` on a
same-stat group, where it adds one per distinct *member* tuning. With a
two-group fixture the tuning options sum to five while every sibling facet sums
to two — in identical `value (N)` presentation.

A complete inventory of all 160 user-facing counts, headings, badges, filter
summaries and group-kind labels is committed at
[evidence/issue-113/count-label-inventory.md](evidence/issue-113/count-label-inventory.md),
with noun, denominator, filter scope and a misreadability verdict for each. 57
were marked misreadable.

## 2. Alternatives considered

Both fix the noun collision. They differ on one axis: **where scope lives.**

Both are built as specimens using `review.css`'s own tokens, so the comparison
is against the shipped UI rather than a redesign of it. The interactive artifact
is [evidence/issue-113/count-treatments.html](evidence/issue-113/count-treatments.html)
— open it locally; it also carries the full criterion-by-criterion comparison
table. Rendered stills:
[alternative A](evidence/issue-113/alternative-a-scoped-summary-line.png) ·
[alternative B](evidence/issue-113/alternative-b-distributed-counts.png).

### A — one scoped summary line

Delete the `SHOWN` tile from this surface and the `Showing…` hint. Replace both
with a single accented line above the list stating both nouns, both
denominators, and the active filter. Group headers carry local facts plus a
piece count.

- **Wins on** answering "how big is this review" in one place; one live region
  to announce on filter change; the tile row becomes homogeneous.
- **Costs** scope that scrolls away on a long list, and four numbers in one
  sentence, which wraps to three lines at 390px — measured at 61px, and the
  cheaper of the two narrow costs.

### B — every count carries its own noun

Keep counts distributed but make each self-describing. The tile row gains a
pieces tile and splits `SHOWN` into its two nouns. Filter chips state per-kind
totals. Each group header leads with a piece count.

- **Wins on** surviving a scroll — the piece count is on the group being read;
  per-kind totals without clicking through.
- **Costs** pairs of numbers that must agree forever — `12` in both the `Groups`
  tile and the `Exact` chip, `74` in both the tile and the `All kinds` chip — and
  no single answer to the size of the review. At 390px its tile row stacks rather
  than overflowing, but stacking costs 178px before the first group.

## 3. Decision

**A hybrid, weighted toward B.** The costs are not symmetric: A's weakness is a
scroll away, B's weakness is a permanent consistency obligation across paired
call sites.

**One correction from measuring.** The comparison originally scored the 390px
row as a win for B, reasoning that tiles and chips stack. Rendered at exactly
390px, neither treatment overflows and **A is the more compact** — a 235px block
against B's 358px, because stacking B's tile row costs 178px. This does not
change the decision; it strengthens it, since the hybrid adopts A's line and
specifically declines B's expanded tile row.

Adopt **A's single scoped line** as the one authoritative statement, and **B's
per-group piece count and review-only banner** as local reinforcement that never
restates a total. `SHOWN` leaves this surface entirely; the tile row keeps only
proposal-shaped counts.

### Exact copy changes

| # | Change |
|---|---|
| 1 | **Delete** the `SHOWN` tile on the duplicates surface, and delete `"Showing " + filteredGroups.length + " of " + selectedArmorGroups.length + " groups"`. |
| 2 | **Add** above the list, in one `aria-live="polite"` region: `12 of 74 groups · 38 of 211 pieces — filtered to exact duplicates`. Unfiltered, the same region reads `74 groups · 211 pieces` with no "of". Both piece figures count group **members**, measured identically: 211 is the members of all 74 groups, 38 the members of the 12 shown. Pieces that are in no duplicate group are counted by neither. |
| 3 | **Group header gains** a piece count as its first element: `3 pieces`. |
| 4 | **Kind label** becomes `Exact` / `Same stats · review only`, replacing `"Exact duplicate group · " + group.groupKind`. |
| 5 | **Same-stat banner**, in two parts. The first sentence is unconditional, because it is always true of a same-stat group: `Base stats match but tuning differs, so this pass selects no survivor.` The second is appended only when at least one member carries a proposal: `Pieces below that already carry a proposal keep their verdict controls.` |
| 6 | **Facet options** state their noun when it is not groups: `Melee (1 group)`. |

### One noun

`pieces` is the user-facing word for a piece of armor. `copies`, `items` and
`members` are retired from user-facing text on this surface. `members` remains
correct in code and in the snapshot schema.

### Adopted separately: transpose the comparison table

At 390px the current member-as-column table shows exactly one member; comparing
requires scrolling inside the table. Members become rows.

This is orthogonal to the count treatment and is the largest single piece of
#119. It must carry over the existing conditional-column behaviour, where
`memberValues` (`review_ui.js:1133-1159`) shows `Seasonal Mod`, `Holofoil` and
`Tuning Stat` only when members actually differ. A fixed-column row layout would
lose that.

## 4. Scope boundaries

Split out of this pass, and not presupposed by the decision:

| Issue | Feature |
|---|---|
| #115 | Per-group bulk verdict controls |
| #116 | Exposing an armor archetype score on duplicate members |
| #117 | Copying a group's instance ids as a DIM search query |
| #118 | Baseline defects found while capturing evidence |

Unchanged by #119: armor grouping keys, close-pass behaviour, ranking, survivor
selection, notes, tags, thresholds, verdict authority, revision, finalization,
persistence, lifecycle, auth. `Id` and `Hash` stay opaque strings. No new
runtime dependencies. `RULESET_VERSION` is not bumped — presentation only.

## 5. Open questions

- **Does the piece count include the survivor?** `3 pieces` on an exact group
  counts one survivor and two candidates. A reviewer scanning for work may read
  it as three deletions. `3 pieces · 2 proposed` fixes it at the cost of a
  fourth number.
- **What is a "piece" in a filtered view?** Both figures count group members
  and are measured identically today, so the ratio is sound. But the *kind*
  filter selects whole groups, whereas a future member-level filter (tuning
  slot, protection) would select members — at which point "pieces shown" and
  "members of shown groups" diverge and the line needs re-deciding.
- **Should the summary line pin on scroll?** It would erase A's only real
  weakness, at the cost of vertical space already scarce at 390px.
- **Not verified against the running app.** Both treatments are specimens.
  Contrast, focus order and live-region announcement need checking during #119.

## 6. Skill selection record

#113 required a reusable design/audit skill installed at user scope before
implementation, via the official skill-installer workflow. No skill is committed
to this repository.

| Field | Value |
|---|---|
| Skill | `ux-audit` |
| Source | https://github.com/paulunemoon/ux-audit-skill |
| Version | 1.4.0 |
| Commit | `f07ff7607039a846fba1e711bb99716a68b12f34` |
| License | MIT — © 2026 Pauline Mila Alonso |
| Installed to | `~/.claude/skills/ux-audit` and `~/.codex/skills/ux-audit` |

The pinned commit was the tip of `main` at install time; the installed
`SKILL.md` was diffed against the raw file at that commit and both install paths
against each other. #113 names `~/.codex/skills` as the global scope, which is
the Codex convention; this work ran in Claude Code, which reads
`~/.claude/skills`, so both were installed from the same pinned commit.

**Why it fits.** Its declared job is evaluating interfaces that already exist,
from a live URL, screenshots, or source. Data display is a first-class dimension
with sections on truncation and identifiers, sorting and filtering, stat cards
and metric grids — which is close to a purpose-built checklist for this ticket.
Every finding carries a severity *and* a confidence that names its source, which
matches #113's framing of its own examples as hypotheses rather than fixes. It
also grades state coverage, responsive behaviour and accessibility as separate
dimensions, and instructs the auditor to respect deliberate constraints — useful
for a dense expert tool where density is a feature.

**Workflow used.** The §0 gate (scope: this surface; platform: local web app;
audience: expert; stakes raised because an approved junk verdict becomes a DIM
tag acted on in bulk; onchain module not loaded). §1 evidence intake against
committed fixtures plus the rendered server. §2 dimensions, subset only — state
coverage, content and microcopy, visual hierarchy, data display, accessibility,
responsive. §3 finding schema. §4 report.

**Setup and data transfer.** No connector, plugin, Figma or Storybook
dependency. The skill declares no API and no network; its one script
(`contrast-check.py`) is offline, dependency-free Python 3, and was used for
contrast ratios only. Nothing left the machine. No runtime dependency was added
to this project.

**Known limitation, and how the pairing was handled.** The skill refuses
greenfield build work. Read closely, that refusal governs *new* UI: its finding
schema still mandates a `Recommendation` field including verbatim copy rewrites,
and it separates Defect / Opportunity / Taste. So it covered the audit and the
exact copy changes in §3, but not the two-alternative exploration #113 also
requires.

#113 anticipated this and asked for a paired design skill. The pairing used was
`artifact-design`, which was already available in the working environment rather
than installed for this ticket. **This is a deviation from the prerequisite as
written**, which expects a user-scoped install, and it is recorded rather than
papered over: a second global skill was assessed as unnecessary once a design
capability was already present, and no candidate was found that would have added
anything for this specific job. If a durable, user-installed design companion is
wanted for future passes, that is a small follow-up — the audit half, which is
the part with no in-environment equivalent, is the half that needed installing.

### Candidates rejected

- **`frontend-design-review`** (microsoft/skills, commit
  `cbfd1b6652debe08f9d329d713b382a1a0db2e3e`, MIT). The issue's primary
  candidate and a more popular source. Rejected: roughly half is a creative
  mode whose guidance (commit to an aesthetic direction, avoid Inter/Roboto,
  gradient meshes, brutalist tone-setting) is wrong for a surface that must stay
  consistent with the shipped UI; its review half leans on Figma Dev Mode and
  Storybook, neither of which exists here, which #113 explicitly warned must not
  become hard dependencies; it has no data-display dimension at all; and its
  stated accessibility floor is WCAG 2.1 A, where #102 and #113 expect AA.
- **`webapp-ui-skill`** (sergekostenchuk, commit `ddaedd71…`). Useful audit and
  state-coverage modes, but it sits inside a larger multi-skill system, making a
  clean single-skill pinned install harder to justify.
- **OpenAI curated catalog.** `figma-use` and `figma-implement-design` require a
  Figma MCP and file. `playwright-interactive` is browser QA and `screenshot` is
  capture — both useful as evidence tools, neither a critique workflow.

Maturity favoured the Microsoft skill and that trade was made knowingly: the
`ux-audit` repository has few stars, against which its changelog shows
evidence-driven maintenance (1.4.0 removed a script on the evidence that it went
unused across twenty-two runs). Fit for this ticket was weighted above
popularity.
