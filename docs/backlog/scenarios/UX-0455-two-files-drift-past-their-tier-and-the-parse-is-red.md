# UX-455: two files have grown past the tier they are listed in

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 71, running `make test-tiers` while closing `UX-451` | **Serves:** the contributor whose `make test-medium` quietly costs a minute more than the tier says | **Topic:** guards | **Area:** tools

## Motivation

`make test-tiers` is red, and not on anything `UX-451` touched.
Measured single-process on a developer machine, against the unmodified
tree:

```console
$ for f in test_the_page_moves_between_runs \
           test_a_command_renders_as_a_command \
           test_the_agent_configuration_holds; do
    PYTEST_XDIST= python3 -m pytest tests/unit/$f.py --durations=0 -q ...
  done
test_the_page_moves_between_runs   18.39s   listed medium at 13.5s
test_a_command_renders_as_a_command 1.36s   listed small
test_the_agent_configuration_holds  0.74s   listed small
```

Two are real drift. `test_the_page_moves_between_runs.py` is past
`LARGE_FLOOR_S` (15.0s) and listed medium at 13.5s;
`test_a_command_renders_as_a_command.py` is past `MEDIUM_FLOOR_S`
(1.0s) and listed small.

The third is **not** drift and is the reason this row says so: the
parallel run reported it as medium, and measured on its own it is
0.74s - under the floor. Under `-n auto` a file waits on a worker, and
the drift parse reads a report from a contended run. That is worth
knowing before someone moves it.

`UX-418` filed exactly this shape for three other files and fixed them;
this is the same finding one round on, which is what the parse is for.

## Required Fix

- Re-measure all three single-process and move the two that really
  drifted, each with its seconds, the way `UX-418` did.
- Decide what to do about the contention artefact: either the drift
  parse reads a single-process report, or it states that a file within
  one worker-slot of a floor is not evidence. A parse that reports a
  file nobody should move is a parse people learn to skim.

## Out of Scope

- **`test_the_handoff_box_is_measured_served.py`**: `UX-451` moved it
  to large with its own before/after measurement, in that commit.
- **The floors themselves**: `tests/tiers.py`'s 1.0s and 15.0s are
  settled, and `UX-418` re-argued them last round.

## Acceptance Test

```bash
make test-tiers
```

exits 0, with each moved file's new seconds in `tests/tiers.py`'s
comment beside it, and the contention decision recorded here.

## Outcome (round 71, 2026-08-31)

### The three, re-measured alone in one process, three runs each

```console
$ for f in test_the_page_moves_between_runs \
           test_a_command_renders_as_a_command \
           test_the_agent_configuration_holds; do
    for i in 1 2 3; do
      PYTEST_XDIST= python3 -m pytest tests/unit/$f.py --durations=0 -q ...
    done
  done
test_the_page_moves_between_runs     18.30 / 18.33 / 18.28s   listed medium at 13.5s
test_a_command_renders_as_a_command   1.35 /  1.34 /  1.37s   listed small (default)
test_the_agent_configuration_holds    0.72 /  0.73 /  0.72s   listed small (default)
```

Two moved, each with its seconds beside it in `tests/tiers.py`:
`test_the_page_moves_between_runs.py` to **large** at 18.3s (three
seconds past the 15.0s floor, not a hair), and
`test_a_command_renders_as_a_command.py` to **medium** at 1.4s.

### The contention artefact, and what it turned out to be

The item offered two ways to handle the third file. Before choosing,
the thing itself was measured — over the 145 files whose `tiers.py`
comment records their seconds, this run's parallel/recorded ratio:

```text
population 145 files
median 1.010    q1 0.916   q3 1.099   min 0.054   max 5.608
```

**There is no contention factor to divide out.** The suite as a whole
runs at its recorded per-file cost under `-n auto`. So "a file within
one worker-slot of a floor" — the item's own second option — has no
number behind it, and widening the floors would be widening them for
385 files to accommodate one.

The one file is at **1.31s parallel against 0.72s alone, a ratio of
1.82**, outside that q3. It is *this file* that is contended, not the
run. Which names the defect precisely, and it is fixing guide §5's:
**the floors are single-process seconds and the parse feeds them a
parallel measurement.** An instrument reading a proxy for the thing it
names, in the tool that exists to catch exactly that.

### The decision: confirm the accused, do not re-measure the suite

The item's first option — have the parse read a single-process report —
is right about the quantity and wrong about the cost: single-process,
this suite is not the 10m40s the documents claim. Measured while
writing this, it was **25% done after 19 minutes**, so ~76 minutes
against `make test`'s 4m43s. Sixteen times the gate's cost to check a
number that is normally about no files at all.

So only the **accused** are re-measured, alone and in one process:
`dev_tier_drift.confirm()`. On a green tree that is nothing; on the run
that found this it was 21s for three files. The seconds a kept row then
prints are the confirmed ones, so what a reader copies into `tiers.py`
is already the quantity the floors are in.

