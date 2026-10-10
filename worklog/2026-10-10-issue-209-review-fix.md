# 2026-10-10 — Issue #209 accessibility measurement review fix

## Authorization, pinned source and participants

This is the orchestrator-routed accepted review fix within the owner's authorized
#209 implementation phase. Branch: `feat/issue-209-svelte-perf-gate`; starting
and previous reviewed head: `cc29041e7a611f1dd3fa09763794b530d8d8c45c`.
Immutable review base and approved plan:
`3be17ac7d39d88cb01439edf328872f48051368e`; the plan stays untouched.
Verbatim copy commit remains `088218ba42ee29719ca7eee852e06ce218806ad6`.
No candidate optimization, frontend/CSS/projection/gate change, dependency change,
issue mutation or PR is authorized or performed in this round. Commit and push
are authorized on the allocated branch only, with `Refs #209`.

The complete original dispatch record is in the branch-added
`2026-10-09-issue-209-implementation.md`; it remains historical. Orchestrator:
OpenAI GPT-6 Codex desktop runtime, exact model ID/native effort not exposed.
Implementer requested/actual: OpenAI `gpt-6.1-sol`, native `high`, launched with
Codex collaboration; no re-selection. Independent reviewer requested/actual:
OpenAI `gpt-6.1-sol`, native `high`, fresh context through native collaboration,
read-only detached checkout `/tmp/vault-cleaner-209-review-cc29041` pinned at
`cc29041`. No cross-provider reviewer was callable. The initial 2026-10-09
review dispatch hit a usage limit and produced no review; it resumed on
2026-10-10. Initial sandbox restrictions during review were overcome through
ordinary escalation. No review durations were supplied, so none are invented.

## Every finding and disposition

The independent reviewer found exactly one P2, at the old
`spikes/issue-209/proof_traversal.py:121`: its supplemental accessibility
comparison checked only desktop light/dark, omitting S13/S15's narrow states.
Accepted and corrected in measurement/records. The independent reviewer had
no other P0/P1/P2/P3 findings. The orchestrator subsequently found one P3:
the bounded S15 parent labels every nonzero child result "exited before
completion", including a completed failing proof. Accepted: change only that
parent summary to "S15 child returned nonzero status". Timeout/exception
messages, nonzero behavior and historical captures are unchanged. Historical NO-GO outcomes remain failures rather than review defects
requiring candidate tuning. No planner amendment or scope expansion is needed.

The independent primary unchanged S15 completed once with exit 1: 1440 light,
1440 dark and 390 dark each report 581 incomplete contrast targets, 581 measured;
390 light reports 2862 incomplete and only 116 measured, with thousands left
unmeasured. The original selector-heavy initial tool output was truncated
(approximately 97k tokens); a clearly labelled count summary and remaining
captured stdout are appended to the evidence. Its missing bytes are not
reconstructed, and there was no second S15. The implementation's prior 900s
verification timeout and traceback remain unchanged as separate historical
facts; completion in review does not establish that timeout's cause.

Exactly two independent gate invocations are appended verbatim. Review 1 passes
all seven; review 2 fails A3 by +0.2ms (10.2/10.0) and B3 by +3.7ms (25.4/21.7).
The two-consecutive-passing-invocation bar still fails. Implementation invocations
1–6, including final 5/6 values, are preserved: **eight overall gate invocations**,
no extra gate invocation in this fix round, none discarded or rerolled.

## Complete incremental change inventory

- `spikes/issue-209/proof_traversal.py`: replace the second independent axe run
  with a passive wrapper of the same RUN_JS axe invocation, requesting complete
  result categories to count unique targets/groups without box/style reads.
  Reuse frozen S15.main for each fixed build's complete fixture/filter/far-down
  acknowledged-verdict/six layout-parity-Tab preparations. Temporarily substitute
  only its accessibility callback, timing no-op and result collection; restore
  every substituted global and #209 asset configuration in `finally`. Execute
  S13's exact 1440/390 × light/dark width/theme→settle→RUN_JS→full focus order;
  report per-state incomplete/measured/unmeasured/unique-target/group counts and
  lowest ratio. Fail on unexplained contrast, reduced counts or unmeasured
  targets. Close the earlier traversal browser before starting these fresh build
  preparations. Existing scrolling, geometry and keyboard measurements unchanged.
- `spikes/issue-209/run_proof.py`: one-line parent summary clarification for
  nonzero S15 child status; completed FAIL is no longer mislabelled incomplete.
- `spikes/issue-209/README.md`: document the four-state instrumented supplemental
  comparator, its exact preparation/transition order, no post-width warm-up,
  separate unchanged primary S15 and expected multi-minute duration.
- `docs/frontend-framework-decision.md`: retain NO-GO and all historical tables;
  add independent two-run comparison table, eight-invocation accounting and
  completed narrow-light S15 failure. Correct the old desktop-only equivalence
  claim and distinguish the corrected supplemental instrument from primary S15.
