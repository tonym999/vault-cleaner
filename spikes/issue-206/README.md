# Issue #206 spike: Svelte 5 + TypeScript + Vite review frontend

This directory is **evidence for
[#206](https://github.com/tonym999/vault-cleaner/issues/206). Nothing here
ships.** It is outside `src/`, so it is not in the wheel, and outside
`tests/`, so CI does not run it. It exists so that every transcript in
[docs/evidence/issue-206/README.md](../../docs/evidence/issue-206/README.md)
can be rerun, and so that the decision in
[docs/frontend-framework-decision.md](../../docs/frontend-framework-decision.md)
can be checked against code.

Do not import it from production code. Data is the synthetic fixtures and
the tracked sanitised armor fixture under `tests/fixtures/`; no personal export
or file under `data/` is read.

## Try it

One command builds the frontend and serves the proof (Node 24 and the project
environment are needed):

```bash
.venv/bin/python spikes/issue-206/serve.py --fixture real
```

It prints two links. Open the first to sign in (it lands on the current
production page), then the second for the Svelte slice in the same session.
`--fixture real` loads all 893 sanitised armor rows (74 duplicate groups).
`--fixture armor_same_stat_four_ui.csv` loads the small synthetic four-member
group instead. With no option both commands retain their synthetic default.

## The development loop

```bash
.venv/bin/python spikes/issue-206/dev.py --fixture real
```

It starts the unmodified Flask review server with the sanitised fixture uploaded,
starts Vite's development server in front of it, and prints one link. Edit
any file under `frontend/src/` and the open page updates without a reload.
How the proxy satisfies the server's `Host` and `Origin` checks is written
at the top of [dev.py](dev.py) and measured in experiment S10.

### Make a change yourself

This is exercise 3 of experiment S14, done by hand:

1. Run the development loop and open the link. The pieces show the verdict
   `Unreviewed`.
2. Open [frontend/src/lib/view.ts](frontend/src/lib/view.ts) and find
   `VERDICT_LABELS`. Change `'Unreviewed'` to `'Not reviewed yet'` and save.
   The page shows the new wording at once.
3. Now delete that line instead of editing it and run `npm run check` in
   `frontend/`. The type check fails: `VERDICT_LABELS` must have a label for
   every verdict state.
4. Put the line back. For a larger change, apply
   `exercises/2-filter-facet.patch` (a second filter) and look at what it
   touched: `patch -p1 -d spikes/issue-206/frontend < spikes/issue-206/exercises/2-filter-facet.patch`,
   and add `-R` to undo it.

## What is here

| Path | Role |
| --- | --- |
| `frontend/` | The slice: a Vite project in Svelte 5 and TypeScript, styled with Tailwind CSS 4 and daisyUI 5. `src/lib/` holds the typed logic (`envelope.ts`, `api.ts`, `session.svelte.ts`, `view.ts`, `filters.ts`) and its unit tests; `src/components/` and `src/App.svelte` hold the markup; `src/contract/` holds envelope samples generated from the Python server |
| `probes/` | Experiment S7 only: one small page per shortlisted library (shadcn-svelte, Skeleton, daisyUI) and one in plain Svelte 5. `probes/src/lib/components/ui/` is what the shadcn-svelte CLI generated, unedited. The CLI's default preset also added the `@fontsource-variable/inter` web font (OFL-1.1); it was removed from the probe, so the probe measures the components and not the font |
| `spike_app.py` | Calls the unmodified production `create_app` and adds the built files to its fixed resource allow-list. Holds the mechanism for the pre-approved CSP additions, which the slice does not use |
| `contract.py` | Writes the envelope samples; `--check` fails when they are stale |
| `serve.py`, `dev.py` | The try-it command and the development loop |
| `harness.py`, `expected.py` | Shared proof plumbing, and the proofs' oracle: what must be shown, computed from the envelope with no code shared with the frontend |
| `check_source.py`, `proof_s*.py`, `wheel_server.py` | One script per experiment |
| `exercises/` | Experiment S14: three changes as patch files, each with a deliberately incomplete version. None is applied |

## Build and check the frontend

From `spikes/issue-206/frontend/`:

```bash
npm ci
npm run check    # svelte-check: TypeScript and Svelte diagnostics
npm test         # vitest: the typed logic, no browser
npm run build    # writes dist/, which is not tracked
```

The probes need their own install and build, from `spikes/issue-206/probes/`:
`npm ci && npm run build`.

## Proof commands

Run each from the repository root with the project environment
(`.venv/bin/pip install -e ".[dev]"`), after both builds above. Each prints
`RESULT: PASS` or `RESULT: FAIL` and exits non-zero on failure.

The browser proofs need the pinned Playwright Chromium
(`.venv/bin/python -m playwright install chromium`). When it is missing they
**fail**; they never skip.

| Experiment | Command | Browser |
| --- | --- | --- |
| Source rules | `.venv/bin/python spikes/issue-206/check_source.py` | no |
| Contract samples are current | `.venv/bin/python spikes/issue-206/contract.py --check` | no |
| S1 information parity | `.venv/bin/python spikes/issue-206/proof_s1_parity.py` | yes |
| S2 hostile content | `.venv/bin/python spikes/issue-206/proof_s2_hostile.py` | yes |
| S3 acknowledged state only | `.venv/bin/python spikes/issue-206/proof_s3_acknowledged.py` | yes |
| S4 finalise, reset, disconnect | `.venv/bin/python spikes/issue-206/proof_s4_lifecycle.py` | yes |
| S5 focus and live regions | `.venv/bin/python spikes/issue-206/proof_s5_focus.py` | yes |
| S6 layouts | `.venv/bin/python spikes/issue-206/proof_s6_layout.py` | yes |
| S7 CSP | `.venv/bin/python spikes/issue-206/proof_s7_csp.py` | yes |
| S8 installed wheel | `.venv/bin/python spikes/issue-206/proof_s8_wheel.py` | yes |
| S9 request envelope | `.venv/bin/python spikes/issue-206/proof_s9_envelope.py` | no |
| S10 development loop | `.venv/bin/python spikes/issue-206/proof_s10_devloop.py` | yes |
| S11 type drift | `.venv/bin/python spikes/issue-206/proof_s11_typedrift.py` | no |
| S12 code, tree and licences | `.venv/bin/python spikes/issue-206/proof_s12_code.py` | no |
| S13 accessibility | `.venv/bin/python spikes/issue-206/proof_s13_axe.py` | yes |
| S14 change exercises | `.venv/bin/python spikes/issue-206/proof_s14_changes.py` | no |
| S15 real scale | `.venv/bin/python spikes/issue-206/proof_s15_scale.py` | yes |

`proof_s6_layout.py --screenshots` also rewrites the PNG files under
`docs/evidence/issue-206/`. `proof_s15_scale.py --screenshots` writes four
full-page sanitised-report captures (all groups, both schemes at 1440/390 px).
S15 reports five-run medians beside production, and takes several minutes
because keyboard traversal and axe cover the whole page. The recommendation
is now bounded conditional on resolving its measured performance slowdown;
see the decision record.

`proof_s8_wheel.py` builds a wheel and a fresh virtual environment in a
temporary directory, as `scripts/check_wheel_install.py` does, so it needs
the same access to a package index or pip cache. `proof_s10_devloop.py` uses
port 5199 for Vite's development server.

Lint: `.venv/bin/ruff check spikes/issue-206`.
