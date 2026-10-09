# 2026-10-09 — #209 presentation performance gate implementation

Refs #209. Work on the existing `feat/issue-209-svelte-perf-gate` only.
Approved plan remains byte-identical and is never edited. No issue mutation or PR.
No `data/` file read; only synthetic fixtures and tracked sanitised armor fixture.
No package added, removed or re-versioned; both lockfile/package files match #206.

## Complete dispatch record

- User explicitly requested implementation and referred to issue dispatch
  https://github.com/tonym999/vault-cleaner/issues/209#issuecomment-6089962949,
  confirming approval at `3be17ac7d39d88cb01439edf328872f48051368e`.
- Immutable review base and this attempt's starting SHA:
  `3be17ac7d39d88cb01439edf328872f48051368e`.
- Issue #209 OPEN, enhancement, project vault-cleaner Status Todo, no milestone;
  tracker #138 OPEN. #206 merged through #208 at
  `d139a05306828c0a4d7e9ded211408b346dd7768`.
- Orchestrator: OpenAI GPT-6 Codex desktop runtime; exact model ID/native effort
  not exposed and not guessed.
- Planned and actual implementer: OpenAI `gpt-6.1-sol`, `high`, native Codex
  `collaboration.spawn_agent`; no re-selection.
- Independent adversarial review required; reviewer selected later by orchestrator.
- Workspace: `/home/raver/projects/personal/vault-cleaner`.
- Copy-only first implementation commit:
  `088218ba42ee29719ca7eee852e06ce218806ad6`. Recursive diff excluding dist and
  node_modules printed nothing. It contains exactly the 27 baseline frontend files.

## Baseline and measurement tooling

Runner sets #206's call-time frontend globals before importing each fixed proof;
source scanner globals also point at #209. It accepts exactly one fixed name and
cannot forward screenshots or a path. No frozen source is edited.
Gate uses unchanged S15 stamps; extra settled stamps are the second nested rAF.
Both pages use 1440x1000 light, same authenticated report, five alternating fresh
pages. CDP counters are diagnostic. The gate enforces S15's focus invariant on the
slice only; production focus loss is measured baseline behavior.

Gate invocation 1 was incomplete: one baseline slice sample then proof incorrectly
asserted focus identity for production. Captured, counted, corrected; no reroll
or exclusion of a complete comparison. Invocation 2 reproduced M1-M4 direction:
A1 198.1/158.2 ms; A3 27.1/9.6 ms; B3 176.0/19.9 ms; verdict style 138.7/3.1 ms.
All seven comparisons fail on the copy, as expected.
The unchanged S1 proof against the copy passed. Full pre-copy pytest first hit
sandbox socket/Chromium restrictions; escalated run passes 1342 in 32.52s.

## Step 1 and step 2 investigation

Step 1 retains complete presented values by equality, never a revision key, and
retains filters when reconciliation changes no value. Three added unit tests cover
one changed verdict, unchanged-revision state/overrides, and a changed snapshot.
35 frontend tests and the type check pass. Invocation 3 moves A3 from 27.1 to 17.4 ms
and A4 from 33.9 to 22.6 ms; script 29.4 to 16.1 ms. Navigation remains behind.

Eight diagnostic command invocations are accounted for: initial join/:has removal;
expanded disabled/theme families; direct-property replacement; narrowed disabled
rules; per-color/background/simple-selector families; transition removal; an
import-bootstrap failure; final fixed all-family command. Every tried family is
preserved in the final proof. Final baseline diagnostic: unchanged 59.5 ms,
join-scope 61.1, has 55.6, disabled 5.6, join-and-disabled 4.1, root-has 71.6,
direct 58.9, color 73.1, background 71.4, simple-selector 70.0, no-transitions 5.5.

Exact cause: daisyUI `.btn` sets transition-property to color, background-color,
border-color, box-shadow, transform, duration 0.2 s. The disabled selectors change
these on all 435 buttons twice. Changing transitions would change intermediate
presentation, so the orchestrator rejected it as diagnostic-only. No stylesheet
candidate was retained. Step 2 invocation 4 uses unchanged step-1 source and still
fails all seven comparisons. Allowed step 3 rendering containment is next.

Baseline tooling commit `a25e997e8c289e2adaa0ea180097091f4844a95b` keeps the
frontend byte-identical to the copy, making step 0 reproducible in a disposable
checkout. The next kept-step commit contains step 1 and step 2 captures. The gate's
warm Node projection diagnostic was added after invocation 4, outside timed windows;
this adds diagnostic output only, not a changed stamp or sample window.
