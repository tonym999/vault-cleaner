# Issue #213 spike: the timing gate on the redesigned slice

This directory is **evidence for
[#213](https://github.com/tonym999/vault-cleaner/issues/213). Nothing here
ships.** It is outside `src/`, so it is not in the wheel, and outside
`tests/`, so CI does not run it.

Result: **NO-GO for the redesigned slice as measured.** The record is in
[docs/frontend-framework-decision.md](../../docs/frontend-framework-decision.md#the-redesigned-slice-against-209s-gate-213);
the transcripts are in
[docs/evidence/issue-213/README.md](../../docs/evidence/issue-213/README.md).

Data is the synthetic fixtures and the tracked sanitised armor fixture under
`tests/fixtures/`. Nothing under `data/` is read. `spikes/issue-210/` and
`spikes/issue-206/` are not edited; their proofs are imported from here.

## What is here

| Path | Role |
| --- | --- |
| `frontend/` | A byte-for-byte copy of `spikes/issue-210/frontend/`. One change was tried on it and taken out, so it is still that copy |
| `proof_gate.py` | #209's gate proof (blob `a77c21f3` on `feat/issue-209-svelte-perf-gate`), with the verdict action added to each run's line and nothing else changed |
| `run_proof.py` | Runs a #206 or #210 proof, unedited, against this build, and prints the hashes of the files the server sent |
| `proof_attribution.py` | Where first-render time goes: a timeline, a profile, a no-framework floor, and one ablation per suspected cause |

## Build

Node 24 and the project environment are needed.

```bash
(cd spikes/issue-213/frontend && npm ci && npm run check && npm test && npm run build)
```

```bash
(cd spikes/issue-210/frontend && npm ci && npm run build)
```

The second build is only compared by hash.

```bash
(cd spikes/issue-206/frontend && npm ci && npm run build)
```

Only `build-check` needs the third: it serves #206's build as the wrong one.

## The gate

```bash
.venv/bin/python spikes/issue-213/proof_gate.py
```

Seven comparisons, slice beside the current page, five alternating fresh
documents each, medians. It fails if any slice median is above production's.
The bar is all seven in each of two consecutive complete invocations. Keep
every invocation in the record.

## The proofs

`run_proof.py` takes exactly one of these names and nothing else:

```bash
.venv/bin/python spikes/issue-213/run_proof.py S1
```

| Name | Proof |
| --- | --- |
| `S1` `S2` `S3` `S4` `S5` `S6` `S15` `source` | #206's, with the three adaptations #210's runner makes |
| `csp` `axe` `layout` `no-transition` | #210's own four |
| `build-check` | Negative control for the build check: serves #206's build and requires it to be refused |

`axe` takes about four minutes and `S15` about five.

## Attribution

```bash
.venv/bin/python spikes/issue-213/proof_attribution.py
```

Diagnostic only; it gates nothing. Every variant it measures is built in a
temporary directory or made by rewriting a served file in flight, and is gone
when it exits. It takes about four minutes.

Every proof ends with `RESULT: PASS` or `RESULT: FAIL`. A browser proof fails
when Chromium is missing; it never skips.
