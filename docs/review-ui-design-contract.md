# Review UI design contract

Status: stable reference, owned by [#136](https://github.com/tonym999/vault-cleaner/issues/136).
Captured 2026-09-20 from the Next.js review prototype (see [Provenance](#2-provenance)).
Extended 2026-09-26 by [#171](https://github.com/tonym999/vault-cleaner/issues/171)
with the Proposals surface ([5.13](#513-proposals-surface)).

This document records what the agreed review-UI design *looks like and how it
is composed*, in terms that do not depend on the prototype's source, its
uploaded archive, or any framework. A future planner or implementer should be
able to read this file, [PLAN.md](../PLAN.md), [AGENTS.md](../AGENTS.md) and the
production code, and never need the original zip.

It is a **design contract, not an implementation plan**. It does not migrate the
renderer, choose a rendering route, or change any behaviour. Nothing here adds a
runtime or build dependency: runtime dependencies stay pandas and Flask.

## Contents

1. [Source-of-truth precedence](#1-source-of-truth-precedence)
2. [Provenance](#2-provenance)
3. [Illustrative, not authoritative](#3-illustrative-not-authoritative)
4. [Design tokens](#4-design-tokens)
5. [Component contract](#5-component-contract)
6. [Icon roles](#6-icon-roles)
7. [Accessibility and focus](#7-accessibility-and-focus)
8. [Responsive behaviour](#8-responsive-behaviour)
9. [Empty states](#9-empty-states)
10. [Candidate mapping to Jinja components](#10-candidate-mapping-to-jinja-components)
11. [Prototype defects not to inherit](#11-prototype-defects-not-to-inherit)
12. [Open questions](#12-open-questions)

## 1. Source-of-truth precedence

When two sources disagree, the lower number wins *for the thing named*.

1. **The Next.js prototype** is authoritative for visual hierarchy, component
   anatomy, spacing and density, design-token intent, navigation and filter
   presentation, card and group composition, and interaction *affordance*
   intent.
2. **Current Vault Cleaner Python and server contracts, and delivered M9
   semantics,** are authoritative for actual data, counts, group membership and
   order, survivor and disposition state, proposal eligibility, verdict
   acknowledgement, stale-state handling, finalisation, reset and shutdown,
   accessibility semantics, and responsive constraints.
3. **Issue [#131](https://github.com/tonym999/vault-cleaner/issues/131), plus
   the delivered references
   [#113](https://github.com/tonym999/vault-cleaner/issues/113) and
   [#119](https://github.com/tonym999/vault-cleaner/issues/119),** supersede any
   illustrative prototype wording or value that conflicts with settled Armor
   duplicates semantics.
4. **AGENTS.md and PLAN.md** security and packaging rules are authoritative for
   trust boundaries, loopback-only behaviour, dependencies, hostile input,
   opaque ids, wheel packaging, and repository hygiene.

Two consequences worth stating plainly:

- *Where the prototype and production disagree about how something looks, the
  prototype is the target and production is the baseline to be migrated.* Each
  such difference is recorded in [section 5](#5-component-contract) as a delta,
  so a later ticket can see exactly what would change.
- *Where they disagree about what something means, does, or exposes to
  assistive technology, production wins*, even if the prototype looks nicer.
  Design intent is never a licence to weaken a semantic or a security control.

## 2. Provenance

The prototype was a v0-generated Next.js 16 / React 19 app with Tailwind 4 and
a shadcn (`base-nova`) setup. Its shape:

| Part | Role in the prototype |
| --- | --- |
| `app/page.tsx` | The whole UI: one client component holding all state, 277 lines |
| `app/globals.css` | Design tokens plus a small `@layer components` set: `button-primary`, `button-secondary`, `icon-button`, `field`, `metric-card`, `filter-chip`, `tab-button`, `empty-state` |
| `app/layout.tsx` | Title, scheme-specific favicons, contradictory light/dark shell metadata, Vercel Analytics in production |
| `components/ui/button.tsx` | A shadcn `Button` with variants and sizes. **Never used by the page**, so it carries no design intent |
| Everything else | Scaffold: lockfile, icons, placeholder images |

It has one page and no server. Its title is "Vault Cleaner / Review".
`app/page.tsx` and `app/globals.css` carry the rendered design intent;
`app/layout.tsx` carries shell metadata and the production-only analytics hook.
The remaining archive is scaffolding.

The prototype is a **visual and component design source**. It is not the
production architecture. The production application remains the Flask
loopback review server, and the prototype's framework, styling toolchain,
icon package, analytics, and package manager are not dependency decisions
(see [section 3](#3-illustrative-not-authoritative), item 6).

**Extension for #171 (2026-09-26).** The same archive was unpacked outside the
repository and extended to design the Proposals surface. A new
`app/proposals.tsx` (705 lines) holds that surface and its sample proposals.
`app/page.tsx` (now 295 lines) gained the Proposals wiring, the surface switch
moved above the filters, `aria-pressed` on the switch buttons, URL parameters
used only to take screenshots, and a wrapping fingerprint. `next.config.mjs`
turns the development badge off. Nothing from the extension is committed. The
owner reviewed and approved it from screenshots on 2026-09-26, and the design it
carries is recorded in [5.13](#513-proposals-surface). Section 1's precedence
applies to the extension exactly as to the original.

## 3. Illustrative, not authoritative

Everything in this table appears in the prototype and **must not be
converted into a product requirement**. The right-hand column names what
actually owns the truth.

| # | Prototype fact | What owns the truth |
| --- | --- | --- |
| 1 | `initialGroups` is a hard-coded array of two example groups | The server report snapshot; browser projections such as `armorGroupsFromSnapshot` in `review_ui.js` |
| 2 | Hard-coded totals and counts: 407 proposed, 88 junk, 319 review, 71 groups, "Exact 2", "Same stats 69", and the derived "unreviewed = 407 minus reviewed". Also the fingerprint string | `reviewCounts` and the report renderer; the fingerprint comes from the report run (`report_run.py`) |
| 3 | Verdicts live in React `useState` and change instantly on click | The server. A verdict is held by the server and the page repaints only after an **acknowledgement**; no optimistic state |
| 4 | Simulated upload, finalise, reset and shutdown: a notice string is set and nothing is called | The server lifecycle and session states in PLAN.md ("M8 schema-version-1 session states") |
| 5 | Illustrative filter option values: `Any class`, `Warlock`, `Titan`, `Hunter`, `Any slot / type`, `Leg Armor`, `Warlock Bond`, and the search placeholder | Report-derived facet values. Class comes from DIM `Equippable`; current DIM `Owner` is shown separately as Location |
| 6 | Next.js, React, Tailwind, shadcn/`base-nova`, Lucide React, `@base-ui/react`, Vercel Analytics, pnpm | Not production dependencies. AGENTS.md: runtime is pandas and Flask; dev tooling stays out of the runtime set |

More facts in the same category, found while capturing the design:

- **Member ordering and disposition.** The prototype treats *Member 1* as the
  "Preferred survivor" and every other member as "Proposed review", purely by
  array index. Real dispositions come from the server: `preferred_survivor`,
  `retained_protected`, `proposed_junk`, `proposed_review`.
- **Verdict controls on every member.** The prototype gives every member
  Approve, Veto and Unset. In production only a member that already carries a
  proposal can receive a verdict; survivors and retained members are read-only.
- **Group shape.** The exact group's grid is written for exactly two members and
  the tuning group's for exactly three. Real groups have any number of members
  (the production matrix shows 2 to 6 members as columns when there is room and
  falls back to rows otherwise; see [8](#8-responsive-behaviour)).
- **Stat, tuning and axis values.** The `Weapons`/`Grenade`/`Super` labels, the
  `Melee`/`Weapons`/`Health` tuning values, the `Protection: soft — locked` and
  `Locked` rows, the `Class Health Melee 0 base` line and the "Identical across
  all pieces" sentence are sample text.
- **Actions with no production counterpart.** `Help`, `More actions`,
  `Export report` and `Copy fingerprint` do nothing in the prototype and have no
  delivered production behaviour. They are **not requirements**; each would need
  its own ticket. (The server deliberately does not import or export review
  manifests; see the README.)
- **The original Proposals tab** was a placeholder card telling the user to
  switch tabs. The #171 extension replaced it with a designed surface
  ([5.13](#513-proposals-surface)).
- **The #171 extension's data and behaviour.** Its ten sample proposals, their
  names, ids, hashes, perks, sources, counts and verdicts; the order of its
  groups; its instant single and bulk verdicts; the "1 chunk" line; the single
  icon-only copy button, which copies nothing and is superseded by per-chunk
  Copy buttons ([5.13.5](#5135-dim-search-panel)); the URL parameters (`tab`, `view`, `expand`,
  `action`, `annotate`); and the "needs snapshot fields" annotations. None is a
  requirement. Group order, counts, chunking and verdict state are the server's
  ([5.13.3](#5133-scope-line-and-bulk-verdicts),
  [5.13.6](#5136-grouped-view-group-card)).
- **`Shutdown is available in the desktop app shell.`** is false for this
  product. Shutdown is a real, delivered server action.
- **Ids and hashes.** The prototype's sample ids and hashes are in the real
  format. None are copied into this repository. Every example below uses
  obviously synthetic values, and every id and hash is an **opaque string**,
  never a number. The risk is at the browser boundary: `"9007199254740993"` is
  2^53 + 1, and JavaScript's `JSON.parse` silently rounds it when it becomes a
  `Number`. Python can keep it exact, but the same contract applies to every
  layer so no boundary has to be trusted to preserve it.

## 4. Design tokens

The prototype's **rendered page and token palette are dark only**:
`app/globals.css` sets `color-scheme: dark` and defines a single token set. Its
custom Tailwind `dark` variant is unused by the design-bearing page and global
stylesheet; `dark:` classes occur only in the unused shadcn `Button`. The shell
metadata is inconsistent with that rendered design: `app/layout.tsx` advertises
`colorScheme: 'light dark'`, white/black theme colours and scheme-specific
favicons. None of that supplies a light page palette. Production already has
both a light and a dark set. The tokens below record the prototype's
*dark-theme intent*; light-theme values are not a prototype fact and are
recorded as an open decision in [section 12](#12-open-questions).

### 4.1 Colour roles (dark, OKLCH)

| Role | Value | Used for |
| --- | --- | --- |
| background | `oklch(0.13 0.015 252)` | Page ground |
| card | `oklch(0.17 0.018 252)` | Section and group surfaces |
| foreground | `oklch(0.96 0.015 248)` | Primary text |
| muted-foreground | `oklch(0.68 0.025 248)` | Secondary text, captions, eyebrows |
| primary | `oklch(0.78 0.12 251)` | Accent: active states, links, focus ring, eyebrow accents |
| primary-foreground | `oklch(0.14 0.02 252)` | Text on a primary fill |
| border | `oklch(0.30 0.025 252)` | Hairlines and card outlines |
| muted / secondary | `oklch(0.22 0.02 252)` | Bar tracks, quiet fills |
| destructive | `oklch(0.68 0.18 24)` | Defined; the page uses rose utilities instead |

Semantic status hues, each used as a **tinted fill plus a border plus the same
hue for text** (roughly 10 percent fill and 40 to 50 percent border):

| Meaning | Hue | Where the prototype uses it |
| --- | --- | --- |
| Approved | emerald | Approve pressed state; the "Preferred survivor" pill; "local-only session" chip; the status notice |
| Vetoed | rose | Veto pressed state; the Shutdown button's text and hover border |
| Review or caution | amber | The tuning group's border and banner; the "Proposed review" pill |
| Score tones | primary, blue, violet | The three stat-spike bars |

### 4.2 Shape, type, spacing (resolved to plain values)

| Token | Value |
| --- | --- |
| `--radius` | `0.6rem`. Derived: sm `0.36rem`, md `0.48rem`, lg `0.6rem`, xl `0.84rem`, 2xl `1.08rem`, plus fully round pills |
| Page width | max `1440px`, centred |
| Page gutter | 16px, then 24px from the small breakpoint, then 32px from the large one; 20px vertical |
| Section card | radius 2xl, 1px border, card at 70% opacity, padding 16px (20px from small), 16px between children, 20px between sections |
| Group card | radius xl, 1px border, solid card; header block 16px or 20px padding with a bottom hairline; body the same padding with 20px between children |
| Type scale | eyebrow 10px; caption 11px; small 12px; body 14px; section title 18px; group title 20px; page title 24px; metric value 30px |
| Numeric and id text | monospace throughout: eyebrows, counts, ids, fingerprint, stat values |
| Eyebrow | 10px, semibold, uppercase, monospace, letter-spacing 0.2em |
| Small label | uppercase, letter-spacing 0.14 to 0.16em |
| Control heights | field 40px; primary and secondary buttons 12px horizontal and 8px vertical padding at 12px text; icon button 36px square |
| Motion | colour transitions on hover only; no other animation is part of the design |

The production tokens (`--bg`, `--panel`, `--ink`, `--muted`, `--line`,
`--accent`, `--approve`, `--veto`, `--review`, `--warn-bg`, `--warn-line`) map
onto these roles one-to-one. The mapping is a naming exercise, not a decision
about values.

### 4.3 Rules that hold in any theme

- **Colour never carries a state alone.** Every status, disposition, verdict
  and tone also has a text label. This matches the delivered convention (see the
  `.tuneline` note in `review.css`).
- **Disposition colours must not imply a recommendation for tuning.** Same-stat
  groups select no survivor and recommend nothing. Their treatment must not use
  the keep or junk hues in a way that suggests one tuning choice is preferred
  (`review.css`, "Same-stat groups are review-only comparisons").
- The prototype reuses emerald for *both* "Preferred survivor" and "Approved",
  and amber for both "Proposed review" and tuning. Whatever palette is chosen,
  a disposition and a verdict must remain distinguishable by more than hue.

## 5. Component contract

Each entry gives the design intent, the anatomy, and the delta against the
current production baseline. "Production" refers to `src/vault_cleaner/ui/`.

### 5.1 Page shell, header and status

**Intent.** A single centred column with a compact header: a small rounded mark
tile, the title "Vault Cleaner / Review" with the slash muted, and a one-line
status notice under it. A quiet cluster of icon buttons sits at the far end.
A hairline separates the header from the numbered sections.

**Anatomy.** Mark tile (36px, primary tint) → `h1` → status line → optional
icon-button cluster.

**Production semantics that stay (they win):**

- a skip link to the main content, and an `h1` that can take programmatic focus;
- the status line is a polite live region, so updates are announced;
- the server-connection text ("Connecting to the local review server…") is real.

**Deltas.** Production has no mark tile, no icon-button cluster, and a narrower
column (`78rem`, about 1250px). The prototype paints its status notice
emerald *regardless of content*; an error must not be presented as success, so
the delivered `.err` and `.ok` distinction stays.

### 5.2 Upload cards and session actions

**Intent.** Three equal cards, one each for Weapons, Armor and Ghosts, in a row
from the large breakpoint and stacked below it. Each card has an icon plus label
on the left, a small monospace `CSV` tag on the right, and beneath them a dashed
drop-style box showing either a prompt or the chosen file's name. The card takes
a primary tint on hover. Below the cards, after a hairline, sit the session
actions: **Finalize review** (primary), **Reset / Start new review**
(secondary), and **Shutdown** (secondary with rose text and a rose hover
border). Production spells the first label **Finalise review**, and its
wording wins.

**Production semantics that stay:**

- each upload has a real visible label and its own polite status line for
  progress and errors (`vc-upload-status-*`);
- the file input accepts `.csv,text/csv` and the browser submits **file bytes,
  never a path**;
- the session actions are a labelled group whose members follow the server's
  session state, not a fixed set:
  - `idle`: **Shutdown** and a "Connected. Upload one or more DIM CSV exports to
    begin." hint;
  - `exports-loaded` and `reviewing`: **Finalise review**, **Reset / Start new
    review** and **Shutdown**;
  - `finalized`: a "Finalised — this review is frozen" confirmation (with a count
    of approved items still suppressed by an active saved veto, when there are
    any), then **Download again**, **Reset / Start new review** and
    **Shutdown**. **Finalise review** is not offered;
  - `closed`: none.

  **Download again** stays available while the server is disconnected, but not
  once the session is terminal; reset and shutdown need a live connection.

**Deltas.** The prototype hides the file input (`sr-only`) inside a styled
label. Whatever is built must show a visible focus indicator on the *card* when
the hidden input is focused (see [section 7](#7-accessibility-and-focus)); the
prototype does not. The prototype places the session actions inside the intake
card; production renders them as a separate group. Placement is a presentation
choice for the implementation ticket, not a contract.

### 5.3 Report metric cards and copy hierarchy

**Intent.** A responsive grid (one column, then two, then four) of four cards.
Each is a stack of an uppercase 10px label, a large 30px value, and a one-line
12px caption. One card, the "still to do" one, carries a highlight: primary
border, faint primary fill, and the value in the primary colour.

Above the grid: the section heading and, on one line, the word "Fingerprint" and
the full fingerprint in a monospace chip. Below the grid: a single explanatory
sentence with a small leading icon, stating that decisions are held in the
server session and finalised later.

**Copy hierarchy.** Eyebrow, then title, then a 14px muted lead sentence, then
content, then a 12px muted footnote. Lead sentences say what the surface is for
and reassure on privacy ("Files stay on this machine"); footnotes say what is
and is not yet persisted.

**Production semantics that stay.** Card labels, values and captions are
computed from `reviewCounts` and the report, not typed. The session note must
keep saying that no reviewed CSV has been produced and this session's new
vetoes have not been persisted until finalisation. The fingerprint is
`monospace` and wraps (`overflow-wrap: anywhere`); it is never truncated.

**Delta.** Production tiles are `min-width: 11rem` flex tiles with `.n` and `.k`.
The prototype's four cards, their exact labels, and the arithmetic are sample
content (item 2 of section 3).

### 5.4 Filter panel, tabs and segmented controls

**Intent.**

- **Filter panel:** one card. Row one is a search field with a leading icon
  followed by two selects, the first with a leading icon and a trailing chevron.
  Row two is the word "Show", a set of **count-bearing chips**, and a "Reset
  filters" secondary button pushed to the far end. A short muted line in the
  heading row says that groups stay intact.
- **Surface tabs:** a rounded bordered strip containing two tabs, each a label
  plus a small monospace count. The active tab is a filled primary pill.
  Beside the strip a right-aligned "Showing N of M groups" line.
- **Group-kind chips:** All, Exact, Same stats, each with its count; the active
  chip has a primary border, tint and text colour.

**Production semantics that stay:**

- The filter row is built from report-derived facets: search, Guardian Class,
  Type, Archetype and Tuning Mod Slot, plus reset.
- **Whole-group filtering.** A filter selects groups, never individual members;
  the "groups stay intact" line is real behaviour, not decoration. For a
  same-stat group the Tuning Mod Slot filter matches when *any* member has that
  slot, and the group is then shown in full (`matchesArmorGroup` in
  `review_ui.js`).
- The surface navigation and group-kind controls are **`aria-pressed` toggle
  buttons, not `tab`/`tablist` roles**. This was a deliberate decision (see the
  `.tabs` comment in `review.css` and #131). A visual tab strip must not change
  the semantics.
- Scope and count text updates in one polite live region
  (`#vc-duplicate-scope`), not one per control.

**Deltas.** Production renders the group-kind control as a single bordered
*segmented* control (`.segbtns`) and the surface navigation as an underline tab
strip (`.tabs`). The prototype uses separate rounded chips for group kind and a
filled pill for the active tab. The prototype's control set (one class select
and one slot select) is smaller than production's four facets; the extra facets
stay. For #171 the owner moved the surface switch above the filter panel on both
surfaces ([5.13.1](#5131-page-order-and-the-surface-switch)).

### 5.5 Section heading pattern

**Intent.** A reusable heading used by every card: a wrapping row with the
heading block on the left and an optional action on the right, aligned to the
baseline. The block is an optional monospace eyebrow of the form
`NN / Label` above an `h2`.

**Anatomy.** `eyebrow?`, `title`, `action?`. The prototype's three uses show
the range of actions: a status chip, a button, and a passive hint with icon.

**Production.** There is no shared heading today; each panel writes its own
`h2` and a `hint` paragraph. Preserve `aria-labelledby` linkage from each
section to its heading. The eyebrow numbering (`01 / Intake`) is decorative and
must not be the only place a section's name appears.

### 5.6 Exact-duplicate group anatomy

**Intent.** A solid card, top to bottom:

1. **Header block.** Title (20px) with an outlined "Archetype: X" pill beside it;
   a muted meta line joining slot, class, tier and hash with muted slashes; on
   the right, a monospace "N pieces" chip.
2. **"Exact match profile"** label followed by the stat-spike ([5.8](#58-tier-5-stat-spike-presentation)).
3. A **zero-stat line** in uppercase monospace listing the stats that are zero.
4. A **"Why grouped" callout**: a box on the page-background tone with a primary
   left rule, a monospace eyebrow, and one or two sentences of explanation.
5. The **comparison matrix** ([5.10](#510-comparison-matrix)).

**Production semantics that stay.** Members, order, survivor and dispositions
are the server's. The piece count is the real count, singular when 1. "Tier"
prints the real tier or `unknown`. The class shows `class-neutral/unknown` when
absent, the archetype `none/unknown`, and the tuning slot follows the six-value
vocabulary plus `none/unknown`. The hash is an opaque string in monospace.

**Deltas.** Production splits the header into headline, meta and context rows
and shows the spike inside the context row; it puts the tuning banner before
the matrix and shows an "identical axes" line instead of a fixed "Why grouped"
sentence. Whether "Why grouped" becomes a labelled callout is an open detail
for the implementation ticket; the *intent* is that the reason the group exists
is stated in words.

### 5.7 Same-stats / different-tuning group anatomy

**Intent.** The same card, with three differences that make it read as a
*different kind of thing*: an amber-tinted outline instead of a neutral one, an
amber "N pieces" chip, and a leading **review-only banner** (amber left rule,
amber tint, an icon, a bold lead "Review-only comparison."). It has no "Exact
match profile" label and no "Why grouped" callout. Its matrix leads with the
**Tuning Mod Slot** row, visually emphasised in the primary colour.

**Production semantics that stay:**

- The group **selects no survivor and recommends nothing**; the banner says so.
- Every member's Tuning Mod Slot is visible as labelled text, and differently
  tuned pieces are never merged into an exact group.
- Only members that already carry a proposal receive a verdict; all others show
  "Read-only comparison".

**Delta.** Production already uses a warm left-ruled `tuneline warn` banner on
same-stat groups and an accent one on exact groups, so the banner *idea*
carries over; the amber outline and chip are new.

### 5.8 Tier-5 stat-spike presentation

**Intent.** Three side-by-side cards (stacked on narrow screens), each with an
uppercase monospace label and a bold monospace value on one line, a thin track
beneath with a bar whose width is proportional to the value, and a small muted
caption. The bar widths for 30, 25 and 20 are 100, 83 and 67 percent.

**Production semantics that stay:**

- The spike applies only to a true tier-5 shape: exactly one 30, one 25, one 20
  and three 0s. Anything else falls back to plain "Base stat" tiles.
- **Order is by role, primary then secondary then tertiary, never by key
  order.** The snapshot's keys arrive alphabetical.
- The bar is decoration. The **value and the role word are always text**.
- The bar width **must be set by a stylesheet rule, never an inline `style`
  attribute.** The server's CSP (`style-src 'self'`, in `server/app.py`)
  drops inline style, which once collapsed all three bars to one width (#131).
  The prototype sets width inline (`style={{ width }}`); that does not carry
  over.

**Deltas.** The prototype colours the three bars in three hues (primary, blue,
violet) and captions each "priority signal". Production uses one hue at 100, 72
and 46 percent opacity and captions each with the role word. The role word wins;
whether hue-per-role returns is a palette choice.

### 5.9 Tuning and information banners

**Intent.** A short box with a **left rule**, tinted fill, and small text. There
are two tones: *informational* (primary rule, card-toned fill; "Why grouped"
and the session note) and *caution* (amber rule and tint; "Review-only
comparison"). A monospace eyebrow may lead the text. An icon may sit at the
start.

**Invariants.** A banner is always visible (never hover-only), always
text-labelled, and never distinguished by colour alone. Its copy for
same-stat groups states that base stats match, tuning differs and no survivor
is selected. Generic and preference-free tuning language is a settled rule, not
a design choice.

### 5.10 Comparison matrix

**Intent.** A bordered, rounded, horizontally scrollable table. **Axes are rows;
members are columns.** The first column is a fixed 150px label column, the
remaining columns share the width equally. The header row shows, per member, a
label ("Member N") and the id in small monospace. Rows are separated by
hairlines, and each cell has a leading vertical hairline.

Rows in the exact group: **Disposition** then **Verdict**. Rows in the tuning
group: **Tuning Mod Slot** (emphasised), Protection, Locked, then **Verdict**.

**Production semantics that stay (they win over the prototype's simple form):**

- Rows are shown **only for axes on which members actually differ**; identical
  axes are summarised in one line instead. For a same-stat group the Tuning Mod
  Slot row is always shown. Which axes exist (Tuning Mod Slot, Seasonal Mod,
  Holofoil, Tuning Stat, Protection, In loadout, Equipped, Locked, Masterwork
  Tier, Power) is owned by `armorComparisonSpecs` in `review_ui.js`, so the
  prototype's `Protection` and `Locked` rows are real axes shown with sample
  values, not a fixed row set.
- The matrix has two orientations chosen by the *group's own container width*
  and member count, not by the viewport: a columns table for 2 to 6 members when
  there is room for every column, and a rows table otherwise, so nothing is
  ever forced into an unreadable width (#131, container queries, per-count
  budgets in `review.css`).
- Member headers show the disposition as text plus the id; long ids wrap and are
  never truncated.

**Delta.** Production's default is the *transposed* layout (members as rows),
switching to the prototype's axes-as-rows orientation when the container
allows. The prototype's fixed member count and always-present rows do not carry
over. The prototype's intent that **axes are rows and members are columns**
is the target orientation and is already reachable in production.

### 5.11 Verdict controls and read-only members

**Intent.** Three small bordered buttons in a wrapping row: **Approve**,
**Veto**, **Unset**, with a one-word status ("Unreviewed", "Approved",
"Vetoed") beneath. The pressed button takes its tone (emerald, rose, primary),
a tinted fill and a matching border; unpressed buttons are neutral and gain a
primary border on hover.

**Production semantics that stay:**

- Each is an `aria-pressed` toggle button with an accessible name that
  includes the action and the member's id.
- Verdict buttons are **disabled** while a mutation is in flight, once the
  session is finalised or terminal, and when the server is not connected. A
  verdict's state changes only after the server acknowledges it. The repaint
  updates existing nodes in place so **keyboard focus is not lost**.
- **Read-only members** show no buttons, and only members with an existing
  proposal are actionable. What a read-only member *does* show depends on the
  group kind, and the difference is deliberate (`armorMemberStatus` in
  `review_ui.js`):
  - **Exact group.** A "Read-only" badge and the disposition as text. Only when
    the member also carries a later proposal does it add "Also proposed X in
    Proposals", the **current verdict**, and the proposal reason. A survivor or
    retained member with no later proposal shows **no** "Current verdict" line,
    so the redundant "Unreviewed" disclosure stays absent (asserted in
    `tests/test_server_browser.py`).
  - **Same-stat group.** An "Existing proposal" or "Read-only comparison"
    badge, the proposed action and reason when there is one, and **always** the
    current verdict.
- A verdict is a session decision, not a tag. A veto suppresses one proposal
  without tagging the item `keep`, changing an existing DIM tag, or re-ranking a
  group; an approval only makes the proposal eligible for the finalised
  reviewed CSV. Nothing changes in DIM until that CSV is imported.
- **Stale state is production behaviour.** If the report or the verdicts have
  changed under the page, the server rejects the request, the page re-fetches
  the report, and it announces that the action was **not applied** and must be
  repeated. The prototype has no equivalent, and no optimistic update may
  replace it.

**Delta.** The prototype's three labels and pressed treatment match production's
names already. The prototype has no `aria-pressed`, no accessible ids, no
disabled state and no read-only variant; production's are required.

### 5.12 Production controls with no prototype design

Two delivered features had **no equivalent in the original prototype**. The
#171 extension designs the Proposals-side instances; the armor-side instance is
still undesigned. Neither may be dropped in a migration, and the contract's
tokens and banner rules apply when either is restyled.

- **DIM search text.** Visible, copy-able DIM `id:` search text for armor groups
  (#117) and for filtered weapon proposals (#150). The weapon-proposal search
  and the static loadout searches are designed in
  [5.13.5](#5135-dim-search-panel). The armor-group search has no visual design and
  stays as delivered, except that
  [#177](https://github.com/tonym999/vault-cleaner/issues/177) adds a per-chunk
  Copy button to it.
- **Bulk verdicts.** The Proposals surface has **Approve all shown**, **Veto all
  shown** and **Unset all shown**, which act on the currently filtered proposals
  through the same acknowledged mutation path as a single verdict. Designed in
  [5.13.3](#5133-scope-line-and-bulk-verdicts). Armor group bulk verdicts
  remain owned by [#115](https://github.com/tonym999/vault-cleaner/issues/115).

### 5.13 Proposals surface

Designed for [#171](https://github.com/tonym999/vault-cleaner/issues/171) by
extending the prototype (see [Provenance](#2-provenance)); the owner approved
the look from screenshots on 2026-09-26. It replaces the original prototype's
placeholder Proposals card.

The surface lists **every** proposal in the report: weapons, armor and ghosts.
Weapons get the richest treatment because only weapon decisions carry the
structured explanation that
[#170](https://github.com/tonym999/vault-cleaner/issues/170) added
(`decision.explanation`, snapshot schema 3). Armor and ghost rows use the same
anatomy without it ([5.13.11](#51311-armor-and-ghost-rows)).

#### 5.13.0 What data each part needs

The design is not all presentation. Two panels and the source chips need data
the snapshot does not carry today, and a planner must treat them as schema work
in a separate ticket.

| Part | Data source | Status |
| --- | --- | --- |
| Reason label, why, keep instead, what you give up, caveats | `decision.explanation` (#170); `reasonLabel` in `review_ui.js` | Available |
| Action, protection, locked, equipped, in loadout, location, class, Tuning Mod Slot | Existing decision fields read by `itemsFromSnapshot` | Available |
| "Keep copy also proposed" chip | #170's `partner_also_proposed` caveat; equivalently, `kept_id` has its own decision in the snapshot | Available |
| "That copy is not proposed" line and "Go to copy" link | `kept_id` and whether it has its own decision | Available |
| Wishlist-source chips on the row ([5.13.7](#5137-proposal-row)) | Structured per-decision source keys | **Not in the snapshot.** #170 puts source names only inside the `why` sentence; the snapshot's `wishlists` list names the run's configured sources, not a decision's |
| Comparison with the copy to keep ([5.13.8.1](#51381-comparison-with-the-copy-to-keep)) | For *both* copies: the authoritative exact-roll perk identity projected by Python (see 5.13.8.1), tier, masterwork tier, crafted level, curated-match count and location | **Not in the snapshot.** Only `kept_id` and #170's prose `keep_instead` exist |
| Wishlist evidence panel ([5.13.9](#5139-wishlist-evidence)) | `WishlistEntry` fields in `wishlist.py`: `source`, `family`, `polarity`, `tier`, `tier_status`, `activities`, `activity_basis` | **Not in the snapshot.** #170 renders only source names, inside the `why` sentence |
| Capacity progress ([5.13.4](#5134-capacity-progress-slot)) | #140 Child 6 | Slot only; no issue exists yet |
| Reserved reasons ([5.13.10](#51310-reserved-reason-slots)) | #140 Child 5, [#172](https://github.com/tonym999/vault-cleaner/issues/172) | Slot only |

Until the missing data exists, an implementation shows the available parts and
omits the source chips and the comparison and evidence panels. It must not
reconstruct any of them in the browser, for example by parsing the `why` or
`keep_instead` prose, or by reading raw `Perks N` export cells.

#### 5.13.1 Page order and the surface switch

**Intent.** Header, intake, report, then the **surface switch** (Proposals /
Armor duplicates), then the filter panel for the selected surface, then that
surface's content.

**Decision (owner, 2026-09-26).** The surface switch sits **above** the filter
panel. Each surface has its own filters, so the switch comes first and the panel
beneath it belongs to the selected surface. This applies to both surfaces.

**Deltas.** Production orders the panels filters → surface selector → surface
content (`review_server.html`). The original prototype put its tab strip after
the filter card as well. Both change. The switch keeps its delivered semantics:
a labelled group of `aria-pressed` buttons, never `tab`/`tablist`
([5.4](#54-filter-panel-tabs-and-segmented-controls)).

On the Proposals surface, the content below the filters is, in order: the
capacity slot, the scope line with bulk verdicts, the DIM search panel, and the
proposal queue (grouped or flat).

#### 5.13.2 Filter panel

**Intent.** One section card headed "Filters", with the muted line **"Filters
select individual proposals"** at the far end of the heading row, as a
counterpart to the duplicates surface's "groups stay intact". Top to bottom:

1. A full-width **search** field with a visible label ("Search name or
   instance id") and a leading search icon.
2. **Action as count chips:** the label "Action", then **All N**, **Junk N**,
   **Review N**. The active chip uses the prototype's active-chip treatment plus
   a semibold weight.
3. A grid of **labelled selects**: Kind, Reason, Class, Protection, Loadout,
   Session verdict. One column on phones, two from small, three from large,
   six from extra large. Every select has a visible label above it.
4. After a hairline: the label "View", then a two-button **segmented control**,
   **Grouped by action, kind, reason** and **One sortable table**, each with a
   small decorative icon. **Reset filters** is a secondary button at the far
   end.

**Decision (owner, 2026-09-26).** Action is a chip group, not a select.

**Production semantics that stay:**

- Facet options come from the report. The Reason select shows `{label} (count)`
  and filters by the reason **slug** (`reasonOptions`, #170). Kind values are
  the report's section kinds (`weapons`, `armor`, `ghosts`), not the prototype's
  singular sample values.
- Protection keeps its five values (any, protected, unprotected, soft only,
  hard only), Loadout its three, and Session verdict its four.
- The action chips and view buttons are `aria-pressed` toggles in a labelled
  group, exactly one pressed at a time.
- Filters select individual proposals. There is no whole-group rule on this
  surface.

**Deltas.** Production renders Action and View as selects (View's options read
"grouped by action/kind/reason" and "one sortable table") and lays all controls
out in one wrapping `.controls` row. Production's selects already have labels;
the prototype's original filter card did not.

#### 5.13.3 Scope line and bulk verdicts

**Intent.** A slim card below the capacity slot. On the left, "Showing **N** of
**M** proposals" with the numbers in monospace. On the right, "Bulk on N shown"
followed by three secondary buttons: **Approve all shown**, **Veto all shown**,
**Unset all shown**.

**Decision (owner, 2026-09-26).** The bulk buttons move from the filter panel to
this line, next to the count they act on.

**Production semantics that stay:**

- Bulk verdicts act on exactly the currently filtered proposals, through the
  same acknowledged mutation path as a single verdict, with the same stale-state
  handling ([5.11](#511-verdict-controls-and-read-only-members)). No optimistic
  update: the prototype's instant bulk change is illustrative.
- The buttons are disabled while a mutation is in flight, when the server is
  not connected, once the session is terminal, and once it is finalised
  (`mutationControlsDisabled` in `review_server.js`).
- The count text is a polite live region.

#### 5.13.4 Capacity progress slot

**Intent.** A dashed, primary-outlined card titled **"Vault space progress"**
with a gauge icon and the monospace eyebrow "Slot · #140 Child 6". It holds four
equal cells, each with an uppercase label and an empty value: **Proposed**,
**Accepted**, **In finalised output**, **Observed in DIM**. One muted line
beneath: the four states are never merged into one number.

**What is designed:** position (first thing below the filters) and the rule
that the four states stay **visually separate**. **What is not designed:** what
each cell counts, units, targets, progress bars, and whether the card appears
before Child 6 lands. An implementation ships no capacity card until Child 6
defines its content.

#### 5.13.5 DIM search panel

**Intent.** A card with a disclosure button, **"DIM search for the N shown
weapon proposals"**, and a muted line at the far end stating how many chunks the
search needs. Expanded, it shows each chunk of the search text in a bordered
monospace block that wraps anywhere, a **Copy** button for each chunk, and a
**"Loadout searches"** list of the three static DIM searches, each with its
meaning.

**Decision (owner, 2026-09-26): per-chunk Copy buttons.** Every chunk of every
generated DIM search gets its own user-initiated Copy button: the weapon
proposals search here, and each armor duplicate group's search in both modes.
The behaviour, including accessible names with chunk position, the #148-style
fallback that selects the chunk, a polite status, zero clipboard calls on
render or filter, and no side effects, is owned by
[#177](https://github.com/tonym999/vault-cleaner/issues/177). That issue
explicitly amends #150's exclusion of clipboard writes for user-initiated copies
only. The prototype's single icon-only button does not carry over: with several
chunks it would be ambiguous.

**Production semantics that stay** (the "Cross-check in DIM" panel,
`review_server.js`):

- The weapon search covers exactly the weapon proposals matching **all** current
  filters, including Action and Session verdict, split into chunks of at most
  `DIM_QUERY_SAVEABLE_MAX` (2048) characters with a split notice. Every chunk
  stays a visible, labelled, read-only `<textarea>`.
- The copy that stays verbatim: the count line, the empty message ("No weapon
  proposals match the current filters."), the error message, the warning that
  the search **includes every matching proposal, junk and review, any session
  verdict, and items still suppressed by an active saved veto, unless the
  current filters exclude them, so it is not an approved-junk list**, and the
  sentence that rendering or selecting the text changes nothing. Copying a chunk
  (#177) keeps that sentence true. The prototype omits the warning and
  side-effect sentences; they stay.
- The three static loadout searches keep their labels and queries, and each has
  a read-only field and a named Copy button. Loadout membership is never written
  into Notes, so DIM remains the source of truth for it.

**Delta.** Production shows this as a separate "Cross-check in DIM" panel after
the filters: a heading, an explanation and the count, then the label, warning
and chunks inside a `<details>` that starts closed and remembers whether it was
open, then the loadout searches as labelled read-only inputs. The prototype puts
the whole panel between the scope line and the queue and makes the disclosure
the panel's own header. Production
also shows the static loadout searches on the Armor duplicates surface; see
[12](#12-open-questions).

#### 5.13.6 Grouped view: group card

**Intent.** One solid card per group. The header block has a monospace eyebrow
`ACTION · kind`, then the **reason label** as the title (16px, semibold), then
the reason **slug** in small muted monospace when it differs from the label. At
the far end is a monospace "N items" chip, singular when 1. The rows follow as a
list separated by hairlines.

**Production semantics that stay:**

- Groups are keyed by (action, kind, reason) and ordered **junk before review,
  then largest first, then alphabetically** (`groupItems`, matching the terminal
  summary). The prototype's group order is sample order and not a rule.
- The group's heading exposes the same facts as production's heading text
  (`ACTION {label} [{slug}] ({kind}) — N item(s)`): action, label, slug, kind
  and count. The structured layout may split them visually, but a screen reader
  must still reach all five from the group's heading and header block.
- Armor and ghost groups have no label, so the title is the slug in monospace.

**Delta.** Production renders each group as a heading line followed by a table.

#### 5.13.7 Proposal row

**Intent.** Three zones in a row from the large breakpoint, stacked below it:

1. **Identity.** An expand button with a chevron and the item name, then the
   full instance id in small monospace, then a muted "type · location" line.
2. **Reason.** A wrapping line of chips: the **action badge** first, then flag
   chips for protection (`{level} protection — {reason}`), locked, in loadout,
   the wishlist source(s) (only once structured source data exists; see
   [5.13.0](#5130-what-data-each-part-needs)), and Tuning Mod Slot for armor.
   Below that are the
   reason label (14px, medium) and the `why` sentence (12px, muted).
3. **Verdict.** Approve, Veto and Unset buttons, with "Verdict: {text}" beneath,
   right-aligned from the large breakpoint.

Row-level rules:

- **Action badge is a disposition, not a verdict.** It is outlined, never
  filled, with uppercase monospace text: **JUNK** in the junk hue (production
  `--junk`, orange-coral) and **REVIEW** in the review hue (amber). Pressed
  verdict buttons are filled, so the two differ by shape and text as well as hue
  ([4.3](#43-rules-that-hold-in-any-theme)).
- **Caveat hint.** A collapsed row with caveats shows one amber line: "N caveats
  before you decide" (singular when 1).
- **Decision (owner, 2026-09-26): exception chip.** When the copy to keep is
  itself proposed, the collapsed row shows an amber chip with a warning icon,
  **"keep copy also proposed"**. Otherwise the collapsed row adds nothing about
  the copy to keep. The full `keep_instead` text appears only in the expanded
  panel.
- When the row is expanded, the `why` line moves into the panel and is not
  repeated in the row.
- A vetoed row takes a faint rose tint in addition to its "Vetoed" text.
- Ids and names wrap. They are never truncated or ellipsised.

**Production semantics that stay:**

- Verdict buttons follow [5.11](#511-verdict-controls-and-read-only-members):
  `aria-pressed` toggles with accessible names including the item name and id,
  Unset pressed when there is no verdict, disabled under the same conditions as
  bulk verdicts, repainted in place after acknowledgement without losing focus.
- The verdict text is `sessionVerdictText`, including its persisted-veto forms
  (for example "Active persisted veto still suppresses this item"). The
  prototype's one-word "Verdict: X" line is sample text; the longer production
  strings must fit and wrap there.
- The expand button carries `aria-expanded` and `aria-controls` pointing at the
  panel.

**Delta.** Production renders each proposal as a table row with separate
columns and a "▸ Name" toggle. #170 put the label and `why` in one Reason cell.

#### 5.13.8 Expanded panel

**Intent.** An inset panel on the page-background tone, indented under the row,
containing in order:

1. **Explanation.** Three columns from medium width, stacked below it: **Why
   suggested**, **Keep instead**, **What you give up**, each with a monospace
   eyebrow over 14px text. With no copy to keep, "Keep instead" reads "No copy
   is named." in muted italics.
2. **Status of the copy to keep**, under the keep-instead text. It is either the
   line "That copy is **not proposed** in this report." or an amber outlined
   badge, **"ALSO PROPOSED · {ACTION}"**, followed by a link, **"Go to copy
   {short id}"**, that moves to that copy's row.
3. **"Before you decide"**, shown only when there are caveats. An amber
   left-ruled box lists #170's caveats in #170's order, each with a decorative
   icon: info for review only, gem for Exotic, lock for locked, layers for
   loadout, warning for copy also proposed. The text carries the meaning.
4. **Comparison with the copy to keep** (5.13.8.1), when the proposal names one
   and the data exists.
5. **Wishlist evidence** (5.13.9), when the data exists.
6. A collapsed disclosure, **"DIM note, tag and hash"**.

**Production semantics that stay:** every definition the delivered detail row
shows remains reachable, in the disclosure if not elsewhere: the note and DIM
tag vault-cleaner would write, the surviving copy (`kept_id`), protection, the
existing DIM tag and notes, the flags (locked, equipped, in a loadout), and the
hash. Armor rows keep their evaluation block. All report text is inert:
`textContent` or autoescaped, never markup.

##### 5.13.8.1 Comparison with the copy to keep

Needs snapshot data ([5.13.0](#5130-what-data-each-part-needs)). Applies to the
reasons that name a copy to keep: `dupe-lower`, `dupe-tie`, `coverage-dominated
by` and `coverage-uncovered vs`. It does not apply to wishlist trash.

**Intent.** A two-member instance of the comparison matrix
([5.10](#510-comparison-matrix)): axes are rows, and the columns are **This
copy** (id · "proposed {action}") and **Keep instead** (id · "retained" or "also
proposed {action}"). Candidate axes are Perk roll, Tier, Masterwork tier, Crafted
level, Curated wishlist matches and Location.

- Only **differing** axes get a row, with the axis name emphasised in the
  primary colour. Identical axes are summarised in one muted line: "Same on
  both: …".
- **Perk identity comes from Python, never from raw export cells.** For each
  copy, Python projects the proven exact-roll prefix that duplicate grouping
  uses (`_exact_roll_prefix_parts` in `rules/dupes.py`): the normalized tuple
  behind `exact_roll_fingerprint`, and the positionally aligned display names
  behind `exact_roll_display_prefix`. Cells at and after the first measured
  tracker boundary (tracker, current socket, mod, masterwork and memento cells)
  are excluded, and selected `*` markers are normalized away. The browser
  compares the **normalized** values position by position and shows the
  **display** names. If either copy has no proven prefix, the row says the rolls
  cannot be compared and shows no perk cells.
- In the Perk roll row, perks are small bordered cells in prefix order. A cell
  whose normalized value differs from the other copy's in the same position is
  highlighted with a primary tint, primary border and medium weight, so it is
  not shown by colour alone. For an exact duplicate the normalized prefixes are
  equal by definition, so that row never appears. The prototype's four sample
  perk cells per copy are illustrative.
- **Narrow containers:** below the small breakpoint each differing axis becomes
  its own bordered block ("This copy: …", "Keep instead: …"). The page never
  scrolls sideways. This follows production's container-width orientation rule
  ([8](#8-responsive-behaviour)).

#### 5.13.9 Wishlist evidence

Needs snapshot data ([5.13.0](#5130-what-data-each-part-needs)).

**Intent.** Under the eyebrow "Wishlist evidence", one bordered card per
evidence entry (two columns from small width), each a definition list:

| Term | Value | When uncertain |
| --- | --- | --- |
| Source | configured source key, monospace (for example `aegis_trash`) | — |
| Rates it | Trash / Keep | — |
| Curation | curation family, monospace | — |
| Tier | "Tier D" when `tier_status` is `parsed` | "Not declared by this source" (`not-declared`); "Tier text not recognised" (`unrecognized`) |
| Activity | "PvE · from the source setting" or "… · from the entry's tags" (`activity_basis`) | "Unknown" (`activity_basis` `unknown`) |

Uncertain values are muted italics **and** say in words why they are uncertain.
A field is never left blank. Where a proposal rests on several entries,
including entries that disagree, all of them are shown side by side. #170's
source names in the `why` sentence stay; this panel adds structure and does not
replace them.

#### 5.13.10 Reserved reason slots

Two reasons from #140 Child 5
([#172](https://github.com/tonym999/vault-cleaner/issues/172)) have reserved
places: **a locked weapon suggested as "unlock and junk"**, and **Aegis trash that
conflicts with a Choosy Voltron keep roll**.

**What is designed:** each is a normal group card and row with a dashed primary
outline, the placeholder title "Reserved reason slot · #172" and a "Slot" note
in the expanded panel. They reuse the existing row anatomy: the locked chip, and
for the conflict, two evidence cards side by side.

**What is not designed:** labels, why / keep instead / give up copy, caveats,
action, protection, group order, and whether either case is junk or review. All
of that belongs to #172. The slot styling is a design-time marker and ships in
no implementation.

#### 5.13.11 Armor and ghost rows

Same row and panel anatomy. Without an explanation the reason zone shows the
slug in muted monospace where the label would be, and there is no `why`, caveat
hint or explanation block. Armor rows show Tuning Mod Slot as a chip, using the
delivered wording ("Candidate: X · Selected: Y" from `tuningComparison`), and
keep their evaluation block in the panel. The prototype's "This pass has no plain-English explanation yet" line is
sample copy.

#### 5.13.12 Flat view

**Intent.** One bordered, horizontally scrollable table in a card. Sortable
header buttons for Name, Instance id, Kind, Class, Location, Action and Reason,
each with a sort icon (up or down when active, a neutral double arrow
otherwise). Protection and Verdict are unsorted columns. The Reason cell holds
the label and, beneath it, the `why` sentence. The Action cell holds the badge
plus the in-loadout chip. Expanding a row inserts the same panel (5.13.8) as a
full-width row beneath it.

**Production semantics that stay:** `aria-sort` on each sortable header;
accessible sort names; sorting by Reason sorts by slug; the sortable column set
comes from `COLUMNS` in `review_ui.js`, so production's **Tuning Mod Slot**
column stays until a later decision (see [12](#12-open-questions)).

**Delta.** Production marks the active sort with "▲"/"▼" text; the prototype
uses icons. Either is acceptable, provided the direction is also exposed through
`aria-sort`.

#### 5.13.13 Empty state

"No proposals match" / "Try a broader search or reset the filters.", with a
primary **Reset filters** button, in the [9](#9-empty-states) panel style. This
applies only when a report is loaded and has proposals. "No report yet" and "the
report has no proposals" are different messages, chosen from server state.

#### 5.13.14 Production control inventory

Every control on the delivered Proposals surface, and where it lands:

| Production control | Outcome |
| --- | --- |
| Search name or instance id | Designed (5.13.2), visible label kept |
| Action select | **Changed** to count chips (5.13.2) |
| Kind, Reason, Class selects | Designed (5.13.2); options and semantics unchanged |
| Protection, Loadout, Session verdict selects | Designed (5.13.2); values unchanged |
| View select (grouped / flat) | **Changed** to a segmented control (5.13.2) |
| Approve / Veto / Unset all shown | **Moved** to the scope line (5.13.3); semantics unchanged |
| Reset filters | Designed (5.13.2) |
| Surface selector (Proposals / Armor duplicates) | **Moved** above the filters (5.13.1); semantics unchanged |
| Sortable column headers | Designed (5.13.12) |
| Row expand toggle | Designed (5.13.7) |
| Row Approve / Veto / Unset | Designed (5.13.7); [5.11](#511-verdict-controls-and-read-only-members) semantics unchanged |
| Verdict presentation text, including persisted-veto forms | Unchanged text, new position (5.13.7) |
| "in loadout" badge | Designed as a chip (5.13.7) |
| Protection column | Chip in grouped view, column in flat view (5.13.7, 5.13.12) |
| Tuning Mod Slot column | Chip in grouped view; flat column **unchanged** (open, 12) |
| Detail definitions (why, keep instead, give up, caveats, note, tag, surviving copy, protection, existing tag and notes, flags, hash) | Designed (5.13.8); none removed |
| Armor evaluation detail | **Unchanged** |
| Weapon DIM search: count, chunks, warning, side-effect text, empty and error messages | Designed (5.13.5); copy unchanged |
| Copy control on generated DIM search chunks | **New:** one Copy button per chunk (5.13.5), owned by #177; also on armor-group searches |
| Static loadout DIM searches and Copy buttons | Designed (5.13.5); labels and queries unchanged |
| Report tiles, fingerprint, overrides, reconciliation, session note | **Unchanged** ([5.3](#53-report-metric-cards-and-copy-hierarchy)) |
| Session actions, uploads, status line | **Unchanged** ([5.1](#51-page-shell-header-and-status), [5.2](#52-upload-cards-and-session-actions)) |

## 6. Icon roles

The prototype renders sixteen distinct Lucide icons (a seventeenth, `Check`, is
imported and never used). **The contract is the role, not the package.** No icon
library is a requirement.

| Role | Prototype icon | Requirement |
| --- | --- | --- |
| Application mark | shield with check | Decorative |
| Weapons / Armor / Ghosts upload | zap / shield with check / sparkles | Decorative next to a text label |
| Drop target | cloud upload | Decorative |
| Finalise / Reset / Export / Copy | file-check / rotate-ccw / download / copy | Decorative next to a label. Copy is icon-only, so it needs an accessible name |
| Search / Filter / Select | search / filter, sliders / chevron-down | Decorative, non-interactive |
| Clear filters | x | Decorative next to a label |
| Review-only banner / session note | sparkles / terminal | Decorative |
| Help / More actions | circle-help / ellipsis | Icon-only. Would need names; no production behaviour exists |
| Empty states | file-check / search | Decorative |

Requirements that hold for any implementation:

- **No icon carries meaning alone.** Icon-only controls need an accessible name;
  otherwise the icon is hidden from assistive technology.
- **Delivery must respect the server CSP** (`SERVER_CSP` in `server/app.py`).
  It sets `default-src 'none'` and then allows only `script-src 'self'`,
  `style-src 'self'` and `connect-src 'self'`. There is **no `img-src` or
  `font-src`**, so *every* `<img>`, CSS image and web font is blocked, including
  same-origin and `data:` ones. Inline `<svg>` markup is permitted; an inline
  `style` attribute on it is not.
- The prototype reuses one glyph for two roles (the shield for both the
  application mark and Armor, sparkles for both Ghosts and the review-only
  banner). Distinct roles should get distinct shapes.

## 7. Accessibility and focus

**Delivered semantics are a floor, not a target.** The following stay exactly as
production has them:

- Skip link; `h1` that can take focus; `role="status"` with `aria-live="polite"`
  for status, upload and scope text.
- `aria-pressed` toggle buttons for surface, group kind and verdicts; no
  `tab`/`tablist` roles.
- `aria-expanded` and `aria-controls` on disclosure buttons.
- Every control has a real, visible label; icon-only controls a name.
- A verdict repaint never rebuilds the focused element.

**Focus treatment.** The prototype gives buttons and icon buttons a 2px primary
ring on `:focus-visible` and gives fields a primary border plus a soft ring on
focus. Production has a single global rule: a 3px accent outline with a 1px
offset on `:focus-visible`. The contract keeps the *global rule as the floor*:
every interactive element, in every theme, needs a focus indicator that is
clearly visible against its background. The prototype's two-tier ring is an
acceptable refinement only if it is at least that visible.

Gaps in the prototype that must be closed by any implementation:

- The upload card's input is visually hidden; the card needs a `:focus-within`
  indicator.
- The search field and both selects have **no labels**, only a placeholder or a
  default option.
- Tabs and verdict buttons carry **no pressed state** in the accessibility tree,
  and the chips, tabs and verdict buttons define no explicit focus style at all.
- The pressed and active states differ mostly by hue; each also needs a
  non-colour cue (weight, underline, or text), as production has.
- Metric captions and eyebrows at 10 to 11px in the muted colour must meet
  contrast in both themes.

Browser and accessibility verification for any migration follows
[browser-verification.md](browser-verification.md).

## 8. Responsive behaviour

- **Page:** the gutter grows at the small and large breakpoints; nothing sets a
  `min-width` above the phone width except intentionally scrollable tables.
- **Upload cards:** stacked, then a row from the large breakpoint.
- **Metric cards:** one column, two from small, four from extra large.
- **Filter row:** stacked, then a three-column grid (wide search, 220px, 170px)
  from large.
- **Stat spike:** stacked, then three columns from small.
- **Comparison matrix:** horizontally scrollable inside its own bordered
  container; the prototype's minimums are 650px and 780px. Production's rule is
  stricter and stays: the orientation switches by *container* width with a
  per-member-count budget, so the page body itself never scrolls sideways.
- Ids, hashes, fingerprints and reasons wrap (`overflow-wrap: anywhere`); they
  are never truncated or ellipsised.
- Production's phone rules (`max-width: 640px` in `review.css`: full-width tiles
  and search, stacked view buttons) are retained.

## 9. Empty states

**Intent.** A dashed, rounded, card-toned panel with a tall minimum height,
centred: an icon (32px), a title (18px), one muted sentence, and optionally one
primary button.

**The prototype shows two instances.** The original Proposals-tab placeholder
("Proposal queue", pointing to the other tab) was superseded by #171.

| Instance | Prototype copy | Status |
| --- | --- | --- |
| No groups match the filters | "No groups match" / "Try a broader search or reset the filters." | Reasonable intent; real copy belongs to the implementation |
| No proposals match the filters | "No proposals match" / "Try a broader search or reset the filters." plus a **Reset filters** button | Designed in [5.13.13](#51313-empty-state) |

An empty state must say *why* it is empty and offer the next step. It must not
imply that nothing was found when the real cause is that no report has been
loaded; the server session state decides which message applies.

## 10. Candidate mapping to Jinja components

This is a **conceptual candidate** only. The final server-rendering route, the
fragment architecture, and whether any of this is adopted belong to the M10
Jinja rendering architecture spike, which this contract must precede. Jinja2 is
already present as a Flask dependency, so evaluating it adds no dependency.

| Prototype component | Candidate production unit |
| --- | --- |
| `SectionHeading` | shared Jinja macro or include |
| `UploadCard` | upload-card partial |
| Metric card | shared metric-card partial |
| `ScoreBars` | stat-spike partial |
| `ExactGroup` | exact-duplicate group partial |
| `TuningGroup` | same-stat group partial |
| `VerdictButton` | verdict-controls partial |
| Filters and tabs | shared review navigation and filter partials |
| Banner (tuning, info) | banner partial with a tone parameter |
| Comparison matrix | matrix partial, parameterised by member count and orientation |
| Empty state | empty-state partial |
| Session actions | session-actions partial |
| Proposals filter panel (search, action chips, selects, view control) | Proposals filter partial reusing the shared filter and chip macros |
| Scope line and bulk verdicts | scope-and-bulk partial |
| Capacity slot | capacity partial; content deferred to #140 Child 6 |
| DIM search panel | the existing cross-check markup as a partial; copy unchanged |
| Proposal group card | proposal-group partial (heading block plus row list) |
| Proposal row | proposal-row partial containing the verdict-controls partial |
| Expanded panel | proposal-detail partial |
| Comparison with the copy to keep | matrix partial, two-member case, with the stacked narrow variant |
| Wishlist evidence | evidence-card partial, one per entry |
| Flat table | sortable-table partial sharing the row's verdict and detail partials |

Constraints the spike must respect. These restate existing rules and are
**not** decisions:

- **Autoescape on, and no `|safe` on any report value.** The delivered UI builds
  nodes with `createElement` and `textContent` so hostile item names stay inert.
  A template route must reach the same guarantee.
- **`Id` and `Hash` stay opaque strings** through every template, attribute and
  script boundary; never a number, never parsed.
- **No inline `style` attributes and no inline scripts.** The CSP is
  `style-src 'self'` and `script-src 'self'`. Bar widths and matrix budgets stay
  in the stylesheet.
- **A verdict is repainted in place after acknowledgement.** Any fragment route
  that replaces DOM must not drop keyboard focus or race the server's revision
  checks.
- **No request ever supplies a filesystem path.**
- **Row ids and the "Go to copy" link.** Element ids built from instance ids
  (production already uses `vc-detail-{id}`) keep the id as an opaque string.
  The link's fragment target is that copy's row id, never text taken from
  `keep_instead`.
- **Packaging is not covered today for new resources.** `pyproject.toml`
  packages only top-level `*.css`, `*.html` and `*.js` for `vault_cleaner.ui`,
  and `scripts/check_wheel_install.py` requests only `/` plus three hard-coded
  assets (`review.css`, `review_ui.js`, `review_server.js`). A nested template
  directory, a dynamically loaded fragment, or a new asset type such as an
  `.svg` icon would be omitted from the wheel without that check noticing. The
  M10 implementation must update **both** the package-data configuration and the
  wheel proof so that every new template and asset is packaged *and* exercised.

## 11. Prototype defects not to inherit

Collected here so a later reader does not mistake them for design:

- Rendered page and token palette are dark only despite shell metadata that
  advertises both colour schemes; no light page palette exists.
- Inline-style bar widths (blocked by the CSP).
- Hard-coded two- and three-member grids.
- Unlabelled filter controls; no pressed or expanded state anywhere.
- No visible focus indicator on the hidden-input upload card.
- Status notice always emerald, even for errors.
- A green pill used for two different meanings (survivor and approved).
- Verdict controls on read-only members, and Member 1 assumed to be the survivor.
- An unused shadcn `Button` component containing `dark:` variants, while the
  custom `dark` variant is dead in the design-bearing page and stylesheet.
- The Report section's fingerprint `<code>` does not wrap, so it widens the
  page at phone width. The #171 extension fixed it in its copy; ids, hashes and
  fingerprints wrap ([8](#8-responsive-behaviour)).
- In the #171 extension's flat table, the verdict buttons wrap onto two lines
  inside a narrow Verdict column. An implementation should give that column
  enough width, or stack the buttons deliberately.
- Vercel Analytics rendered in production builds. It is a telemetry call to a
  third party. The durable rule is **no analytics, no telemetry and no remote UI
  resources**; the only outbound traffic the product permits is the explicitly
  documented static game-content download (wishlists and the public Bungie
  manifest), which `--no-wishlists` turns off (README, "Privacy").

## 12. Open questions

Recorded, not decided. None blocks this ticket.

1. **Light theme.** The prototype defines only a dark page palette despite its
   contradictory light/dark shell metadata. Production ships both.
   Which light values match the prototype's hierarchy is a decision for the
   implementation ticket, using [section 4.3](#43-rules-that-hold-in-any-theme)
   as the guardrail.
2. **Group-kind control.** Separate chips (prototype) or a segmented control
   (delivered)? Both keep the `aria-pressed` semantics.
3. **"Why grouped" callout.** Adopt a labelled callout for exact groups, or keep
   the delivered "identical axes" line and banner?
4. **Bar hue per role.** Three hues (prototype) or one hue with an opacity ramp
   (delivered)? The role word is required either way.
5. **Session actions.** Inside the intake card (prototype) or a separate labelled
   group (delivered)?
6. **`PLAN.md` has no M10 section yet.** This ticket is titled as M10 but the
   plan does not define it. Adding it is outside this ticket's scope.

Added by #171:

7. **Snapshot data for the source chips, comparison and evidence panels.**
   Which fields carry each decision's structured wishlist source keys, each
   copy's Python-projected exact-roll identity (normalized and display) plus
   tier, masterwork tier, crafted level, curated-match count and location, and
   each proposal's `WishlistEntry` evidence? That is a snapshot schema change
   for its own ticket ([5.13.0](#5130-what-data-each-part-needs)).
8. **"Go to copy" when the target is hidden.** If the current filters hide the
   copy to keep, or it sits in another group, does the link reset filters,
   expand the target, or say that it is filtered out?
9. **Static loadout searches on Armor duplicates.** Production shows them on
   both surfaces. The prototype shows them only inside the Proposals DIM panel.
10. **Tuning Mod Slot in the flat table.** Keep production's sortable column, or
    use the grouped view's chip?
11. **Reserved reasons.** Label, copy, action and order for the two #172 cases
    ([5.13.10](#51310-reserved-reason-slots)).
12. **Capacity progress content.** What each of the four cells counts. Timing
    is settled: no capacity card ships until #140 Child 6 defines its content
    ([5.13.4](#5134-capacity-progress-slot)).
