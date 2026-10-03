# Issue #137 spike: Jinja server-rendered review seam

This directory is **frozen evidence for
[#137](https://github.com/tonym999/vault-cleaner/issues/137). Nothing here
ships.** It is outside `src/`, so it is not in the wheel, and outside
`tests/`, so CI does not run it. It exists so that every transcript in
[docs/evidence/issue-137/README.md](../../docs/evidence/issue-137/README.md)
can be rerun, and so that the decision in
[docs/review-rendering-architecture.md](../../docs/review-rendering-architecture.md)
can be checked against code.

Do not maintain it, extend it, or import it from production code. The
production migration is planned by the follow-up tickets drafted in the
decision record.

## What is here

| File | Role |
| --- | --- |
| `render_env.py` | The explicit Jinja environment: autoescape always on, `StrictUndefined`, a loader over a fixed allow-list of template names, and empty allow-lists for filters and globals |
| `context.py` | A pure function from the schema-version-1 session envelope to the template context for the Armor duplicates surface. It reads the snapshot, the verdicts and the revisions, and neither `state` nor `override_status` |
| `spike_app.py` | Calls the unmodified production `create_app`, then adds the spike's resources and two `GET` routes |
| `templates/` | The slice: fragment root, group card, both matrix orientations, verdict controls, read-only status, and two documents (`shell.html`, and `whole_page.html` for experiment E9) |
| `static/spike.js` | The browser script: installs fragments, repaints verdicts, filters. It builds no report DOM |
| `static/whole.js`, `static/spike.css` | The whole-page experiment's script, and the one CSS rule browser-owned filtering needs |
| `harness.py` | Shared plumbing for the proofs: a live server thread, the pinned Chromium, a DOM projection |
| `wheel_probe.py` | Run by `proof_e7_wheel.py` inside the fresh environment it builds |

The spike page is served at `/spike/` beside the production page at `/`, by
the same app and session. Two query switches select an experiment and are
checked against fixed lists in the browser: `?repaint=r1|r2|r3` and
`?filters=browser|server`.

## Proof commands

Run each from the repository root with the project environment
(`.venv/bin/pip install -e ".[dev]"`). All data is the fake fixtures under
`tests/fixtures/`. Each proof prints `RESULT: PASS` or `RESULT: FAIL` and
exits non-zero on failure.

The browser proofs need the pinned Playwright Chromium
(`.venv/bin/python -m playwright install chromium`). When it is missing they
**fail**; they never skip.

| Experiment | Command | Browser |
| --- | --- | --- |
| Template rules | `.venv/bin/python spikes/issue-137/check_templates.py` | no |
| Environment comparison, shell-only shape | `.venv/bin/python spikes/issue-137/proof_environment.py` | no |
| E1 parity | `.venv/bin/python spikes/issue-137/proof_e1_parity.py` | yes |
| E2 hostile content | `.venv/bin/python spikes/issue-137/proof_e2_hostile.py` | yes |
| E3, E4 acknowledgement and staleness | `.venv/bin/python spikes/issue-137/proof_e3_e4_mutation.py` | yes |
| E5 repaint mechanisms | `.venv/bin/python spikes/issue-137/proof_e5_repaint.py` | yes |
| E6 orientation | `.venv/bin/python spikes/issue-137/proof_e6_orientation.py` | yes |
| E7 installed wheel | `.venv/bin/python spikes/issue-137/proof_e7_wheel.py` | no |
| E8 headers and refusals | `.venv/bin/python spikes/issue-137/proof_e8_headers.py` | yes |
| E9 whole-page shape | `.venv/bin/python spikes/issue-137/proof_e9_whole_page.py` | yes |
| E10 filter ownership | `.venv/bin/python spikes/issue-137/proof_e10_filters.py` | yes |
| E11 finalise and reset | `.venv/bin/python spikes/issue-137/proof_e11_finalize.py` | yes |
| Keep/remove line ranges | `.venv/bin/python spikes/issue-137/proof_js_map.py` | no |

`proof_e7_wheel.py` builds three wheels and one fresh virtual environment in
a temporary directory, as `scripts/check_wheel_install.py` does, so it needs
the same access to a package index or pip cache.

Lint: `.venv/bin/ruff check spikes/issue-137`.
