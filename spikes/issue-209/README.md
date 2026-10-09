# Issue #209 presentation performance spike

A failed measured copy of #206: **NO-GO**. Nothing here ships and no production file changes.
Only tracked synthetic and sanitised fixtures are used. Baseline #206 stays frozen.
Use Node 24 and the project's environment; browser proofs require pinned Chromium
and fail rather than skip when unavailable. No dependency differs from #206.

From the repository root:

```bash
(cd spikes/issue-206/frontend && npm ci && npm run build)
(cd spikes/issue-209/frontend && npm ci && npm run check && npm test && npm run build)
```

Every proof command, from the repository root:

```bash
.venv/bin/python spikes/issue-209/run_proof.py S1
.venv/bin/python spikes/issue-209/run_proof.py S2
.venv/bin/python spikes/issue-209/run_proof.py S3
.venv/bin/python spikes/issue-209/run_proof.py S4
.venv/bin/python spikes/issue-209/run_proof.py S5
.venv/bin/python spikes/issue-209/run_proof.py S6
.venv/bin/python spikes/issue-209/run_proof.py S13
.venv/bin/python spikes/issue-209/run_proof.py S15
.venv/bin/python spikes/issue-209/run_proof.py source
.venv/bin/python spikes/issue-209/proof_gate.py
.venv/bin/python spikes/issue-209/proof_styles.py
.venv/bin/python spikes/issue-209/proof_visual.py
.venv/bin/python spikes/issue-209/proof_traversal.py
```

The runner accepts only the fixed names above; screenshot switches and paths are
refused, protecting #206 evidence. S15 runs unchanged in an isolated child, with
unbuffered output and a fixed 900s verification limit. Timeout is FAIL, never a
skip; the Linux runner uses stable pidfd handles to close only that child's
browser/driver/process descendants, including detached orphans. The gate reports seven comparisons and fails
when any slice median exceeds production. Require two consecutive complete final
invocations; keep every invocation in the record, including incomplete attempts.
Stylesheet probes are diagnostic-only against #206 assets. Visual comparison uses
PNG bytes in memory: eight idle captures and two held-request captures. On a
difference, an explicit `--write-difference` flag preserves only the fixed
desktop-light baseline/candidate pair in `docs/evidence/issue-209/`. Default runs
write no image; no path input is accepted and no #206 image is overwritten. Evidence: [transcripts](../../docs/evidence/issue-209/README.md).

To preserve one required difference pair explicitly:

```bash
.venv/bin/python spikes/issue-209/proof_visual.py --write-difference
```

The candidate uses whole-group rendering containment: off-screen groups render as
approaching the viewport. The traversal proof accounts for the deferred work,
Long Tasks, geometry (>1px height/middle-element/scroll drift is FAIL) and keyboard jump, and compares full-report axe/contrast
coverage with #206. A failed gate is a NO-GO; nothing is tuned after the approved
stop condition. See the decision record for the final result.
