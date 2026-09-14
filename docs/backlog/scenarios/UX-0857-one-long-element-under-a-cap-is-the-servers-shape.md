# UX-857: one long element under a cap is the server's shape

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-848, UX-856 | **Found by:** round 119, the user | **Serves:** R4 (an llvm-sized element alone on the critical path takes the whole machine) | **Topic:** capture | **Area:** examples | **Shape:** judgement

## Motivation

BuildStream caps an element's `max-jobs` at 8 by default. On a 40-core
server an element the size of llvm, alone on the critical path while
half the graph waits on it, builds at `-j8` with 32 cores idle; under
the mode it takes every token the pool has. `examples/10` cannot show
it: four elements at `-j4` on four cores are saturated at `off` already,
and the mode read slower at every stage. A four-core box models the
server faithfully anyway: one long element under a `max-jobs` below the
core count.

## Required Fix

`examples/11-serial-giant/`: one cmake element compiling 256 generated
C files into one binary (the giant), three small elements that depend
on it, `max-jobs: 2` in `project.conf` (the server's 8 of 40, scaled),
`all.bst` on top; the `bst-examples` job captures it twice from a cold
cache (`bga snapshot --jobserver off`, then `--jobserver auto`, the
switch from `UX-856`) and `bga compare` prints both walls; the README
carries this box's two numbers, dated, with the expected ratio (the
giant at 2 jobs against 4 tokens) beside the measured one.

## Out of Scope

A real llvm build; a machine with more cores than this box.

## Acceptance Test

`tests/unit/test_the_examples_build.py` gains the CI step's assertion
for 11 (a wall for each run, `auto` under `off`); mutation: point the
second capture at the first's snapshot - the compare refuses (red). The
two walls from this box pasted in the Outcome.

## Outcome

**Gap measured (width):** `off`: `peak_work_concurrency 2, requested_
jobs 2, achieved_vs_requested 1.0` - the `-j2` cap held exactly. `auto`:
`peak_work_concurrency 3` (above 2 - tokens taken), `jobserver_pool`
`ceiling 3, capacity 4, moves 0, pool_min 2, pool_max 2` - the ledger's
first row `pool 2, hold, "no sample yet"`, last `pool 2, hold, "busy 4.0
within band"`: never moved, because the box read ~4.0 busy cores
throughout. `jobserver_decisions`: `giant.bst` `joined`, policy
`cmake_meson` - the mechanism works; the pool cannot widen past 3 on 4
cores (8 of 40 on the server modelled), so no argv/`MAKEFLAGS` debugging
was needed.

**Gap measured (phase):** at the original 1800 lines/file, `giant.bst`'s
measured CPU (`cc1` 25.30s of 32.70s total) was under half its own
72.07s wall. Raised to 9800 lines/file (`gcc -c` on one file: 0.47-
0.55s standalone, matching the ~0.5s target); real captures: `cc1`
121.44s (87% of the element's own 135.19s measured CPU), measured-
process span 89.01s, but the element's Plane-1 wall is 140.25s - a ~50s
gap `generate.sh` (8.78s standalone) and `cmake` configure (0.40s CPU)
do not account for; the remainder is BuildStream's own per-element
staging/install/cache steps plus this shared box's contention
(`/proc/loadavg` 7-10 on 4 cores throughout). Compile share: 63.5%
(`off`) / 65.5% (`auto`) - a 5.4x CPU jump barely moved this off its
original 64.8%, since the ~50s gap grew alongside it rather than
staying fixed. Not tuned further to force 70%.

**Close measured**, `python3 -m pytest tests/unit/test_the_examples_build.py -v`:

```text
tests/unit/test_the_examples_build.py::test_the_ci_step_11_captures_both_modes_from_a_cold_cache PASSED
tests/unit/test_the_examples_build.py::test_the_ci_steps_11_own_wall_assertion_matches_real_compare_output PASSED
tests/unit/test_the_examples_build.py::test_the_ci_steps_11_ordering_check_accepts_an_auto_under_off_reading PASSED
tests/unit/test_the_examples_build.py::test_the_ci_steps_11_ordering_check_refuses_this_box_s_own_real_capture PASSED
9 passed in 1.94s
```

Real captures, this 4-core box, 2026-09-14, cold cache both times, back
to back (`/proc/loadavg` ~8 throughout both):

```text
bga capture run --run-dir run-off  --jobserver off  examples/11-serial-giant plane2-off.json  -- bst build all.bst   -> Total Duration 147.16s
bga capture run --run-dir run-auto --jobserver auto examples/11-serial-giant plane2-auto.json -- bst build all.bst   -> Total Duration 163.14s
bga compare run-off run-auto -> Verdict: REGRESSED (+15.98s, +10.9%)
```

`giant.bst` alone: 140.25s -> 156.25s. Reproduced on a second back-to-
back pair (also +10.9%). `auto` genuinely ran wider (mean concurrency
2.79 of peak 3) and moved more compiler work (102.40s vs 89.01s work
span), but the element's own wall still grew - three compiler processes
plus `PoolController`'s 250ms thread on an already ~8-loadavg 4-core
box leaves less slack than `off`'s two, the same finding `10-jobserver`
made for its own saturated-box reason. Not tuned to read IMPROVED. The
quiet-box pair (load under 2, no other agents) is still to be measured;
the session runs it at the round's close and writes the numbers here.

**Mutation table:**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| CI step's `awk` ordering check (`auto` under `off`) | `exit !(auto < off)` -> `exit !(auto > off)` | `test_the_ci_steps_11_ordering_check_accepts_an_auto_under_off_reading`, `test_the_ci_steps_11_ordering_check_refuses_this_box_s_own_real_capture` | 2 of 9 |
| CI step's `XDG_CONFIG_HOME` export | line deleted | `test_the_ci_step_11_captures_both_modes_from_a_cold_cache` | 1 of 9 |
| CI step's ordering check on a tie (`auto == off`) | `exit !(auto < off)` -> `exit !(auto <= off)` | `test_the_ci_steps_11_ordering_check_refuses_a_tie` | 1 of 10 |
