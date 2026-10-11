# 2026-10-11 — #213 planning: the timing gate on the redesigned slice

Planned #213 on `feat/issue-213-redesigned-slice-timing-gate`, cut from `main`
at `89ff866ee610816bf9fe28e048e60617fbd66063`. The plan is
`handoffs/issue-213-implementation-plan.md`. Refs #213.

## Authorization

The owner asked for #213 to be planned. That covers research, this branch,
the plan commit and its push. No PR was opened, no issue was commented on or
changed, and nothing is approved: implementation needs the owner's approval
of the plan SHA and a separate authorization.

- **Planner:** Anthropic `claude-opus-5-5` (Claude Code desktop session; the
  session does not report its native effort setting, so none is recorded).
- **Issue checks:** #213 open, label `enhancement`, on the vault-cleaner
  project with status `Todo`, no milestone, no comments. #209 open, its
  branch unmerged at `ee61b0790e4e1a8f8b928d3b452210fa6558f9b8`. #210 closed,
  merged through PR #212. Tracker #138 open.

## Measurements

Only the tracked sanitised fixture
`tests/fixtures/real/2026-09-01T-current/armor.csv` was read. No `data/` file
was read. The scripts ran from the session scratchpad and are not in the
repository.

- **#209's gate, unmodified, on #210's build, two invocations.** The blob
  `a77c21f3f2826c735c49463f6ef4d305604e82da` of
  `spikes/issue-209/proof_gate.py`, run with `PYTHONPATH=spikes/issue-210`.
  It runs as it is: its flip probe adds a class the redesign has no rule for,
  and its projection probe finds `duplicateGroups` with the same signature.
- **Result: the redesigned slice fails.** Navigation (A1, A2, B1) is slower
  by 85 to 113 ms in both invocations. A3 and A4 pass in both. B2 and B3
  passed in the first invocation and failed in the second.
- **Counters over navigation,** slice / production: script about 94 / 23 ms,
  layout 78 / 46 ms, style 32 / 15 ms. The slice has fewer elements.
- **A sampling profile** of an unminified build puts class merging at about
  7 of roughly 80 ms of script.

Full figures are in the plan, P1 to P6.

## Decisions

1. **A new `spikes/issue-213/`, starting from a verbatim copy** of
   `spikes/issue-210/frontend`. `spikes/issue-210/` is evidence for a merged
   ticket and stays frozen, as `spikes/issue-206/` did in #209.
2. **The gate proof is carried from #209's branch, not merged from it.** The
   pinned blob is committed unchanged first, so the adaptation is one diff a
   reviewer can read. The plan lists the only three kinds of difference
   allowed. Whether #209's branch is ever merged stays with the owner.
3. **The bar is #209's, unchanged.** Seven comparisons, two consecutive
   complete invocations. See the first surprise below for what that costs.
4. **Byte-identical captures are a trigger, not a gate.** A change that
   alters a capture or a document height stops the work for the owner's
   acceptance. The visual proof gets a control first, because #210's round 2
   saw capture bytes change on regeneration and did not find out why.
5. **shadcn-svelte is not decided here.** Class merging is too small a part
   of the cost to be the reason for a decision. Resolving class strings once
   is allowed with identical rendered `class` attributes; removing the
   conventions or the packages is out of scope.
6. **Attribution comes before any change, and a cause needs an ablation.**
   The commit order makes the first checkable. The second is there because
   the one candidate cause on record was a guess.
7. **Rendering containment, deferred mounting, paging and virtualisation
   are excluded outright.** #210's constraints rule out relying on
   containment; the others would pass the `ready` stamp by moving work after
   it.
8. **NO-GO with a complete record is a finished ticket,** not a stop
   condition. #209 treated the failing gate as a stop, which then needed the
   orchestrator to authorize finishing the record.
9. **Implementer:** `claude-opus-5-5` at `high`, Judgement rung. **Review:**
   independent adversarial.

## Surprises, for the next agent

- **B2 and B3 flip on frame phase.** The settled stamp lands on a frame
  boundary. The slice's acknowledgement-to-settled was 28.5 to 30.3 ms in
  all ten runs. Production's was about 20 ms in five runs and about 31 ms in
  the other five, and which side its median fell on decided both
  comparisons. Neither page changed between the two invocations. #209's
  final failures on A3 and B3 were 0.2 to 3.7 ms, so they may have been the
  same effect; that was not measured.
- **The `tailwind-merge` guess in #210's worklog is measured and small.**
  The 85 ms is spread across mounting 13,019 elements, garbage collection,
  layout and style. The planner's expectation is NO-GO.
- **#210's runner cannot be redirected by setting `run_proof.FRONTEND`.**
  `configure`'s default argument is bound when the function is defined
  (`spikes/issue-210/run_proof.py:96`), and every local proof calls
  `configure()` at import. A runner for another build has to call
  `configure(<its frontend>)` first. The plan makes each proof print the
  hashes of the files the server actually sent.
- **The gate times the two pages on opposite verdict actions,** and that
  comes from S15 itself (`spikes/issue-206/proof_s15_scale.py:253`), not from
  #209. No effect above 1 ms shows in the planning runs. The plan has the
  action printed per run.
- **`/api/report` finishes 10 to 20 ms later on the slice** than on
  production. Not investigated; it is on the plan's attribution list.
- **zsh reads `$B:spikes/...` as a parameter modifier** and fails with "bad
  substitution". Write `"${B}:spikes/..."` when showing a file from a ref
  held in a variable.
- The planning checkout has an untracked `spikes/issue-209/` holding only
  `node_modules`, `dist` and `__pycache__`, left from a checkout of #209's
  branch. Nothing was staged from it.

## Not done

- No slice source was changed and no fix was tried.
- The cause of the later `/api/report` response, and of the extra layout and
  style time, was not looked for.
- Whether the capture bytes are stable from run to run was not measured.
- No issue was created, edited or commented on. The dispatch comment waits
  for approval of the plan SHA and its own authorization.
- The two stale Gemini rows in `handoffs/models.toml` were not re-verified;
  the plan relies on neither.
