# UX-731: a ratio guard with a two-millisecond denominator

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-551 (wall clock is a property of the machine), UX-716 (the neighbouring decay) | **Serves:** the round whose gate goes red on a green tree | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

`test_performance_scales_subquadratically` reds intermittently on a
loaded machine and passes alone. Round 98's full gate:

```text
FAILED tests/unit/test_graph_performance.py::test_performance_scales_subquadratically
====== 1 failed, 7343 passed, 82 skipped, 1 warning in 749.22s (0:12:29) =======
$ pytest tests/unit/test_graph_performance.py::…subquadratically -q
1 passed in 2.95s
```

"Flaky" is not the diagnosis. Measured here, five trials of the guard's
own code path (min of 5 repeats each, as it does), on a 4-core box:

```text
trial 1: 0.0016s -> 0.0075s   ratio 4.61x   (threshold 10.0)
trial 2: 0.0017s -> 0.0077s   ratio 4.55x
trial 3: 0.0017s -> 0.0077s   ratio 4.63x
trial 4: 0.0017s -> 0.0076s   ratio 4.47x
trial 5: 0.0018s -> 0.0078s   ratio 4.34x
$ nproc; cat /proc/loadavg
4
0.83 1.59 3.25 1/2846 31278
```

The ratio sits at the theoretical O(N+E) value, with 2.2x of headroom.
What has no headroom is the **denominator**: 1.7 ms. `make test` runs
`-n auto` — four workers on four cores, and the 15-minute load average
above is 3.25 — so one scheduler preemption inside a 1.7 ms window
inflates `small_elapsed` and the quotient with it. min-of-5 protects a
*mean* against one slow trial; it cannot protect a minimum whose true
value is under two milliseconds on a contended box.

The guard's own docstring records this fix being sized once already,
for "sub-50ms measurements on a shared VM" (P4-06, single sample, 8x).
The machine got faster and the window fell by more than an order of
magnitude; the fix did not move with it. That is the same decay
`UX-716` records for the timing reference, in a guard rather than a
ledger.

## Required Fix

The claim is *the algorithms are O(N+E), not O(N²)*, and the
instrument reads wall clock over 1.7 ms — a proxy, and the shape
`fixing-guide` §5 names. Two routes, and the choice is the judgement:

- **Grow the denominator.** N=500 → a size whose baseline is tens of
  milliseconds, so contention is a small fraction of it. Costs suite
  seconds and the file has a tier.
- **Stop timing.** Count the operations the three functions perform —
  edges visited, dict lookups — and assert the count scales linearly.
  A counter is not a proxy and does not care what else the box runs.

The second is what the claim actually says. Measure the cost of both
before choosing; state which and why in the Outcome.

## Out of Scope

- Raising the 10x threshold. **Declined**: it widens the guard against
  a defect it exists to catch, to work around an instrument problem.
- The three other O(N²) hotspots the docstring names as out of scope
  (`compute_reachability`, `compute_dominators`, the ready-queue
  metrics). P1-21 holds them.

## Acceptance Test

The guard's verdict is unchanged by load: run it against a busy box
and against an idle one and the assertion's input moves by less than
its margin. Mutation: reintroduce a quadratic rescan in
`compute_unweighted_depth` — red on both.