Why alone rather than inside a single-process suite: a file run by
itself pays all of its own imports, so its cost alone is an **upper
bound** on its cost within a single-process suite. For a gate that only
reports files as *too slow*, an upper bound is the conservative
direction — a candidate the confirmation clears is under the floor in
the stricter reading too.

A cleared file is **printed**, not dropped: it is a fact about the
reader's runner, and silence would have made this item unfindable.

### What holds it, and the mutations

`tests/unit/test_a_candidate_is_confirmed_alone.py`, seven clauses:

| # | mutation | clause that went red |
|---|---|---|
| C1 | `confirm()` returns its rows unchanged (the state before this item) | `..._under_the_floor_clears_it`, `..._carries_the_confirmed_seconds` |
| C2 | a confirmation that could not run is read as a clearance | `..._could_not_run_is_not_a_clearance` |
| C3 | the kept row keeps the parallel seconds | `..._carries_the_confirmed_seconds` |
| C4 | `alone_seconds` passes `-n auto` after all | `..._is_really_single_process` |

**C4 is the finding.** On its first run it left the file **green**. The
clause it was aimed at asserted only that the real re-run came back
under the floor — and one file on its own under xdist has almost
nothing to contend with, so the number barely moves. *A guard on the
result of a measurement is not a guard on the measurement.* The clause
was rewritten to observe the `subprocess.run` call itself — its argv
and its environment are where the quantity is decided — and C4 then
reddened it.

### The guard committed this item's own defect, and CI caught it

`2eb706d` went red on **all four interpreters**, on the clause added
here:

```text
FAILED tests/unit/test_a_candidate_is_confirmed_alone.py::test_the_measurement_is_a_real_single_process_run
AssertionError: tests/unit/test_the_agent_configuration_holds.py measured 1.47s
alone, at or over the 1.0s medium floor - either the file grew and belongs in
MEDIUM now, or this machine is loaded
assert 1.4749999999999959 < 1.0
```

That clause asserted `alone < MEDIUM_FLOOR_S` — **a wall-clock number
against a threshold, on a machine the guard does not control**, and
running inside `make test`'s own `-n auto` suite, so the "alone"
subprocess had three workers for company. It is precisely the defect
this item exists to fix, committed in the guard written to fix it, and
its own failure message says so: *"or this machine is loaded"*. It was.

Which side of a floor a file lands on is a fact about a runner. It
belongs to `confirm()`'s caller — which prints it — and never to an
assertion. The clause was replaced by two that no runner can decide:

- the measurement **happened and was timed** (`is not None`, `> 0`);
- a file that cannot be run comes back `None` **for real** rather than
  monkeypatched — the un-mocked half of the exit-code fix below, and
  deterministic.

| # | mutation | clause that went red |
|---|---|---|
| C5 | `alone_seconds` always returns `None` | `..._returns_seconds`, `..._is_really_single_process` |
| C6 | the exit-code guard removed, so an empty junit reads as 0.0s | `..._comes_back_unmeasurable` |

Worth stating plainly: local `make test` was green on the commit that
shipped this. The suite here runs on a machine where that file costs
0.72s; CI's costs 1.47s under load. A guard that passes on one clock
and fails on another is the same finding one level up, and the reason
`UX-418`'s rule about clocks is a rule.

### Two defects the existing guards found, both real

`make test-tiers` went red on the first attempt, on two guards this
item had not touched:

- `test_a_slow_file_says_which_file.py` fabricates a junit document
  putting a real 0.02s file at 51.0s. The confirmation correctly
  cleared it. That clause is about the **message**, so it now passes
  `--no-confirm` — the flag's whole reason for existing — and a new
  clause beside it runs the *same* fabricated report through the
  shipped path and asserts it comes back cleared and said so, so
  `--no-confirm` is not a way past the gate that nothing notices.
- `alone_seconds` could not tell "ran and cost nothing" from "did not
  run": pytest writes a junit document on a collection error too, an
  empty one summing to 0.0s, which would have cleared every candidate
  the re-run could not reach. It now returns `None` outside pytest's
  tests-ran exit codes (0 and 1). **A confirmation that confirms by
  failing** is worse than no confirmation, and this is the shape of it.

### Deviation from the Required Fix

The third file is **not** moved, which is what the item predicted; the
second bullet's "one worker-slot" framing was replaced by a measurement
that says there is no such margin to state, and by a confirmation step
instead.

### Verification

The figures below are from the first landing; the clause above was
replaced afterwards and re-verified at `make test` **5506 passed, 28
skipped in 283.00s** with `make test-tiers` still `exit 0`.

```console
$ make test-tiers
5503 passed, 28 skipped, 1 warning in 283.12s (0:04:43)
tiers ok: 386 file(s) measured against the declared floors (medium 1.0s, large 15.0s)
exit 0

$ make lint
All checks passed!
```
