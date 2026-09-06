# UX-717: the host series is on the trace and in no question

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-675 (the three CPU tracks); **not** UX-676 - the round-101 track verified it publishes a report section and per-row trace queries, not a Finding the reachability gate reads, so the premise this row was filed on does not hold | **Serves:** R5, the capacity operator - the question hangs off `capacity-recommendation`, which publishes `cores_busy` and `binding_constraint`; the row said R4 before it was built | **Topic:** viewer | **Shape:** judgement | **Area:** bga/viewer

## Motivation

`UX-675` put eight host counter tracks on the trace and no canned
question names one. The library's own guard could not have caught it —
it holds a set of one:

```text
tests/unit/test_the_questions_ask_what_the_trace_answers.py:163
    emitted = {bga_timeline.CONCURRENCY_COUNTER}
```

`HOST_COUNTERS` has had five tracks on the wire since `UX-437` and now
has eight, so a question naming `host cores busy` fails that clause
**for being right**. This is `UX-437`'s own defect one surface over:
the series is written, drawn, and reachable by nobody who did not
already know the track's name.

Attempted inside `UX-675` and reverted, measured: adding one question
takes the library 17 → 18 and reddens 16 clauses across five files —
seven spelled-out counts in `README.md`, `docs/guides/cli.md`,
`docs/guides/what-the-viewer-answers.md`, `.claude/skills/measure/SKILL.md`
and `questions.js` itself, the two sorting tables, the chrome cost, and
`test_every_library_query_is_reachable_from_a_finding`. That last one
is the gate: a library query must be reachable from a finding, and no
finding names CPU utilization until `UX-676` publishes one.

## Required Fix

The question (`were-the-cores-busy`: `host cores busy` against
`host cores`, with `host load average` beside them to separate a busy
machine from a blocked one), the finding it hangs off, and every
counted sentence re-derived. `emitted` in the counter-track clause
becomes `{CONCURRENCY_COUNTER} | {label for HOST_COUNTERS}` and reads
`t.name in (...)` as well as `t.name = '...'`.

## Out of Scope

- The utilization envelope itself — `UX-676` computes it; this puts
  the raw series in front of a reader who wants the numbers.

## Acceptance Test

`bga view`'s library serves nineteen questions, one of them naming a
host counter track; every counted sentence says nineteen; mutation:
misname the track in that question's SQL — the counter-track clause
reds, which it could not do before this item widened its set.

## Outcome

**The gap, measured.** `emitted` held one name
(`test_the_questions_ask_what_the_trace_answers.py:163`) and the
library served 17. Checked before writing anything, per the brief:
`git log --oneline --all | grep UX-676` shows three commits, none
touching `bga/findings.py` or `bga/provenance.py`; no `_finding()` id
names utilization, envelope or cores, so `TRACE_QUERIES` had nothing to
route the new question through. `UX-676` published a report section
and per-row `trace_query`s on its own two interval tables, not a claim
`attach()` wires up — the premise "UX-676 publishes the utilization
finding" does not hold.

**The close, measured.** Added `were-the-cores-busy` (17 → 18); widened
`emitted` to `{CONCURRENCY_COUNTER} | {label for HOST_COUNTERS}` and to
read `t.name in (...)`. Hung the query off `capacity-recommendation`
instead of a UX-676 claim — the one existing finding that already
publishes `host_cpu_count`, `cores_busy` and the binding constraint.
Run for real on a fresh two-plane capture of `examples/06`
(cache-busted, both planes, host samples on):

```text
$ bga timeline .../20260906T153003Z -o six.pftrace
399 host counters on 8 tracks: host cores, host cores busy, ...
$ trace_processor_shell -q were_the_cores_busy.sql six.pftrace
"seconds","cores_busy","cores_total","load_average"
1788708703.28,3.993,4.000,14.260
1788708701.28,4.000,4.000,14.260
```

25 rows returned; not empty.

**Mutation table.**

| mutation | reddened | file |
|---|---|---|
| `emitted` reverted to `{CONCURRENCY_COUNTER}` | `test_every_counter_track_named_is_one_the_emitter_creates` | `test_the_questions_ask_what_the_trace_answers.py` |
| `HOST_COUNTERS`' `"host cores busy"` label renamed | same | same |
| new SQL's `t.name in (...)` given a track the emitter never creates | same (proves the `in (...)` regex is read, not decorative) | same |
| `capacity-recommendation`'s `TRACE_QUERIES` tuple reverted to two | `test_every_library_query_is_reachable_from_a_finding` | `test_buttons_that_know_why.py` |

All four reverted from the scratchpad copy and reconfirmed green.

**Deviations.** (1) No UX-676 claim existed to hang the question off —
reported per the brief rather than inventing a new Finding's severity
policy; used `capacity-recommendation` (role `capacity-operator`/R5,
not R4 as `**Serves:**` states) as the closest real fit. (2) The
Acceptance Test says "nineteen"; the Motivation's own "17 → 18" and the
actual count are both eighteen — read as the task file's typo. (3)
Touched two undeclared files: `tests/unit/test_a_counted_figure_is_derived.py`
(the chrome-cost count literal, 2→3) and
`tests/unit/test_the_report_you_can_attach.py` (`PAGE_BUDGET_B`,
316,000→322,000 — the page grew 1,114 B past it).
