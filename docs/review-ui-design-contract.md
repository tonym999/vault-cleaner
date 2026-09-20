# Review UI design contract

Status: stable reference, owned by [#136](https://github.com/tonym999/vault-cleaner/issues/136).
Captured 2026-09-20 from the Next.js review prototype (see [Provenance](#2-provenance)).

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
| `app/layout.tsx` | Title, favicons, `color-scheme`, Vercel Analytics in production |
| `components/ui/button.tsx` | A shadcn `Button` with variants and sizes. **Never used by the page**, so it carries no design intent |
| Everything else | Scaffold: lockfile, icons, placeholder images |

It has one page and no server. Its title is "Vault Cleaner / Review". Only
`app/page.tsx` and `app/globals.css` carry design intent; the rest of the
archive was scaffolding.

The prototype is a **visual and component design source**. It is not the
production architecture. The production application remains the Flask
loopback review server, and the prototype's framework, styling toolchain,
icon package, analytics, and package manager are not dependency decisions
(see [section 3](#3-illustrative-not-authoritative), item 6).

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
- **The Proposals tab** is a placeholder card telling the user to switch tabs.
  The real Proposals surface is the delivered table.
- **`Shutdown is available in the desktop app shell.`** is false for this
  product. Shutdown is a real, delivered server action.
- **Ids and hashes.** The prototype's sample ids and hashes are in the real
  format. None are copied into this repository. Every example below uses
  obviously synthetic values, and every id and hash is an **opaque string**,
  never a number: `"9007199254740993"` is 2^53 + 1, which a JSON number would
  silently round.

## 4. Design tokens

The prototype is **dark only**: `color-scheme: dark`, a single token set, and the
Tailwind `dark` variant declared but never used. There is no light palette in
the prototype. Production already has both a light and a dark set. The tokens
below record the prototype's *dark-theme intent*; the light theme is not a
prototype fact and is recorded as an open decision in
[section 12](#12-open-questions).

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
(secondary), and **Shutdown** (secondary with a rose hover).

**Production semantics that stay:**

- each upload has a real visible label and its own polite status line for
  progress and errors (`vc-upload-status-*`);
- the file input accepts `.csv,text/csv` and the browser submits **file bytes,
  never a path**;
- the session actions are a labelled group, and their enabled state, the
  additional **Download again** action, and every label follow the server's
  session state (`idle`, `exports-loaded`, `reviewing`, `finalized`, `closed`).

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
  the "groups stay intact" line is real behaviour, not decoration.
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
stay.

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
- **Read-only members** show no buttons. They show a "Read-only" badge, the
  disposition as text, any existing proposal action and reason, and the current
  verdict as text. Only members with an existing proposal are actionable.
- Verdicts do not tag anything, change a DIM tag, or re-rank a group.

**Delta.** The prototype's three labels and pressed treatment match production's
names already. The prototype has no `aria-pressed`, no accessible ids, no
disabled state and no read-only variant; production's are required.

### 5.12 DIM search text

Production also has visible, copy-able DIM `id:` search text for armor groups
and for filtered weapon proposals (#117, #150). The prototype has **no
equivalent** and therefore no design for it. The existing production
presentation stays as it is, and the contract's tokens and banner rules apply
to it when it is restyled. It is not to be dropped in a migration.

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
- **Delivery must respect the server CSP.** It is `default-src 'none'`, with
  `script-src 'self'` and `style-src 'self'` (`server/app.py`). Inline `<svg>`
  elements are permitted; external images, remote fonts, and inline `style`
  attributes are not.
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

**The prototype shows two instances.**

| Instance | Prototype copy | Status |
| --- | --- | --- |
| No groups match the filters | "No groups match" / "Try a broader search or reset the filters." | Reasonable intent; real copy belongs to the implementation |
| Proposals tab | "Proposal queue" pointing to the other tab | **Placeholder, not a design.** The Proposals surface is the delivered table |

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
- **Packaging:** templates and assets must ship in the wheel
  (`scripts/check_wheel_install.py` covers this).

## 11. Prototype defects not to inherit

Collected here so a later reader does not mistake them for design:

- Dark only, with no light palette.
- Inline-style bar widths (blocked by the CSP).
- Hard-coded two- and three-member grids.
- Unlabelled filter controls; no pressed or expanded state anywhere.
- No visible focus indicator on the hidden-input upload card.
- Status notice always emerald, even for errors.
- A green pill used for two different meanings (survivor and approved).
- Verdict controls on read-only members, and Member 1 assumed to be the survivor.
- An unused shadcn `Button` component and a dead `dark` variant.
- Vercel Analytics rendered in production builds. It is a network call and is
  incompatible with a local, no-outbound-request product.

## 12. Open questions

Recorded, not decided. None blocks this ticket.

1. **Light theme.** The prototype defines only dark. Production ships both.
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
6. **`PLAN.md` has no M10 section yet.** This ticket is labelled M10 but the plan
   does not define it. Adding it is outside this ticket's scope.
