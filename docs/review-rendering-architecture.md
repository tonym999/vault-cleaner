# Review rendering architecture

Status: decision record for
[#137](https://github.com/tonym999/vault-cleaner/issues/137), written
2026-10-03. It decides how the permanent review presentation should be
rendered. It changes no production code; the migration is the follow-up
tickets drafted in [section 8](#8-follow-up-ticket-drafts).

Every measured claim links to a transcript in
[docs/evidence/issue-137/README.md](evidence/issue-137/README.md). The proof
code is in [spikes/issue-137/](../spikes/issue-137/README.md). All data is
fake fixtures.

## 1. Decision

**GO, with the hybrid shape.** Move the report's presentation from browser
DOM construction to Flask/Jinja templates, split like this:

- **Jinja renders report-scoped fragments.** A fragment is fetched and
  installed only when the report changes (a new `report_revision` or
  `fingerprint`), and only if its revision headers equal the envelope the
  browser has adopted. A fragment is a function of the snapshot, the verdicts
  and the two revisions, and of nothing else in the envelope.
- **A verdict acknowledgement repaints in place** from the JSON envelope the
  unmodified `POST /api/verdicts` already returns. No fragment is fetched
  after a verdict, so the focused control is never rebuilt.
- **Session state that can change without a revision is painted from the
  envelope,** never rendered into a fragment: the frozen states
  (`state`) and which members have an active persisted veto
  (`override_status`). `POST /api/finalize` changes both and bumps nothing.
- **Filtering stays in the browser,** over `data-*` attributes the server
  writes. The browser hides groups and counts what it shows; it does not
  decide what a group's values are.
- **The shell stays one persistent document** holding the live regions and
  the filter controls. JavaScript keeps session state, requests, the
  mutation gate, reconciliation, focus and lifecycle.

The other three shapes each fail a gate ([section 2](#2-shapes-compared)).
The recommendation is to proceed with the migration in the order of
section 8, starting with the packaging and environment foundation.

Gate results for the chosen shape:

| Gate | Requirement | Result | Evidence |
| --- | --- | --- | --- |
| G1 | Rendered parity with production for the slice | Pass. Equal for all four fixtures, with and without verdicts; two declared differences | [E1](evidence/issue-137/README.md#e1-rendered-parity-gate-g1) |
| G2 | Every untrusted value inert; ids and hashes opaque | Pass | [E2](evidence/issue-137/README.md#e2-hostile-content-gate-g2), [template rules](evidence/issue-137/README.md#template-rules), [environment](evidence/issue-137/README.md#template-environment-and-the-shell-only-shape) |
| G3 | Server-acknowledged state only; stale fragments never installed | Pass. Equal revision pairs mean equal fragments, including across a finalise | [E3 and E4](evidence/issue-137/README.md#e3-and-e4-acknowledged-state-only-and-no-stale-fragment-gate-g3), [E11](evidence/issue-137/README.md#e11-finalise-and-reset-gate-g3) |
| G4 | Focus kept or restored; persistent live regions never recreated | Pass with in-place repaint (R1): the focused control is the same node | [E5](evidence/issue-137/README.md#e5-repaint-mechanisms-gate-g4) |
| G5 | Orientation switch and inactive-table accessibility unchanged | Pass. Same thresholds as `review.css:364-388`, same measurements as production | [E6](evidence/issue-137/README.md#e6-orientation-switch-on-jinja-markup-gate-g5) |
| G6 | Templates work from an installed wheel | Pass, once `package-data` names the template directory | [E7](evidence/issue-137/README.md#e7-templates-from-an-installed-wheel-gate-g6) |
| G7 | Auth, Host, Origin, `no-store` and the CSP unchanged | Pass. No header or directive differs on any spike route | [E8](evidence/issue-137/README.md#e8-request-envelope-and-headers-gate-g7) |
| G8 | Cleaner authority split; JavaScript removed outweighs what is added | Pass for the slice: no rule is in both languages (see [what stays in JavaScript](#what-stays-in-javascript-for-the-slice)), and 908 lines are replaced by 155. Limits in [section 7](#7-limits-of-the-evidence) | [E10](evidence/issue-137/README.md#e10-filter-ownership-gate-g8), [line ranges](evidence/issue-137/README.md#javascript-keepremove-line-ranges-gate-g8) |

No stop condition was reached. The proof wraps `create_app` without editing
it, needs no envelope field that is missing, no CSP change and no new
dependency.

## 2. Shapes compared

The four shapes are the issue's. "The slice" is the Armor duplicates surface.

| Shape | G1 to G3, G5 to G7 | G4 (focus, live regions) | G8 (authority, JavaScript) | Verdict |
| --- | --- | --- | --- | --- |
| **Shell only:** Jinja renders the shell, JavaScript builds the report | Not affected | Unchanged from today | Fails. The production shell has no value to interpolate: rendered through Jinja it equals its own bytes. No JavaScript is removed | Rejected |
| **Fragments, refetched after every mutation** (R2) | Pass (E3 and E4 ran for R2) | Fails the contract. Every list element, including the focused button, is destroyed; focus is then put on the equivalent new button | One extra request and one extra stale window per verdict | Rejected |
| **Whole page after a mutation** | Same templates and headers; parity and staleness were not measured for this shape | Fails. A new document recreates every live region, whatever the implementation does | Still needs script to post, because `form-action 'none'` blocks a form | Rejected |
| **Hybrid:** fragments when the report changes, in-place repaint after a verdict (R1), browser filtering | Pass | Pass. The focused control is the same node | Pass | **Chosen** |

Evidence for each rejection:

- Shell only:
  [environment transcript](evidence/issue-137/README.md#template-environment-and-the-shell-only-shape),
  last section. `review_server.html` is 3,881 bytes with no template tag.
- Refetch and replace:
  [E5](evidence/issue-137/README.md#e5-repaint-mechanisms-gate-g4), the two
  `r2` blocks: "list elements still in the document: 0 of 225". The design
  contract says *a verdict repaint never rebuilds the focused element*
  ([section 7](review-ui-design-contract.md#7-accessibility-and-focus)).
  Restoring focus afterwards does not meet that sentence.
- Whole page:
  [E9](evidence/issue-137/README.md#e9-the-whole-page-shape). Two things
  are separate here:
  - **Inherent to the shape.** The response is a new document, so
    `#vc-status` and the other live regions are new nodes (measured: the old
    status node did not survive). A message written into a region as the
    page loads is initial content, not a change to an existing region. A
    script-free post is blocked by `form-action 'none'` (measured), so the
    shape does not remove the script either. G4 fails on this alone.
  - **This implementation only.** The spike's `whole.js` calls
    `location.reload()` and does nothing else. It restores no focus and
    carries no filter text or status message across, so the measured loss of
    focus (to `body`) and of the unsent filter text shows what an unassisted
    reload does, not what the shape must do. An implementation could put
    focus back by key after load, as R2 was allowed to, and could carry
    filter text in the URL. Neither was built or measured. Chromium restored
    the scroll position by itself.

### Repaint mechanism

The verdict response stays JSON in all three candidates.

| | R1 in place | R2 refetch and replace | R3 refetch and patch |
| --- | --- | --- | --- |
| Focused control after the ack | Same node | New node, focus restored by key | Same node |
| List elements kept | 225 of 225 | 0 of 225 | 225 of 225 |
| Requests per verdict | 1 | 2 | 2 |
| Live regions | Same nodes, one status write | Same nodes, one status write | Same nodes, one status write |
| Tab order | Unchanged | Unchanged | Unchanged |
| Extra browser code | Paint: picks one of the server-rendered texts | Focus restoration by key | A tree-patching routine, with a fallback to R2 when shapes differ |

**R1 is chosen.** R2 breaks the contract's rule. R3 meets it, but adds a
second request and a second stale window per verdict and a patching routine
that R1 does not need; G8 decides between R1 and R3.

**Announcements preserved by construction.** All three mechanisms leave the
shell alone, so `#vc-status`, `#vc-reconciliation` and `#vc-duplicate-scope`
are the same nodes before and after, and each acknowledgement is one text
write to `#vc-status`, as today. Under R2 a screen reader's reading position
inside the replaced list is not something the page controls. **Real
screen-reader output was not measured** for any mechanism.

### Filter ownership

| | (a) server renders all, browser hides | (b) server filters from query parameters |
| --- | --- | --- |
| Matches production for every measured case, including recount-and-drop | Yes | Yes |
| Requests per filter change | 0 | 1 |
| Works after the server has stopped | Yes, as production does | No |
| JavaScript for the two measured filters | 62 lines | 27 lines |
| Python for the two measured filters | 0 lines needed (see the note below) | 63 lines |
| Where `duplicateScopeText` lives | JavaScript only | Python only |
| Where facet option counts and labels live | JavaScript only | Python only |

**(a) is chosen.** Production filters with no server
([E10](evidence/issue-137/README.md#e10-filter-ownership-gate-g8), "after the
server has stopped"), which matters after a `--once` finalisation and during a
disconnect, when the report stays readable. (b) would take that away, and
would turn every keystroke in the search box into a request with its own
stale window. (b) leaves 35 fewer lines of JavaScript for the two measured
filters (27 against 62) and needs 63 in Python; that does not outweigh a
lost behaviour, so the choice rests on the measured behaviour and not on a
preference.

Production does more than match and count: when the group kind changes it
recounts each facet's options for that kind and drops a selected value the
kind lacks, with a reconciliation message (`review_server.js:263-275`,
`:1284-1296`). Both candidates implement that for the Class facet and both
match production on it, options and message included. The first version of
this spike did not, and its option counts were rendered in Python while the
browser filtered; that put one count in both languages and diverged from
production.

**Where option counts live, under (a): in JavaScript only.** The browser
counts groups per facet value from the `data-*` attributes of the groups in
the selected kind, words the option label, and drops a stale selection.
In a production design under (a), Python would render no facet options.
Under (a), then, Python decides each
group's normalised values and writes them as attributes; the browser
compares attributes, counts, and words the scope sentence, the option labels
and the dropped-filter message. No rule is in both languages.

**The spike as built does not look like that, and the "0 lines" figure
needs reading with care.** One template and one context builder serve both
candidates, so every fragment, including the default one that candidate (a)
fetches, carries the parts only (b) uses: a server-counted
`<select data-vc-part="class-options">` block, and the `data-scope-text` and
`data-dropped-class` attributes. `_reconciled_class`, `_class_options`,
`_filtered` and `scope_text` in `context.py` run on every render. The (a)
page ignores all of it and counts in JavaScript (E10 compares what it
shows), so its behaviour is right, but the Python count code still executes
on the (a) path. The line figures are counted between the
`[filters-a]` and `[filters-b]` markers in the spike's files. "0 lines" for
(a) means that none of the Python between the `[filters-b]` markers is
*needed* by (a), not that none runs; fix round 1 moved the closing
`[filters-b:end]` marker in `context.py` down to take in `_class_options`
and `_reconciled_class`, which is what attributes them to (b). Production
under (a) would omit the (b)-only parts from the template and the builder.

## 3. Template and resource layout

### Proposed production layout

```text
src/vault_cleaner/
├── server/
│   ├── templating.py          # the environment (see below)
│   ├── presentation/          # one pure context builder per fragment
│   │   └── armor_duplicates.py
│   └── app.py                 # GET /fragments/<fixed name> routes
└── ui/
    ├── review.css
    ├── review_server.js       # session, requests, seam, paint, filters
    └── templates/
        ├── shell.html         # the persistent document served at /
        ├── armor_duplicates.html
        ├── _armor_group.html  # macros: header, stat spike, both matrices
        └── _verdict.html      # macros: verdict controls, read-only status
```

- **Environment.** `jinja2.Environment` built explicitly, not Flask's:
  `autoescape=True` unconditionally, `undefined=StrictUndefined`, a loader
  over a fixed tuple of template names read through `importlib.resources`,
  and **empty allow-lists for filters and globals.** Deleting `safe`, `int`
  and `float` is not enough: `tojson`, `urlize` and `xmlattr` return
  `Markup` (`tojson` output closes a double-quoted attribute),
  `filesizeformat` and `round` convert to a number, and the `lipsum` global
  returns `Markup`. The slice needs no filter; a later template that does
  must add it to the allow-list by name. Flask's own environment
  escapes by file extension (off for `.j2` and `.txt`), renders a misspelt
  key as nothing, and searches a directory
  ([transcript](evidence/issue-137/README.md#template-environment-and-the-shell-only-shape)).
  No request value reaches the loader.
- **Routes.** Each fragment is its own fixed `GET` rule, registered like the
  other routes in `create_app`. There is no path converter and no generic
  template or static route. A fragment route takes the session lock, reads
  `session_metadata(session)` and `revision_headers(session)` together,
  builds the context, renders, and sets the two revision headers.
- **Packaging.** `pyproject.toml` gains `"templates/*.html"` for
  `vault_cleaner.ui`. Without it a nested directory is left out of the wheel
  ([E7](evidence/issue-137/README.md#e7-templates-from-an-installed-wheel-gate-g6)).
  `scripts/check_wheel_install.py` must then check every allow-listed
  template is a package resource and request each fragment route.
- **Template rules,** enforced by a scan of the template bytes
  ([transcript](evidence/issue-137/README.md#template-rules)): every
  interpolation inside a tag is in a quoted attribute; no filter outside the
  environment's allow-list (so none today), no `{% filter %}` block, no
  `Markup`, no `{% autoescape %}`; no interpolation inside a URL-bearing
  attribute (`href`, `src`, `action`, `formaction`, `srcset`, `poster`,
  `ping`, `data`, `xlink:href`), because escaping does not stop
  `javascript:`; no `style=`, `on…=` or inline script; no include, extends or
  import with a non-literal name; the files on disk are exactly the
  allow-list.
- **One stylesheet rule is missing today.** `review.css` gives
  `.armor-section-head` `display: flex`, which defeats the `hidden`
  attribute. Browser-owned filtering needs `[hidden] { display: none
  !important; }` (the spike's `spike.css`).

### Template-context contract for the slice

`build_context(envelope)` is a pure function
([context.py](../spikes/issue-137/context.py)). Every value is a `str`, a
`bool`, or a list or mapping of them; revisions and counts are converted to
`str` in Python, and no template applies a filter.

**Envelope inputs.** The context reads `snapshot`, `verdicts`,
`report_revision`, `verdict_revision` and `fingerprint`, and nothing else.
It does not read `state` or `override_status`
([section 4](#state-that-changes-without-a-revision)).

Top level:

| Key | Type | Source in the envelope |
| --- | --- | --- |
| `report_revision`, `verdict_revision` | `str` | `report_revision`, `verdict_revision` |
| `fingerprint` | `str` | `fingerprint` (empty when `null`) |
| `total_groups`, `total_pieces` | `str` | counts of the two group lists and their `members` |
| `sections` | list of `{kind, heading, rule, groups}` | exact groups first, then same-stat, each in snapshot order |

The builder also emits four keys that only candidate (b) of
[filter ownership](#filter-ownership) uses. Under the chosen design they
would not exist:

| Key | Type | Source |
| --- | --- | --- |
| `class_options` | list of `{value, label}` | each group's `guardian_class`, counted over the requested kind |
| `dropped_class` | `str` | the requested class, when the requested kind has no group of it |
| `scope_text` | `str` | group and piece counts and the requested filters |
| `filtered_empty` | `bool` | there are groups and the requested filters match none |

Per group (`sections[].groups[]`):

| Key | Type | Source |
| --- | --- | --- |
| `dom_id` | `str` | `group_kind` + `:` + `group_id` |
| `kind`, `filter_kind` | `str` | `group_kind` |
| `member_count` | `int` | `len(members)`; printed, never computed on |
| `name`, `archetype`, `type_text`, `class_text`, `tier_text`, `hash_text` | `str` | `name`, `item_archetype`, `type`, `guardian_class`, `tier`, `hash`, with the `none/unknown` and `unknown` fallbacks |
| `pieces`, `kind_text` | `str` | member count; group kind |
| `spike` | `{tier5, rows or tiles, zero_summary}` | `stats`, `tier` |
| `banner` | `{warn, text}` | group kind, `tuning_mod_slot`, member count |
| `identical_line` | `str` | comparison axes on which members do not differ |
| `extras` | list of `(label, value)` | `spirit_signature`, `seasonal_mod`, `holofoil` |
| `has_junk` | `bool` | a member's `proposal_action` (exact) or current decision (same-stat) is `junk` |
| `axes` | list of `{label, tuning, cells}` | member fields; only axes that differ, plus Tuning Mod Slot for same-stat |
| `guardian_class` | `str` | normalised `guardian_class`, for filtering |

Per member (`groups[].members[]`):

| Key | Type | Source |
| --- | --- | --- |
| `id` | `str` | `members[].id`, required to be a string |
| `dom_id` | `str` | group kind + `:` + `id` |
| `number`, `location`, `label` | `str` | position; `location`; `disposition` (exact) or the current decision's `action` (same-stat) |
| `can_verdict` | `bool` | exact: `disposition` is `proposed_junk`/`proposed_review` and `proposal_action` agrees; same-stat: the same section has a `junk` or `review` decision for this `id` and the group's `hash` |
| `verdict` | `str` | the envelope's `verdicts` |
| `texts`, `current_texts` | mapping of verdict to `str` | constant wording for a member with no active persisted veto |
| `persisted_texts`, `persisted_current_texts` | mapping of verdict to `str` | constant wording for a member with one; the browser chooses between the two sets |
| `names` | mapping of verdict to `str` | group kind and `id` |
| `status` | mapping or `None` | read-only members: `disposition`, the current decision's `action` and `reason` |

Three points about this contract:

- **Eligibility is read, not derived.** For an exact group it is the
  member's `disposition` and `proposal_action`. For a same-stat group it is
  the presence of a decision in the same section's `decisions`, which is what
  `POST /api/verdicts` itself accepts. The builder joins on `id`; it ranks
  and groups nothing.
- **The builder fails closed.** A non-string id or hash, an unknown
  `group_kind` or `disposition`, or a proposal that disagrees with its
  decision raises. Through the route, measured for a hostile `disposition`,
  the production error handler answers with its bare `internal_error` 500,
  naming neither the field nor the value
  ([E2](evidence/issue-137/README.md#e2-hostile-content-gate-g2), last
  block). A hostile `group_kind` and a numeric id are shown to raise in the
  builder (same transcript, "code-path fields"); the proposal-mismatch case
  is not exercised by any proof.
- **Key order is not the wire's.** `session_metadata` returns a `dict` in
  insertion order; the browser receives it through `jsonify`, which sorts
  keys. The builder must sort `stats` itself, or the zero-stat line prints
  in a different order from production. E1 found this.

## 4. State and repaint flow

### Who owns what

| State | Owner |
| --- | --- |
| Report, groups, members, order, dispositions, eligibility, verdicts, revisions | Server (unchanged) |
| Text and structure of every report region | Server, through templates |
| Every text a member's verdict can show (three verdicts, with and without an active persisted veto) | Server; rendered once as `data-*` on the node |
| Which verdict is current | Server; the browser reads `verdicts` in the adopted envelope |
| Which members have an active persisted veto | Server; the browser reads `override_status` in the adopted envelope |
| Whether the session is frozen | Server; the browser reads `state` in the adopted envelope |
| Adopted envelope, in-flight gate, connection and terminal state | Browser |
| Selected surface, group kind, facet and search values, sort, expanded rows | Browser |
| Focus, scroll position, generated DIM search output | Browser |
| Comparison orientation | CSS container queries (unchanged) |

### Report load or change

1. The browser adopts an envelope (from `GET /api/report`, an upload, or a
   reset). Adoption is what it is today.
2. If `report_revision` or `fingerprint` changed, it fetches each report
   fragment.
3. It accepts a fragment only if `Vault-Cleaner-Report-Revision` and
   `Vault-Cleaner-Verdict-Revision` equal the adopted envelope's. Otherwise
   it discards the response unparsed, re-reads the envelope, and tries again,
   at most three times; then it treats the session as disconnected and keeps
   what is on screen.
   The pair is enough because a fragment is a function of the snapshot and
   the verdicts only: `report_revision` moves whenever the snapshot does,
   and `verdict_revision` whenever the verdicts do. Two fragments with equal
   headers are therefore equal
   ([E11](evidence/issue-137/README.md#e11-finalise-and-reset-gate-g3): the
   bytes are identical across a finalise).
4. It parses an accepted fragment with `DOMParser` into an inert document,
   imports the nodes, and replaces the region's children. It never assigns
   `innerHTML`. One delegated listener on the persistent host handles
   clicks, so installed nodes need no binding.
5. It paints verdict state, persisted-veto wording and the frozen gate from
   the envelope, applies the in-flight gate and the current filters, and restores focus by the control's stable key if the focused
   control was in the replaced region.

### Verdict

1. The browser disables verdict controls and posts to the unmodified
   `POST /api/verdicts`. Nothing else changes on screen
   ([E3](evidence/issue-137/README.md#e3-and-e4-acknowledged-state-only-and-no-stale-fragment-gate-g3):
   the server had committed and the page still showed `Unreviewed`).
2. On 200 it adopts the returned envelope and, for each cell with that
   member id, sets `aria-pressed` on the three buttons and writes the text
   the server rendered for the new verdict. Both orientations and every
   group the member appears in are repainted, because the paint walks the
   DOM by attribute and keeps no registry.
3. It re-enables the controls and writes one message to `#vc-status`.

### State that changes without a revision

`POST /api/finalize` sets `state` to `finalized` and replaces the override
store, so `override_status` gains active entries, and it changes neither
revision nor the fingerprint. Nothing rendered from those two fields could be
validated by the revision pair. So:

- **A fragment never depends on them.** It renders no `disabled` attribute
  and both wordings of every verdict text.
- **The browser paints them whenever it adopts an envelope:** it disables
  verdict controls when `state` is `finalized` or `closed` (as production's
  `mutationControlsDisabled` does today), and for each member picks the
  persisted-veto wording if `override_status` has an `active` entry for that
  id. No fragment is fetched.
- **Measured**
  ([E11](evidence/issue-137/README.md#e11-finalise-and-reset-gate-g3)): a
  page with the fragment installed, after a finalise elsewhere, reaches
  production's finalised presentation with no fragment request.

Reset is different: with a report loaded it bumps `report_revision`, so the
report-change flow replaces the fragment (measured in E11). Shutdown clears
the report; the fragment route then answers 409 like `GET /api/report`
(not exercised from the browser).

The first version of this spike rendered `disabled` and the persisted-veto
wording into the fragment. Review found that a finalise then left an
installed page showing `vetoed` with live buttons, and that two different
fragments carried the same revision pair.

### What stays in JavaScript for the slice

No rule: no eligibility, no wording of verdict text, no grouping or order.
What the browser does hold, each a lookup or a count over what the server
sent:

- which verdict a member has, from `verdicts`;
- which members have an active persisted veto, from `override_status`
  (production's `persistedVetoIds`, `review_server.js:71-79`, stays);
- whether the session is frozen, from `state`;
- which groups match the selected filters, how many are shown, the scope
  sentence, and each facet's option counts and labels.

The mapping from a verdict to the pressed button is written twice, once in
the template and once in the paint. That is three attribute values, not a
rule.

### Stale state

- **`stale_verdicts`:** re-read the envelope, repaint in place, announce that
  the action was not applied. No fragment is fetched: structure depends only
  on the report.
- **`stale_report`:** re-read the envelope, then the report-change flow
  above, then the same announcement.
- The action is never replayed
  ([E4](evidence/issue-137/README.md#e3-and-e4-acknowledged-state-only-and-no-stale-fragment-gate-g3):
  the server's verdict revision is unchanged after reconciliation).

## 5. JavaScript keep/remove map

Line ranges are in `src/vault_cleaner/ui/`, at this branch's head, and each
is checked by
[`proof_js_map.py`](evidence/issue-137/README.md#javascript-keepremove-line-ranges-gate-g8).
`S` is `review_server.js` (1,793 lines); `U` is `review_ui.js` (1,851 lines).

| # | Responsibility | Current code | Lines | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Bootstrap and session establishment | `S:81-120`, `S:128-212`, `S:312-413`, `S:1773-1792` | 247 | **Keep.** In `applySessionEnvelope` (`S:312-413`) the two snapshot projections (`S:320-335`) are removed with the builders they feed |
| 2 | Uploads | `S:752-754`, `S:1483-1508`, `S:1760-1767` | 37 | **Keep** |
| 3 | Report fetching | `S:443-570`, `S:1509-1525` | 145 | **Keep,** and add the fragment fetch with its revision check (93 lines in the spike, with install, paint and focus) |
| 4 | Filters, sorts, search, group-kind navigation | `U:211-262`, `U:264-302`, `U:747-802`, `U:846-857`, `S:214-310`, `S:786-832`, `S:1212-1218` | 310 | **Keep, rewritten** to compare server-written `data-*` values and hide nodes. Normalisation and each group's facet values **move to Python.** Sort and grouping order for Proposals are not measured here |
| 5 | Verdict mutation and acknowledgement | `S:572-584`, `S:899-921`, `S:935-943`, `S:1526-1543`, `S:1556-1564`, `S:1737-1759`, `U:1168-1199`, `U:1790-1815` | 153 | **Keep** the mutation path. `paintRow` and `paintArmorMember` (`U:1168-1183`, `U:1790-1815`) are **replaced** by one generic paint; the verdict text wording (`sessionVerdictText`, `S:415-426`) **moves to Python**, while the lookup of active persisted vetoes (`S:71-79`) stays |
| 6 | Stale-state reconciliation | `S:760-776`, `S:944-1014`, `S:1544-1555` | 100 | **Keep.** `adopt` (`S:944-1014`) chooses between in-place repaint and a fragment fetch in place of `buildView`/`renderList` |
| 7 | Finalise, download, reset, shutdown | `S:585-601`, `S:777-785`, `S:851-877`, `S:1447-1482`, `S:1565-1736` | 261 | **Keep.** The session-action buttons (`S:1447-1482`) can **move to a template**; the logic stays |
| 8 | Focus and live regions | `S:603-610`, `S:755-759`, `S:833-850`, `S:878-898` | 52 | **Keep.** Focus restoration gains a stable key per control (`data-vc-key` in the spike); today armor verdict buttons have no id and a rebuild loses focus on them |
| 9 | Responsive comparison switching | none in JavaScript; `review.css:364-388`. The double build is `U:1641-1648` | 8 | **Move to template.** Both tables are rendered by the server; CSS chooses, as today |
| 10 | DOM construction: duplicate groups | `U:304-624`, `U:804-844`, `U:1201-1640`, `U:1773-1788` | 818 | **Remove.** Projection and derivation **move to Python**; markup **moves to templates** |
| 10 | DOM construction: proposals | `U:87-150`, `U:982-1166` | 249 | **Remove,** in the Proposals ticket |
| 10 | DOM construction: shell, metrics, filters, lists | `S:627-746`, `S:1015-1043`, `S:1219-1369`, `S:1370-1446`, `U:892-981` | 467 | **Remove:** the shell panel and filter controls **move to templates**; metrics **move to a template**; how they repaint after an acknowledgement is not decided here (see ticket 3) |
| 10 | DOM construction: DIM search text | `U:626-739`, `U:1650-1771`, `S:1044-1211` | 404 | **Keep for now.** It is browser-generated on demand and works offline. Its static panel markup moves to the template |

For the slice alone: the spike replaces 908 lines of production JavaScript
(`U:304-624`, `U:804-844`, `U:1201-1648`, `U:1773-1788`, `U:1790-1815`,
`S:1376-1431`) with 93 lines of fragment seam and 62 lines of filtering in
JavaScript, a 474-line context builder and 187 lines of templates. The total
is not much smaller (816 lines against 908, with only two of six filters
written); the point is where it lives. The 321 lines at
`U:304-624` validate a snapshot the browser must treat as untrusted, and
re-correlate proposals it did not compute.

## 6. Findings

**Security.**
[E2](evidence/issue-137/README.md#e2-hostile-content-gate-g2): with every
string in the envelope hostile, autoescaped output installed through
`DOMParser` and `importNode` created no element, opened no dialog and tripped
no CSP directive, and equalled production's `textContent` DOM. Escaping is
one rule for text and for quoted attributes; the template scan guarantees
there is no unquoted one. With escaping deliberately off, elements appeared
but nothing ran: the parsed document is inert and the CSP blocked the image
and its handler. `Id` and `Hash` stayed byte-identical strings through
attributes, text and the verdict request. The environment has no filter and
no global, and the scan rejects any filter and any interpolated URL
attribute
([environment](evidence/issue-137/README.md#template-environment-and-the-shell-only-shape),
[template rules](evidence/issue-137/README.md#template-rules)); no committed
template needed either.

**Packaging.**
[E7](evidence/issue-137/README.md#e7-templates-from-an-installed-wheel-gate-g6):
templates render and serve from a non-editable wheel once `package-data`
includes them. Today's setting silently omits a nested directory, and
today's wheel proof would not notice.

**CSP and request envelope.**
[E8](evidence/issue-137/README.md#e8-request-envelope-and-headers-gate-g7):
routes added to the app `create_app` returns are covered by its
`before_request` and `after_request`. No directive changes. Jinja needs no
inline style or script.

**Accessibility, focus and live regions.**
[E5](evidence/issue-137/README.md#e5-repaint-mechanisms-gate-g4): with R1
the focused control and all three live regions are the same nodes after an
acknowledgement, and tab order is unchanged. A fragment install on a report
change replaces the list; focus is restored by key, which is better than
today, when armor verdict buttons have no id.

**Responsive ownership.**
[E6](evidence/issue-137/README.md#e6-orientation-switch-on-jinja-markup-gate-g5):
the switch is CSS container queries today and stays so. No JavaScript
measures layout. Server-rendered markup with the same classes and
`data-member-count` flips at the same container width as production, and the
inactive table is out of the tab order and the accessibility tree. The
server renders both tables; it does not choose one.

**Parity.**
[E1](evidence/issue-137/README.md#e1-rendered-parity-gate-g1): the only
differences are production's empty `class=""` attributes and the spike's
`data-vc-*` attributes.

## 7. Limits of the evidence

- **No screen reader was run.** Node identity and write counts are measured;
  what is spoken is not.
- **Chromium only,** the pinned headless build. Firefox and WebKit were not
  measured.
- **One slice.** Proposals, uploads, metrics and session actions were not
  rendered. In particular:
  - the **metrics** region changes on every verdict and is computed in
    JavaScript today (`reviewCounts`, `approvedOutputItems`). Neither way of
    repainting it (in place from the envelope, or a refetched fragment) was
    measured;
  - **sorting and grouping** of Proposals were not prototyped either way;
  - a Proposals **verdict filter** changes membership on a verdict. Hiding
    rows should cover it; that was not measured.
- **Two of the six duplicate filters.** Group kind and Class were measured,
  including the per-kind recount and drop. Search, slot, archetype and
  tuning slot were not. The Tuning Mod Slot facet counts pieces, not groups,
  and matches any member of a same-stat group (`U:760-769`, `U:783-794`);
  that was not written or measured.
- **The whole-page experiment is one unassisted implementation**
  ([section 2](#2-shapes-compared)). Its template has no paint step, so it
  would show neither the frozen state nor the persisted-veto wording.
- **Finalise was driven from outside the page.** E11 posts
  `/api/finalize` and then has the page adopt the envelope. The spike has no
  Finalise button, download or `--once` handling.
- **The `closed` state** was not exercised from the browser.
- **G3 rests on an invariant that was not exhaustively tested:** that the
  revision pair changes whenever the snapshot or the verdicts change. E11
  measures finalise and reset; E3 and E4 measure verdicts and a re-upload.
  Not every mutation path was walked.
- **The spike's fragments carry candidate (b)'s parts** on every render
  ([filter ownership](#filter-ownership)); no proof renders a fragment
  without them.
- **R3's fallback** (replace when the fragment's shape differs) exists in the
  spike but no proof exercises it.
- **The armor DIM search panel** is rendered as static markup; its buttons do
  nothing in the spike.
- **Hostile values the slice never prints** (`note`, `original_notes`,
  `tag`, wishlist and scoring fields) were replaced but appear nowhere, so
  E2 says nothing about them beyond the escaping rule being the same for
  every value.
- **Line counts** compare a spike with production code. The spike's builder
  and templates have no tests; production code will be larger.
- **Performance** was not measured. Fragment sizes for the fixtures are in
  [E9](evidence/issue-137/README.md#e9-the-whole-page-shape); no large
  report was rendered.

## 8. Follow-up ticket drafts

**Drafts only. No issue has been created;** creating them needs the owner's
authorization. There is no M10 milestone and `AGENTS.md` forbids one-off
milestones, so the milestone is left for the owner. Each ticket follows the
handoff workflow and is independently shippable.

The issue names seven workstreams. Six tickets cover them; workstream 5
(browser-state integration) is merged into ticket 2, because the seam's
stale and focus handling cannot be exercised without a real fragment and was
measured on the Armor duplicates surface.

Order: 1 → 2 → 3 → 4 → 5 → 6.

### 1. M10: Jinja rendering foundation (environment, packaging, wheel proof)

- **Label:** `enhancement`. **Workstream:** 1.
- **Depends on:** #137.
- **Scope rule.** A hunk is in scope if and only if it: adds the explicit
  template environment under `src/vault_cleaner/server/`; adds
  `src/vault_cleaner/ui/templates/` holding the shell and serves `/` from it,
  byte-identical to today's response; adds `"templates/*.html"` to
  `package-data`; makes `scripts/check_wheel_install.py` check every
  allow-listed template is a package resource; adds the template-rule scan as
  a test, with the filter allow-list (empty unless a filter is argued for by
  name), the cleared globals and the URL-attribute rule; adds the `[hidden]`
  rule to `review.css`; or records the M10
  architecture in `PLAN.md` and the template rules in `AGENTS.md`.
- **Stop conditions.** The served shell differs by a byte; any new runtime
  dependency; any CSP change; a request value reaching the loader; Flask's
  own `render_template` being needed; a template needing a filter that
  returns `Markup` or converts to a number.

### 2. M10: Armor duplicates as a server-rendered fragment, with the browser fragment seam

- **Label:** `enhancement`. **Workstreams:** 4 and 5.
- **Depends on:** ticket 1, and on #152, #177, #116 and #115, which all
  change the Armor duplicates card: each merged first or explicitly
  re-sequenced by the owner.
- **Scope rule.** A hunk is in scope if and only if it: adds the Armor
  duplicates context builder and templates; adds the one fixed `GET`
  fragment route with revision headers; adds to `review_server.js` the
  fragment fetch with its revision check, install, generic verdict paint and
  keyed focus restoration; rewrites the six duplicate filters to compare
  server-written attributes; switches the Armor duplicates surface to that
  path; or adds the tests proving it (parity with the retired builders,
  hostile content, stale fragments, focus, orientation, and a finalise and a
  reset with the fragment already installed). **A fragment may read only
  the snapshot, the verdicts and the two revisions.** `state` and
  `override_status` are painted by the browser from the adopted envelope,
  and a test must show the fragment's bytes are unchanged across a finalise.
  Facet option counts and labels live in JavaScript only, and the fragment
  carries no server-counted options, scope text or dropped-filter value.
  The planner must also settle one owner for the counts in the scope
  sentence: in the spike `total_groups` and `total_pieces` are counted in
  Python and the shown counts in JavaScript.
- **Stop conditions.** A snapshot, envelope or verdict-protocol change; a
  rule needed in both Python and JavaScript; a verdict repaint that rebuilds
  the focused control; any filter that needs the server; any change to
  group membership, order or eligibility; a fragment whose content must
  depend on anything the revision pair does not cover, or a need for a new
  revision or header to validate one.

### 3. M10: shell regions as templates (uploads, session actions, metrics, filters, navigation, empty states)

- **Label:** `enhancement`. **Workstream:** 2.
- **Depends on:** ticket 2.
- **Scope rule.** A hunk is in scope if and only if it moves markup built at
  `review_server.js:627-746`, `:786-820`, `:1015-1043`, `:1219-1369` or
  `:1447-1482` into a template or fragment, or adds the test proving the
  moved region.
- **Gate the planner must measure and pass before choosing.** The metrics
  change on every verdict. This record's rule is that no fragment is fetched
  after a verdict; R3 was rejected partly for its second request and second
  stale window per verdict, and a metrics refetch would bring both back.
  The default is therefore **in-place paint from the envelope**, with the
  counts as lookups over data the envelope already carries. A refetched
  metrics fragment is allowed only if the planner measures it against the
  same checks as E3 to E5 and shows the count rule would otherwise have to
  exist in both languages. If neither option passes, stop.
- **Stop conditions.** A count the server cannot compute from the session;
  a count rule in both languages;
  a control that holds focus being rebuilt on acknowledgement; a live region
  being recreated; a lifecycle or finalisation change.

### 4. M10: Proposals surface as server-rendered fragments

- **Label:** `enhancement`. **Workstream:** 3.
- **Depends on:** tickets 2 and 3; #178 for the parts of contract section
  5.13 that need snapshot schema 4; #177.
- **Scope rule.** A hunk is in scope if and only if it moves Proposals
  projection (`review_ui.js:87-150`) to a Python context builder, Proposals
  markup (`review_ui.js:982-1166`) to templates, or adds the tests proving
  it. The planner must first measure who owns sort and grouping, and the
  verdict filter's membership change.
- **Stop conditions.** Sorting or grouping needing a rule in both languages;
  bulk verdicts needing a protocol change; any reconstruction of data the
  snapshot does not carry (contract 5.13.0).

### 5. M10: retire the imperative DOM builders and the tests that own them

- **Label:** `maintenance`. **Workstream:** 6.
- **Depends on:** tickets 2, 3 and 4.
- **Scope rule.** A hunk is in scope if and only if it deletes a function in
  `review_ui.js` or `review_server.js` with no remaining caller, or deletes
  or rewrites a test in `tests/test_review_ui_js.py` or
  `tests/test_server_ui_js.py` whose subject was deleted. Every deleted
  behavioural assertion must name the surviving test that covers it.
- **Stop conditions.** A deleted assertion with no surviving equivalent; a
  function that still has a caller; any behaviour change.

### 6. M10: final single-path gate (Playwright, wheel proof, documentation)

- **Label:** `maintenance`. **Workstream:** 7.
- **Depends on:** ticket 5. Coordinate with #96, which owns broad browser
  coverage.
- **Scope rule.** A hunk is in scope if and only if it: makes the wheel
  proof request every fragment route after uploading a fake fixture; updates
  `docs/browser-verification.md`, the design contract's section 10 and
  `PLAN.md` to the delivered architecture; or notes in
  `spikes/issue-137/README.md` that production has superseded it. The spike
  stays, because this record's evidence is rerun from it.
- **Stop conditions.** A second rendering path still reachable; a fragment
  route the wheel proof does not exercise; any product change.
