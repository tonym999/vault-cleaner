# Issue #210 spike: the redesigned Armor duplicates slice

This directory is **evidence for
[#210](https://github.com/tonym999/vault-cleaner/issues/210). Nothing here
ships.** It is outside `src/`, so it is not in the wheel, and outside
`tests/`, so CI does not run it.

It holds a copy of the #206 Svelte slice, redesigned as direction D (see
[docs/evidence/issue-210/README.md](../../docs/evidence/issue-210/README.md)),
and the proofs that run against it. The server, envelope, routes and CSP are
production's, unmodified. Data is the synthetic fixtures and the tracked
sanitised armor fixture under `tests/fixtures/`; nothing under `data/` is
read.

`spikes/issue-206/` is not edited. Its harness and proofs are imported from
here.

## Try it

Build once (Node 24 and the project environment are needed):

```bash
cd spikes/issue-210/frontend && npm ci && npm run build
```

There is no serve script of its own. The captures show the built page:

```bash
.venv/bin/python spikes/issue-210/capture.py /tmp/vc-210-captures real
```

## What is here

| Path | Role |
| --- | --- |
| `frontend/` | The slice. `src/lib/` is the typed logic carried from #206 and #209, plus four small helpers in `view.ts`. `src/components/` and `src/app.css` are the redesign. `src/components/ui/` holds the button and badge taken from shadcn-svelte 1.7.0 |
| `run_proof.py` | Runs a #206 proof, unedited, against this build. Makes the three adaptations the plan allows and no others; they are listed at the top of the file |
| `proof_csp.py` | In place of #206's S7 part 1, which reads daisyUI's `.btn` |
| `proof_axe.py` | In place of #206's S13: axe, focus contrast, and that no focus outline is clipped |
| `proof_layout.py` | Pieces side by side with aligned rows, groups of four stacked at 390 px, nothing outside the viewport, no text under 11 px, and the identical-tuning case |
| `proof_no_transition.py` | No verdict control animates; style recalculation per verdict, recorded |
| `capture.py` | Writes the captures in `docs/evidence/issue-210/captures/` |

## Run the proofs

From the repository root, after the build:

```bash
.venv/bin/python spikes/issue-210/run_proof.py S1
```

`run_proof.py` takes one of `S1`, `S2`, `S3`, `S4`, `S5`, `S6`, `S15` or
`source`. The four local proofs run directly:

```bash
.venv/bin/python spikes/issue-210/proof_axe.py
```

Every proof ends with `RESULT: PASS` or `RESULT: FAIL`. One run of each is
recorded verbatim in section 5 of the evidence README.

## Frontend checks

From `spikes/issue-210/frontend/`:

```bash
npm run check
```

```bash
npm test
```
