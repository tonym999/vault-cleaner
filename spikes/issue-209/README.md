# Issue #209 presentation performance spike

A measured copy of #206; nothing here ships and no production file changes.
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
```

The runner accepts only the fixed names above; screenshot switches and paths are
refused, protecting #206 evidence. The gate reports seven comparisons and fails
when any slice median exceeds production. Require two consecutive complete final
invocations; keep every invocation in the record, including incomplete attempts.
Stylesheet probes are diagnostic-only against #206 assets. Visual comparison uses
PNG bytes in memory: eight idle captures and two held-request captures; no image
is written. Evidence: [transcripts](../../docs/evidence/issue-209/README.md).
