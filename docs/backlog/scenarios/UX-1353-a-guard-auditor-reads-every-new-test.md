# UX-1353: a guard auditor reads every new test against what its task says it guards

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1351 | **Found by:** the Haiku 5.5 workflow review, 2026-10-10 — Ruslan in the project thread, 15:45; the 2026-09-28 reviewer review proposed the class | **Serves:** every round's guards, and the escapes that are guards bound to a proxy | **Topic:** guards | **Area:** unassigned | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

12 of the 23 confirmed escapes counted on 2026-09-27 were a guard that
could not fail on the defect it named: a vacuous regex, an echo read
instead of the check, a proxy. The verifier mutates one track; nothing
reads every new guard in a round. The 2026-10-10 probe planted that
class in UX-1341 (the guard ran a hardcoded `--from 1`, not the guide's
spelling) and a Haiku 5.5 verifier found it for $0.017.

## Required Fix

A `.claude/agents/guard-auditor.md` on `model: haiku` at `effort: high`,
read-only. It reads each test file a round adds or changes and the
Acceptance Test of the task it names, and answers per guard: can it
fail on the defect its task names, or does it read a proxy, an echo or
nothing? A guard it suspects goes to one `opus` reader at `medium` with
the auditor's reason; only that reader's confirmed findings go to the
round's fix list, never to new filed rows.

## Decision

Route:     Add `.claude/agents/guard-auditor.md` (frontmatter `model: haiku`, `effort: high`, `tools: Read, Grep, Glob, Bash`), body "report only, fix nothing": for each test file the round adds or changes, it reads the task's Acceptance Test and answers can-fail / proxy / echo / nothing, with a reason; suspects go to one `opus` reader at `medium`, and only that reader's confirmed findings go on the round's fix list, never as filed rows. Pinned in the existing agent-configuration clauses. ~40 lines of agent file, ~10 of test.
Rejected:  a hook or tool running the audit: a guard reading a proxy is a judgement, there is no mechanism to put in its place.
Rejected:  a whole-diff PR reviewer: out of scope (postponed by Ruslan 2026-10-10).
Rejected:  pinning the UX-1341 plant as a unit test: needs a live model run; the Acceptance Test stays the session's reading after merge, priced by UX-1351's cell.
Rejected:  naming the agent in CLAUDE.md or the decompose skill now: widens the brief the three arms share; a later bookkeeping line.
Files:     `.claude/agents/guard-auditor.md` (new); `tests/unit/test_the_agent_configuration_holds.py`: `"guard-auditor"` into `REPORTERS`, plus `test_the_guard_auditor_reads_on_haiku_and_escalates_to_opus` in the frontmatter class.
Guard:     `tests/unit/test_the_agent_configuration_holds.py`: the new clause reads `model: haiku`, `effort: high`, and a body naming `opus` at `medium` and "fix list"; existing clauses cover five fields, effort level, name = filename, no Edit/Write, reporter says "fix nothing".
Mutation:  (1) `model: haiku` -> `model: sonnet` reddens the new clause; (2) `Edit` in `tools:` reddens `test_a_reporting_agent_cannot_edit_the_tree`; (3) deleting "fix nothing" reddens `test_a_reporter_is_never_put_on_the_editing_list`.
Class:     bookkeeping (process): closes a defect class (12 of 23 escapes) but cuts no measured cost. With UX-1040 it is 2 of 5 rows, at the 40% cap; UX-1352 (also bookkeeping) waits.
Split:     one track.
Question:  none

## Out of Scope

Running mutations (the verifier's). A whole-diff PR reviewer.

## Acceptance Test

Run on a round's merged tree with UX-1341's planted guard restored, it
flags that guard and the opus reader confirms it. Its false-flag share
over the round is stated, priced by `UX-1351`'s cost cell.

## Outcome

**Gap measured.** At `b1323876`, `ls .claude/agents/` lists seven
agents and no `guard-auditor.md`; nothing reads every new guard in a
round.

**Close measured.** `.claude/agents/guard-auditor.md` added (haiku, high,
`Read, Grep, Glob, Bash`), `"guard-auditor"` in `REPORTERS`, new clause
`test_the_guard_auditor_reads_on_haiku_and_escalates_to_opus`.
`pytest tests/unit/test_the_agent_configuration_holds.py -k Subagents`:
`23 passed, 156 deselected` (after the fix loops). The live Acceptance Test (UX-1341 plant
flagged, opus confirms, false-flag share) is the session's reading after
merge, per the Decision.

| Mutation | Reddened | Count |
|---|---|---|
| `model: haiku` -> `model: sonnet` | the opus clause | 1 failed, 22 passed |
| `Edit` added to `tools:` | `test_a_reporting_agent_cannot_edit_the_tree` | 1 failed, 22 passed |
| `**Fix nothing.**` -> `**Read and answer.**` | `test_a_reporter_is_never_put_on_the_editing_list` | 1 failed, 22 passed |
| `"guard-auditor"` moved REPORTERS -> MAY_EDIT | the opus clause (`in self.REPORTERS`) | 1 failed, 22 passed |
| same move plus `Edit` in `tools:` (the swap) | the opus clause | 1 failed, 22 passed |
| routing sentence: `goes` -> `never goes` | the opus clause | 1 failed, 22 passed |
| routing sentence: `, never as filed rows` deleted | the opus clause | 1 failed, 22 passed |
| routing sentence inverted (`never to one opus reader`) | the opus clause | 1 failed, 22 passed |
| launcher sentence deleted | the opus clause | 1 failed, 22 passed |

All rows re-measured at 23 tests (`-k Subagents -n 2`, base `23 passed`).

**Deviation.** The Decision's mutation 3 needed the whole sentence, and its
guard missed three escapes (REPORTERS removal, inverted routing, no named
launcher); the fix loop closed all three.

Not coded, judged by the session: a verb inversion ("refutes"), a gate
bypass keeping the words, a hedged launcher; a string test cannot read
meaning, the live Acceptance run after merge is the witness. Pre-existing
gap: the `tools:` regex reads only the first frontmatter line.