- `docs/evidence/issue-209/README.md`: append independent gate logs, disclosed
  partial S15 capture/count summary, reviewer inventory and this round's captured
  comparator/verification evidence. All prior evidence bytes remain untouched.
- This new dated worklog: record authorization, actual participants, finding and
  disposition, changes, every verification outcome and remaining limitations.

## Reviewer's independent inventory

Plan ancestry/content/head, 27-byte-identical-file copy, inclusion/frozen paths,
package/lock/worklog/sanitised-fixture guard/whitespace/no-data/clean-checkout
checks PASS. Root and spike Ruff PASS; pytest **1342 PASS**; required browser
**16 PASS, 3 deselected**, no skip. Clean #209 npm/type/**35 unit tests**/build
and clean #206 npm/build PASS. Unchanged S1–S6, S13 and source PASS. Unconditional
identity reuse negative control makes all three targeted tests fail as required.
Stylesheet diagnostic PASS, rejected no-transitions 7.1ms. Visual all five FAIL.
Traversal FAIL: +557px height, -560.2px middle element and focused last control
outside viewport; no scrolling Long Tasks. Its desktop-only coverage was
13137 targets/582 measured/444 controls, the scope omission accepted above.
Historical step measurements and explicit image-writing modes were not rerun.

## This round's verification

Initial spike Ruff found import ordering and unbound loop closures; imports were
sorted and closures explicitly bound before measurement. Final Ruff passes.
An ephemeral synthetic guard first used system python3 and failed import because
Flask is installed only in the project venv; no guard or browser ran in that
attempt. Repeated with `.venv/bin/python`, it verifies eight ordered width/theme
and focus calls, rejects a narrow-light unmeasured target and restores all
substituted globals. It passes; it is a guard test, not browser/parity evidence.
One corrected browser measurement is captured to
`/tmp/issue-209-review-fix-traversal.log`, complete stdout/stderr appended verbatim.
It exits 1 / RESULT FAIL. All eight 444-control focus laps pass; all states
except candidate 390-light report 581/581/0 incomplete/measured/unmeasured.
Unique targets/groups equal 13137/74 in every state; candidate 390-light instead
reports 2862/116/2746 and explicitly fails reduced/unmeasured coverage. No second
corrected measurement is made. Final repository checks follow below.


One additional two-scenario ephemeral probe passes: reduced target counts also
fail independently of unmeasured entries; each scenario checks all eight ordered
state/focus calls and global restoration. The P3 parent-summary probe preserves
status 1 and exactly prints the generic nonzero-status message. Neither probe
runs a browser or changes the repository test count. The standalone synthetic
commands are in the appended evidence.

The corrected comparator's first invocation reproduces primary S15's narrow-light
failure: candidate 2862 incomplete / 116 measured / **2746 unmeasured**, versus
baseline 581/581/0. Unique axe targets/groups still match (13137/74), so equal
unique counts alone cannot establish complete contrast coverage. No reroll or
candidate tuning followed this result.


Corrected traversal figures, same single invocation: slice 61 steps, largest
29.9ms, total 1611.0ms + navigation 146.9ms = 1757.9ms; production 59 steps,
largest 31.6ms, total 1818.7ms + navigation 174.7ms = 1993.4ms. No scrolling Long Tasks.
Slice height 60392→60949 (+557px), middle article 30118.2→29558.0 (-560.2px),
restored scroll 0. Production geometry unchanged. Last control focused after two
Shift+Tabs but outside viewport. Geometry/keyboard and coverage all independently
FAIL; these numbers are not another seven-comparison gate invocation.

No served-source lines added in this round; candidate still +34 non-blank lines,
1454 total, 35 frontend unit tests. Screen readers, find-in-page, other browsers,
other widths' performance and #210 presentation remain unmeasured. The full
initial review S15 selector line remains unavailable due to disclosed tool
truncation; the first corrected comparator captures exact unmeasured count 2746
without the enormous selector list. No frozen proof or candidate is adjusted.


Final required verification: both root/spike Ruff **PASS**; pytest **1342 passed
in 33.68s**; required browser **16 passed, 3 deselected in 12.79s**, no skip.
Both suites exit0, stdout/stderr captured together. Worklog checker **ok**,
fixture guard/whitespace/frozen-path/package comparisons clean. Both inclusion
commands print nothing (expected grep1). Evidence prefix at cc29041 is byte
identical; candidate/frontend/gate/plan incremental diffs empty. Both synthetic
command fences were extracted from the new evidence and rerun successfully,
confirming their reproduction text. No new repository test or dependency.

Clean npm/type/35-unit/build and unchanged S1–S6/S13/source were independently
rerun at the same unchanged candidate; not repeated here for this bounded
measurement/doc round. Primary S15 and seven-comparison gates were not rerun
by this fix round. All original and review invocations remain in the record.
Final recommendation **NO-GO**, because A/B consecutive bar, C coverage, D
appearance, geometry and keyboard traversal fail. Commit/push allocated branch
only; no PR, issue/project mutation or migration release.
