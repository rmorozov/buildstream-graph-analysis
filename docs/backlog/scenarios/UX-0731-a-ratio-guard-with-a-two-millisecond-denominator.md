# UX-731: a ratio guard with a two-millisecond denominator

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-551 (wall clock is a property of the machine), UX-716 (the neighbouring decay) | **Serves:** the round whose gate goes red on a green tree | **Topic:** guards | **Shape:** judgement | **Area:** tools

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

## Outcome

**The decision, taken here: stop timing.** Both routes measured before
choosing, as the Required Fix asks.

Route 1, grow the denominator. N=9000 is the first size whose window
is tens of milliseconds, and its large partner would be N=36000:

```text
N=500:  fixture 0.002s  measured window  1.91ms  5 repeats incl. load 0.05s
N=9000: fixture 0.036s  measured window 44.76ms  5 repeats incl. load 1.16s
```

~6 s for the pair, and still a clock: 44 ms buys headroom against a
preemption, it does not remove one. Route 2, count the work:

```text
trial 1: small 33032 (0.040s)  large 132032 (0.169s)  ratio 3.997x
trial 2: small 33032 (0.040s)  large 132032 (0.157s)  ratio 3.997x
trial 3: small 33032 (0.040s)  large 132032 (0.173s)  ratio 3.997x
```

Identical to the event across trials, 0.21 s, and nothing the box is
doing can reach it. Route 2, and the row's own reasoning was right:
"the algorithms are O(N+E)" is a claim about work, and a line event is
work the interpreter did.

**The close, measured.** `sys.settrace` counts line and return events
whose frame is in `bga/graph/edg.py` or
`bga/attribution/blame_chain.py`; loading and normalising stay outside
the trace, as they stayed outside the clock. The threshold is
**unmoved at 10x** — the instrument changed, the claim did not, and
`Out of Scope` declined widening it.

```console
$ pytest tests/unit/test_graph_performance.py -q
4 passed in 0.83s
```

Faster than the version it replaces (5 repeats x 2 sizes, declared
1.2 s in `tests/tiers.py`, 2.19 s in `ci_reference.json`), so the tier
does not move.

**The mutation table.**

| mutation | clause that reds |
|---|---|
| a quadratic rescan of `graph.dependencies` inside `compute_unweighted_depth`'s Kahn loop — the Acceptance Test's own | `test_four_times_the_graph_is_not_sixteen_times_the_work`: `4x the graph took 15.21x the steps (535030 -> 8140030)` |
| `_MEASURED` names `bga/graph/edge.py`, a path nothing matches (vacuity: both counts 0, ratio undefined) | `test_every_measured_module_is_reached` |
| the reading becomes a clock again — `steps[where] += 1 + (time.perf_counter_ns() % 2)` | `test_the_count_does_not_move_between_runs`: `40587 vs 40636` |

Applied to scratch copies (`edg.pristine.py`, `perf.pristine.py`) and
reverted from those copies, not `git checkout --`; `__pycache__`
cleared between runs.

**One mutation that did not red, and what it means.** Dropping the
module filter so every traced frame counts left all four clauses
green: the frames executing inside those three calls are the same
frames every run, so the count stays deterministic even when the
filter stops filtering. The determinism clause therefore does not
guard the *filter* — `test_every_measured_module_is_reached` does —
and M3b above is what it does guard.

**The neighbouring red, recorded rather than fixed.** Round 98's same
gate also failed `test_a_project_directory_still_gets_the_project_shaped
_error`: 56.10 s alone against its own 120 s subprocess cap, on a
machine whose spread was 2.2x the same day. Same class, different
guard, and out of this row's scope — it is a subprocess cap, not a
ratio.
