# UX-717: the host series is on the trace and in no question

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-675 (the three CPU tracks), UX-676 (a finding to link the query from) | **Serves:** R4, asking whether the cores were busy | **Topic:** viewer | **Shape:** judgement | **Area:** bga/viewer

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
