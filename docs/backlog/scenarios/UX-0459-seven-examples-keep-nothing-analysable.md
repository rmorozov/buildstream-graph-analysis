# UX-459: eight findings are reachable by nothing a clone has

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, tracing the heuristics in `bga analyze` to the fixtures that reach them | **Serves:** the round that adds a heuristic and has no fixture that can exercise it | **Topic:** guards | **Area:** tools

## Motivation

`FINDING_READERS` is the registry of what `analyze` can conclude — 21
findings. A fresh clone carries **two** analysable captures, and they
reach eleven of them:

```console
$ python3 tools/dev_finding_coverage.py
blast-radius-ranking     *** NOTHING PRODUCES THIS ***
blast-radius-structural  *** NOTHING PRODUCES THIS ***
build-failed             declared unreachable: every committed capture is of a build that succeeded (UX-156)
cache-transfer-cost      *** NOTHING PRODUCES THIS ***
certified-headroom       *** NOTHING PRODUCES THIS ***
criticality              *** NOTHING PRODUCES THIS ***
execution-bound          *** NOTHING PRODUCES THIS ***
failed-task-time         declared unreachable: no committed capture has a failed task
run-mode-incremental     *** NOTHING PRODUCES THIS ***
shared-source-blast      *** NOTHING PRODUCES THIS ***
(a clone) 21 findings | 11 produced by a capture | 2 declared unreachable | 8 neither
```

The two are `tests/fixtures/macro_micro` and
`tests/fixtures/with_timeline`. **Eight findings are reachable by
nothing a clone has**, so every guard that touches them builds its own
synthetic payload and the suite stays green whatever the analyzer does
to real data.

### The correction this item exists because of

The first version of this row said "seven of nine examples keep no
committed capture" and proposed committing one per example. Both halves
were wrong, and the same way:

```console
$ git ls-files 'examples/*/.bga' | wc -l
0
$ cat examples/06-macro-micro-optimization/.bga/.gitignore
# Written by `bga snapshot` (UX-126) ...
*
```

**No example capture has ever been committed.** Every `.bga` carries a
`.gitignore` holding `*`, and `UX-189` decided a clone should not ship
the capture archive. The captures under `examples/06` and
`examples/08` that the first census counted exist only on a machine
that has built them — this container had, from an earlier round.

So the census measured the working tree and reported it as the
repository. That is fixing guide §5 inside the census written to find
§5 gaps, and it inflated the answer twice over: it said 7 uncovered,
then 3 after building six more captures locally; a clone's answer is
**8**, and building captures locally changes it by nothing at all.
`tools/dev_finding_coverage.py` defaults to `git ls-files` for exactly
this reason and takes `--local` to show the difference.

## Required Fix

The fix is **not** to commit captures — `UX-189` settled that, and
`examples/*/.bga/.gitignore` enforces it. Two routes remain, and this
item is to pick one with a measurement rather than a preference:

- **Curated fixtures**, the shape already in the tree: `tests/fixtures/`
  carries 65 tracked files including the two captures that work. Derive
  small fixtures from the example builds for the eight, sized against
  what `macro_micro` and `with_timeline` cost.
- **Or CI does the reaching**: `bst-examples` already builds 01-06 on
  every run and throws the analysis away. Running
  `dev_finding_coverage.py --local` there would exercise the eight on
  real data without a byte entering the repository — at the price of a
  guard that only runs in one job.

Either way, `UX-460`'s guard is what freezes the answer.

## Out of Scope

- **Committing `examples/*/.bga`**: refused above, with the decision
  and the mechanism that enforces it.
- **`build-failed`, `failed-task-time`**: declared unreachable in
  `dev_finding_coverage.UNREACHABLE`, with reasons.
- **`examples/09`**: builds fine. A first draft of this round filed a
  row saying it could not, on the strength of `ls examples/*.sh`
  showing no staging script for it. The script is not a `.sh` and is
  not shared: `examples/09-fine-grained-siblings/generate_bulk.py` is
  committed, the root `.gitignore` excludes `files/bulk/` deliberately
  ("60,000 inodes whose only purpose is to make staging measurable"),
  and `examples/README.md` says so two paragraphs below the text that
  first draft quoted:

  > Generate the bulk tree once (it is gitignored, like the toolchain):
  > `examples/09-fine-grained-siblings/generate_bulk.py`

  Run, it makes 60,000 files in 2.97s and `bst build all.bst`
  succeeds. The row was withdrawn. Reading one glob instead of the
  document beside it is how a working thing gets filed as broken.

## The decision, made in UX-463

This row was filed with two arms and no measurement between them:
curated fixtures, or a CI job running the census on builds it already
discards. `UX-463` inventoried the generation tooling and found the
arms do not overlap - curated fixtures own graph shape, timing and run
mode, because a real build cannot be asked for two longest paths within
a few percent; a generator owns outcome, sandbox profile and scale,
because those live below `bst` and a synthesised trace can only assert
what its author already believed. So both, split by axis.

