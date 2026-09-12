# UX-808: the max-jobs advice lists one row per task, not per element

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-677 (the advice) | **Found by:** round 112, a fresh two-plane capture of `examples/06` taken to price the advice (`UX-739`) | **Serves:** R4 and R5 reading the recommendation table | **Topic:** analysis | **Area:** bga | **Shape:** bounded

## Motivation

`_max_jobs_advice` (`bga/cli.py`) hands `compute_max_jobs_advice`
every normalized task, and the advice emits one row per task. A cold
build has a FETCH task beside every BUILD task, so every element
appears twice — once judged on its BUILD span, once refused on its
FETCH span's single sample:

```text
$ bga snapshot --project examples/06-… --trace-spine on -- bst build all.bst
$ python3 -c "... analyze.json['capacity_recommendation']['max_jobs_advice']['elements'] ..."
{'element': 'codegen.bst', 'current_max_jobs': 4, 'recommended_max_jobs': 1, 'samples_in_span': 4, 'refusal': None}
{'element': 'codegen.bst', 'current_max_jobs': 4, 'recommended_max_jobs': None, 'samples_in_span': 1, 'refusal': "only 1 host CPU sample interval(s) fall inside this element's BUILD span - 2 needed (UX-677)"}
{'element': 'core.bst', 'current_max_jobs': 1, 'recommended_max_jobs': 1, 'samples_in_span': 7, 'refusal': None}
{'element': 'core.bst', 'current_max_jobs': 1, 'recommended_max_jobs': None, 'samples_in_span': 1, 'refusal': "only 1 host CPU sample …"}
```

22 rows for 11 elements. The refusal names "this element's BUILD span"
while reading a FETCH span, and `_building(w)` counts a fetching
element as building, which lowers the recommendation for whatever
built alongside it. `tests/fixtures/host_cpu` did not show it: that
run was warm on sources, so it had no FETCH tasks.

## Required Fix

`_max_jobs_advice` passes only BUILD tasks (`task.task_key.task_kind
== TaskKind.BUILD`, the test `compute_split_projection` already applies
in `bga/correlate.py`), so the advice has one row per built element and
`_building` counts builders only. A guard in
`tests/unit/test_the_max_jobs_advisor_does_not_overcommit.py` (or
beside it) feeds an element with a BUILD and a FETCH task through the
CLI-side gatherer and asserts one row; mutation: drop the filter, two.

## Decomposition

Input classes the guard covers: an element with a BUILD task alone, one
with a BUILD and a FETCH task, and one with only a FETCH task (no row at
all — nothing was built); the journey it extends is
`test_the_max_jobs_advisor_does_not_overcommit.py`'s — host series +
spans → one recommendation per element under the no-overcommit
constraint — with "per built element" as its first step.

## Out of Scope

- The price beside each row — `UX-739`.
- Elements built more than once (retries): one row per attempt is the
  attempt's own claim and stays.

## Acceptance Test

On the round-112 capture above, 11 rows for 11 elements after the fix
(pasted), `codegen.bst`'s recommendation unchanged at 1 or moved with
the reason stated; the guard red under the mutation and green after
the revert.

## Outcome

**Gap measured.** Before the fix, the round-112 capture's own
`analyze.json` gave 22 rows for 11 elements (Motivation). `_max_jobs_
advice` (`bga/cli.py`) built its `tasks` list from every normalized
task with no `task_kind` filter.

**Close measured.** `_max_jobs_advice` now keeps only
`task.task_key.task_kind == TaskKind.BUILD`. Re-run on the same
capture (`PYTHONPATH=<worktree> python3 -c "...main()..." analyze
$RUN/run --plane2 $RUN/plane2.json --format json`):
`capacity_recommendation.max_jobs_advice.elements` has **11 rows for
11 elements** (one each), `codegen.bst` unchanged at
`current_max_jobs: 4, recommended_max_jobs: 1, samples_in_span: 4,
refusal: None`. Full set: `core.bst` 1→1; `toolchain.bst`, `app.bst`,
`all.bst` refuse (thin evidence); `lib-a..e.bst` 4→2; `lib-f.bst` 4→1.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| drop the `TaskKind.BUILD` filter | `TestOneRowPerBuiltElement::test_a_build_and_fetch_task_yield_one_row` (2 rows, not 1) | 1 of 10 in the file |

Reverted from a pristine copy of `bga/cli.py`; file green after
revert (`10 passed`).

**Deviation.** None.
