# UX-473: nothing in CI builds a generated project

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-465` stages 1-4, which shipped | **Found by:** round 72, closing `UX-465`'s first four stages | **Serves:** the round whose spec change breaks a build nobody runs until someone runs it by hand | **Topic:** guards

## Motivation

`UX-465` stage 5, split out so the item could close on what it did.
`tools/bga_gen_project.py` works and `tests/unit/test_a_generated_project_builds.py`
builds two generated projects where `bst` is present — but the census
that says what those builds *cover* runs nowhere:

```text
$ python3 tools/dev_finding_coverage.py
(a clone) 21 findings | 18 produced by a capture | 2 declared unreachable | 1 neither
```

Eighteen, because a generated capture is not committed (`UX-189`) and
so a clone cannot see it. The two findings `UX-465` reached —
`build-failed` and `failed-task-time` — are reachable by a command
nobody runs on a schedule, which is the same "true on one machine"
shape `UX-213` and `UX-459` are both about.

## Required Fix

`bst-examples` builds one generated project per CI run — it has `bst`,
`bwrap` and a builder already — and runs
`tools/dev_finding_coverage.py --local` over the capture, printing the
count. A drop in what a real build can produce then shows up in a job
log rather than in a round that happens to look.

Printing rather than asserting, at least at first: the census over a
generated capture has never run twice on the same runner, and a gate
whose bound nobody has measured is `UX-458`'s open question one axis
over.

## Out of Scope

- Committing a generated capture — `UX-189` settled that a clone does
  not ship one, and this item does not reopen it.
- Axis G at scale. A 1,202-element *real* build is a different budget
  question and `gen_synthetic_scale_run.py` covers the analysis side
  already.
- Turning the printed count into a gate — that needs the spread
  `UX-458` is waiting on, and is a row of its own when it exists.

## Acceptance Test

A `bst-examples` job log showing a generated project built and the
census's count for it, and a guard over `ci.yml` that the step is
there — `test_the_workflow_runs_what_it_says.py`'s shape.
