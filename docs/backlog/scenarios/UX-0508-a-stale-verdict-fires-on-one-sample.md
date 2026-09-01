# UX-508: the whole-runner verdict fires on one sample

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-442 (the two-run rule it copies), UX-503 | **Serves:** the branch whose CI is red because one runner was fast | **Topic:** guards

## Motivation

Round 75's fourth push went red on `test (3.11)` with nothing in its
diff that could have caused it — a dev tool, a guard file and three
documents:

```text
run 33571888677, cdf912b, the record step's own spread block
  "shift_files": 142,
  "shift": 0.581,          <- IMAGE_BAND is (0.6, 1.7)
```

`spread`'s shift **is** `shift_of`, the one the gate divides by, so the
drift step read `stale` and exited 1. The three pushes before it were
green; the reference itself was recorded on an ordinary run (its own
`spread.shift` is 1.069). One runner ran the suite about 1.7x faster
than the run the reference was taken on, and that single reading failed
the build.

This is the defect `UX-442` fixed for **per-file** drift and `UX-503`
fixed for **absent** files, on the third quantity in the same tool: a
verdict about a distribution, taken from one sample. `against` already
says so about itself — *"This says what one run found. Whether that is
drift or one slow afternoon needs the run before it"* — and then the
band is applied to one run anyway.

Re-recording is not the answer and the tool's own message asking for it
is part of the defect: a wholesale re-record on this run would put the
reference on the fast runner, and the next ordinary run would read
about x1.7 — the other edge of the same band. That is `UX-496`'s
finding, reached from the opposite side.

## Required Fix

`stale` reports on one run and fails only when `CI_DRIFT_RUNS`
consecutive runs agree the reference no longer describes the runner.
The carry already crosses runs for per-file readings; it carries the
run's shift too. A run with no `--carry` still fails on one sample, as
`UX-442` left it — a gate that went quiet over a forgotten flag is
worse than one that reports.

## Out of Scope

- The band's width. `UX-496` and `UX-458` own whether `IMAGE_BAND` and
  `CI_DRIFT_FACTOR` are sized right; this item is about how many
  samples a verdict needs, not where the edges are.
- Re-recording the reference. It is not stale — one runner was fast.

## Acceptance Test

A synthetic run at x0.5 against a reference: exit 0, and the message
says the run is outside the band and waiting. The same run twice over
one carry: exit 1. Mutation: confirm on the first run again — the
single-run case reds.

## Outcome (round 75, 2026-09-01) — 🟢 Done

### The gap, measured

CI itself, on this round's fourth push. Run 33571888677, `cdf912b`,
from the record step's own spread block:

```text
"shift_files": 142,
"shift": 0.581            <- IMAGE_BAND is (0.6, 1.7)
```

`spread`'s shift **is** `shift_of`, the one the gate divides by, so the
drift step read `stale` and exited 1. Its diff was a dev tool, a guard
file and three documents — nothing that can move 142 files' timings.
The three pushes before it were green and the reference was recorded on
an ordinary run (its own `spread.shift` is 1.069). One runner ran the
suite about 1.7x faster, and that single reading failed the build.

`against`'s docstring already said one run cannot decide — *"whether
that is drift or one slow afternoon needs the run before it"* — and the
band was applied to one run anyway. Third one-sample verdict in this
tool, after `UX-442` (per file) and `UX-503` (absent files).

### After

```text
$ python3 -m pytest -k RunnerVerdict
6 passed
```

x0.50 against the reference: **exit 0**, "one runner's afternoon until
the next run agrees". The same run twice over one carry: **exit 1**,
with the re-record route. A normal run between two excursions breaks
the chain, as `UX-442` requires. No `--carry`: exit 1 on one sample,
unchanged — a gate that went quiet over a forgotten flag is worse than
one that reports.

The carry already crossed runs for per-file readings; it now carries
the run's shift in its own `shifts` list. A carry written before this
key existed reads as no memory, so the first run after it decides
alone.

**Re-recording was the wrong fix and was not applied.** A wholesale
re-record on this run would put the reference on the fast runner, and
the next ordinary run would read about x1.7 — the other edge of the
same band. That is `UX-496`, reached from the opposite side.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| R1 | `stale` confirms on the first run again | 3 clauses |
| R2 | `stale` never confirms | 2 |
| R3 | the carry stops writing the shift | 1: `..._two_agreeing_runs_...` |
| R4 | `out_of_band` ignores the window's length | 3 |
| R5 | agreement becomes "ever", not "consecutively" | 2 |

**A trap worth writing down.** R5 is `all` → `any`: same length. The
restoring `cp` gave the file a new mtime in the same second and the
same size, so CPython reused the mutated `.pyc` and two clauses stayed
red after the revert — `inspect.getsource` showed the correct source
while `dis` showed `LOAD_GLOBAL any`. Every mutation above was re-run
with `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` cleared. A
same-length mutation is the one shape where a falsify run can lie to
you in both directions.

### Deviation from the Required Fix

None. Out of scope and untouched: the band's width (`UX-496`,
`UX-458`) and the reference itself, which is not stale.

```text
make test-touching  483 passed in 15.80s;  make lint clean
make test           5765 passed, 27 skipped in 317.64s
```
