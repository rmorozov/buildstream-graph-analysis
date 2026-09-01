# UX-459: eight findings are reachable by nothing a clone has

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 72, tracing the heuristics in `bga analyze` to the fixtures that reach them | **Serves:** the round that adds a heuristic and has no fixture that can exercise it | **Topic:** guards

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

## Acceptance Test

```bash
python3 tools/dev_finding_coverage.py
```

reports zero in the `neither` column on a clean checkout, with the
route chosen and its cost recorded here.

## Outcome

_Not started._