Six of the eight uncovered findings close under `UX-464`; T5's two need
`UX-465`; `cache-transfer-cost` is declared uncovered for want of a
remote CAS.

`UX-464` landed in the same round and moved the census from **11
produced to 18**, leaving `cache-transfer-cost` as the only finding
nothing in a clone reaches. This row stays open on its last clause -
T5's `build-failed` and `failed-task-time`, which need `UX-465`'s
failed build - and closes with it.

## Acceptance Test

```bash
python3 tools/dev_finding_coverage.py
```

reports zero in the `neither` column on a clean checkout, with the
route chosen and its cost recorded here.

## Outcome

**Round 73 · 2026-09-01 · Status: 🟢 Done — zero in the `neither` column, and the fixture that closed it found an unfixed defect**

### The gap, and what closed it

```console
$ python3 tools/dev_finding_coverage.py | tail -2
(a clone) 21 findings | 18 produced by a capture | 2 declared unreachable | 1 neither
  neither: cache-transfer-cost
```

`cache-transfer-cost` was the last one, and this row had proposed
declaring it uncovered "for want of a remote CAS". That turned out to
be the wrong call, and the reason is worth having written down: **the
finding does not need a remote CAS, it needs a capture whose Plane 1
log records `PULL` tasks** — which is exactly the ingested form a
curated fixture is for (`UX-463`'s split: curated fixtures own graph
shape, timing and run mode; a generator owns outcome, sandbox profile
and scale). A pulled artifact is Plane 1 scheduler data, not something
below `bst`.

Two things have to be true at once, and no existing fixture had both:

- `compute_cache_accounting` returns `{}` unless the capture records a
  Pipeline Summary;
- `_transfer_us` counts only tasks whose `primary_resource` is
  `DOWNLOAD` or `UPLOAD`.

`tests/fixtures/golden/mixed_task_kinds` has the second and not the
first — one `FETCH|DOWNLOAD` span, no `queue_summary` — so it publishes
no cache block at all:

```console
$ bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics --format json | jq -c '.cache'
{}
```

So `tests/fixtures/topologies.py` gained `a_build_that_pulls`: three
elements pulled (`PULL` on `DOWNLOAD`, `TaskKind.PULL` and
`Resource.DOWNLOAD` are both first-class in `bga/ingest/models.py`),
one built, and a queue summary that says which is which.

### Sizing it, rather than picking a number

```text
  pull    build   transfer share   cache-transfer-cost
  3.0s     4.0s       0.692        fires
  1.0s     9.0s       0.250        fires        <- the defaults
  0.5s    20.0s       0.070        silent
```

`TRANSFER_SHARE_NOTABLE` is 0.1. 0.250 clears it with margin without
being a build that does nothing but download. Serial on purpose:
`_transfer_us`' own docstring says two concurrent pulls count twice, so
a concurrent fixture could report a share above 1.0 and would be
arguing with the thing it exercises.

```console
$ bga analyze tests/fixtures/a_build_that_pulls/run --diagnostics --format json | jq -r '.findings[] | select(.id=="cache-transfer-cost") | .title'
25% of wall-clock was artifact transfer (download 3.0s) - this build spent it moving artifacts rather than making them

$ python3 tools/dev_finding_coverage.py | tail -1
(a clone) 21 findings | 19 produced by a capture | 2 declared unreachable | 0 neither
```

### What the fixture found on its first run

```text
WARNING bga.validation.invariants: Model score reduced: T_C (9000000) < LB (12000000)
```

`UX-60` used that exact line: applying its own decision revealed that
"a BUILD task carried no dependency on its own element's FETCH", and it
closed that hole. The hole is open one edge over — a dependency's
`PULL` — and this is the first committed capture to walk into it.
`lib3` builds for 9.0s on top of three pulls that finish at 3.0s, and
the replay starts it at `t=0`. No other committed capture reports the
warning (measured, four of them, all `0`), because none has a `PULL`.
Filed as `UX-481` rather than fixed here: it moves a certified floor,
which is a task with its own measurement.

### Deviation from the Required Fix

The Required Fix offered two routes — curated fixtures, or CI running
`--local` on builds it already discards — and said to pick one with a
measurement. The measurement picked the first: the finding's trigger is
a Plane 1 task kind, so a curated capture reaches it deterministically
in **1.2s**, where the CI route would reach it only on a runner with a
remote cache configured, which no job has. The CI route is not
abandoned — it is `UX-473`, for the two findings a curated capture
genuinely cannot reach.

The row also proposed declaring `cache-transfer-cost` uncovered. That
proposal is withdrawn above, with the reason: a declaration would have
been a wrong sentence in the record, and the guard `UX-460` adds
(`test_a_declared_finding_is_not_also_produced`) would now be failing
on it.

### Verification

```text
python3 tools/dev_finding_coverage.py     0 neither
make lint                                  clean
make test                                  5567 passed, 28 skipped in 303.15s
```
