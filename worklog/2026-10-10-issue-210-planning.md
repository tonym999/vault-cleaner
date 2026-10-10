# 2026-10-10 — #210 planning: redesign of the Svelte Armor duplicates slice

Planned #210 on `feat/issue-210-armor-duplicates-redesign`, cut from `main` at
`d139a05306828c0a4d7e9ded211408b346dd7768`. The plan is
`handoffs/issue-210-implementation-plan.md`. Refs #210.

## Authorization

The owner asked for #210 to be planned, with Claude as implementer, and asked
for the prior-art survey and two or three mockup directions before the plan
fixed a design. That covers research, this branch, the plan commit and its
push. No PR was opened, no issue was commented on or changed, and nothing is
approved: implementation needs the owner's approval of the plan SHA and a
separate authorization.

- **Planner:** Anthropic `claude-opus-5-5` (Claude Code desktop session; the
  session does not report its native effort setting, so none is recorded).
- **Issue checks:** #210 open, label `enhancement`, on the vault-cleaner
  project with status `Todo`, no milestone, no comments. #152 open. #206
  merged through PR #208.

## What was done

- **Prior-art survey,** recorded in `docs/evidence/issue-210/README.md`
  section 1. Destiny Item Manager was read from its changelog, wiki and
  Compare source, then seen live in the owner's signed-in Chrome (inventory,
  item popup, Compare, Organizer) with the owner's permission.
- **Four mockup directions** on the full 74-group sanitised fixture, dark,
  at 1440 px and 390 px: A ledger, B side by side, C index and inspector,
  and D, B revised after the live look at DIM. The generator, stylesheet and
  nine captures are in `docs/evidence/issue-210/mockups/`.
- **The plan,** for direction D.

## Owner decisions (2026-10-10, in the planning session)

1. Direction D.
2. Try shadcn-svelte and see what it looks like. The owner wrote
   "shadcn/ui"; that project is React, and its Svelte port is shadcn-svelte,
   which #206 already probed. The plan reads the request as the port and
   says so.
3. Start from #206 on `main` and carry #209's value-retention change
   forward. This was the planner's advice, which the owner accepted.
4. Repeat #209's timing gate as a follow-up, not in this ticket. Also the
   planner's advice.
5. #210 supersedes #152. Nothing was done to #152; closing it needs its own
   authorization.

## Measured while planning

On the envelope the unmodified server returns for
`tests/fixtures/real/2026-09-01T-current/armor.csv`. No `data/` file was read.

- 74 groups (9 exact, 65 same-stat), 158 pieces, 435 verdict buttons.
- 66 pairs, 6 triples, 2 groups of four. Every exact group is a pair.
- Every group is tier 5 with the 30/25/20 spike.
- Same-stat groups differ on 2 to 9 comparison fields. Tuning Stat equals
  Tuning Mod Slot, ignoring case, on all 140 same-stat pieces.
- Mockup page heights at 1440 / 390 px: A 25,036 / 64,571; B 35,562 /
  61,331; C 6,455 / 8,198; D 28,360 / 56,209. #206 measured about 61,000 /
  101,000.

## Surprises, for the next agent

- **DIM never shows tuning as a field.** It marks the tuned stat beside that
  stat's value, in a fixed six-stat order with zeros kept. That is what
  turned B into D. The source and changelog did not make it obvious; the
  live app did.
- **The #206 proofs fix more copy than expected.** The kind text
  (`Exact duplicates`, `Same stats · review only`) and the scope text
  (`N groups · M pieces`) are asserted verbatim, and facets are read as
  `select[data-facet]`. The mockup's shorter pill wording and a non-native
  select would both fail S1.
- **Direction D cannot pass S1 unedited.** The oracle requires a separate
  visible `tuning_stat` value per same-stat piece; D merges it into the
  tuned-stat cell. The plan allows exactly one oracle adaptation for this
  and requires a test for the case where the two fields differ, which the
  fixture never exercises.
- **shadcn's default button carries a transition,** which is #209's dominant
  cost. The plan adds a proof that no verdict control has one.
- **The survey is incomplete.** D2ArmorPicker and Braytech were not signed
  in; light.gg showed only an item-definition page; Ishtar Commander and the
  in-game screens were not examined; and nothing was seen at phone width,
  because the Chrome window ignored resize requests. The evidence README
  says so.
- **The live DIM session showed the owner's real vault.** Only layout
  observations were recorded. No screenshot of it was saved.

## Decisions in the plan

- **The plan commit also carries `docs/evidence/issue-210/`.** The planner
  template has the first commit hold the plan and the worklog. The mockups
  are the design the plan points at, and they existed only in a session
  scratchpad, so they are committed with it. The owner approves this with
  the plan SHA.
- **New directory `spikes/issue-210/`,** with a verbatim copy commit and a
  separate carry-forward commit, so the cheap-to-change report measures the
  redesign alone. `spikes/issue-206/` stays frozen.
- **Approved packages for the trial:** `bits-ui`, `tailwind-variants`,
  `clsx`, `tailwind-merge`, and the `shadcn-svelte` CLI. `daisyui` is
  removed. Anything else is asked for.
- **Three contract departures,** accepted by the owner in choosing D: the
  fixed-order stat strip instead of role-ordered spike cards, the review-only
  statement once per section instead of per card, and sentence-case labels.
- **Implementer:** `claude-opus-5-5` at `high`, Judgement rung, at the
  owner's direction. **Review path:** standard orchestrator review, with the
  owner's acceptance from captures as the design gate.

## Not done

- No slice code was written. The mockups are static pages, not Svelte.
- The light palette in `mock.css` was never captured or checked.
- The proof-runner approach was read from #209's branch, not run.
- `python3 scripts/check_model_roster.py` reports 2 stale rows (both
  Gemini); neither is relied on.
