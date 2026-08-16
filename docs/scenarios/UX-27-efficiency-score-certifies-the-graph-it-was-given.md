# UX-27: `efficiency_score` and `certified_headroom` certify the graph the run was given, so a badly-shaped build scores perfectly

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — (UX-02 defines the score this changes; UX-39 is the CI-facing consequence)

## Motivation

Real repro, `examples/06-macro-micro-optimization` (filed with this task; built for exactly this purpose), 4-core host, `bst --builders 4 --max-jobs 4 build all.bst`. The project is mis-optimized in three one-line ways: six independent libraries declared as a six-deep dependency chain, an unused `codegen.bst` build-dep on five of them, and `notparallel: True` on the heaviest element. The `optimized/` sibling fixes all three and changes nothing else.

Baseline:

```
Total Duration: 39.6s
  Efficiency Score: 1.00 (very efficient - remaining gains are mostly in reducing Critical Path's own work, not scheduling)
  Certified Headroom:          0.00s
  T∞ (observed critical path): 36.25s
  LB (resource lower bound):   36.25s
Attribution Breakdown:
  Execution On Chain Us        36.25s ( 91.6%)
  Resource Wait Us              0.00s (  0.0%)
CPU Utilisation:
  Useful                  40.25s
  Idle No Tasks          118.03s
```

After the three fixes:

```
$ bga compare /tmp/run-06-baseline /tmp/run-06-optimized
Verdict: IMPROVED  (total duration -12.07s, -30.5%, 39.57s -> 27.50s)
  Certified Headroom        0.00s ->      4.05s   (+4.05s)
  Efficiency Score           1.00 ->       0.83   (-0.17)
```

A 30.5% real improvement moved the tool's own headline efficiency number **down** 0.17 and its "room to improve" number **up** 4.05s. This is not a rendering bug and not a miscomputation - it is what the definitions say. `LB` is a lower bound over *this run's observed graph and observed durations*; a graph serialized into a chain has a critical path equal to its own total work, so `LB == T∞ == T_C` identically and the scheduler is tautologically perfect. `efficiency_score` (UX-02) is built on that ratio, so it measures *"did the scheduler pack the graph it was handed"* and never *"was that graph worth packing"*.

The consequence is that the tool's headline number is **anti-correlated with the thing a user is trying to do** across the entire class of problem that graph-level optimization exists to fix. On this build it also mis-directs every other ranked list: `Biggest Opportunity` is BuildStream's own 3.05s startup (7.7%) while 118.03s of task-occupancy capacity goes unused, and `Top Improvement Opportunities` claims a `best-case speedup 1.05x` against a real available speedup of 1.44x.

This was checked against the code, not inferred from the output: `bga/floors/` and `bga/replay/` derive `LB`/`T_C` purely from the observed graph plus `resource_capacities`, and `bga/report/text.py`'s `_CONFIDENCE_HIGH`-gated efficiency banding reads that ratio directly. Nothing anywhere in `bga/` compares the observed graph against any counterfactual shape.

Note this is *distinct* from the already-documented `UX-13` caveat (LB certifies against dispatch capacity, not CPU cores). Even with a perfect capacity model, a chain-shaped graph would still score 1.00.

## Required Fix

The tool needs a second, graph-aware efficiency signal that does not take the observed dependency graph as ground truth. Sketches, in increasing cost - a real design decision to make when picked up, not settled here:

1. **Work-vs-span ratio** (cheapest, no new capture): report `Σ observed task durations / (wall_clock × capacity)` alongside the existing score. On the baseline that is `40.25 / (39.57 × 4) = 25.4%`; on the optimized run `61.45 / (27.50 × 4) = 55.9%`. It moves the right way, needs nothing that isn't already ingested, and is the natural basis for `UX-39`'s CI gate. Its own known flaw - the numerator inflates under contention (the same work cost 40.25s of occupancy serialized and 61.45s when six elements ran concurrently) - must be stated honestly, not hidden.
2. **Counterfactual replay against a relaxed graph**: re-run `ReplayScheduler` with the dependency edges of *structural* elements (`stack`/`import`) dropped, or with each element's declared-but-unconsumed build deps dropped, and report the delta as "graph-shape headroom". `bga/structural/` already computes `choke_points` and `serialized_pairs`; this turns them into a number.
3. **Declared-vs-used dependency detection**: an over-declared build dependency (problem 2 in the repro) is in principle detectable by comparing declared deps against what an element's sandbox actually read - Plane 2 already traces every process's `--dir`-tagged sandbox. Substantially more work; note it as the eventual, real version.

Whatever is chosen, `efficiency_score`'s own banding text must stop saying *"very efficient"* for a run it cannot actually vouch for, and must name what it does and does not cover.

## Out of Scope

- Changing `LB`/`T∞`/`T_C`'s own definitions. They are correct and spec-mandated (Parts 14-18); the gap is that nothing sits *above* them asking whether the graph is the right one.
- `UX-13`'s dispatch-capacity-vs-CPU-cores caveat, and `UX-14`'s contention model - both real, both already filed and done, both orthogonal to this.

## Acceptance Test

1. Against `examples/06-macro-micro-optimization` baseline vs. `optimized/`, whatever new signal ships moves in the same direction as wall-clock across the pair (better after the fix, not worse).
2. The existing `efficiency_score` either stops claiming "very efficient" for the baseline run, or its banding text names the scope it certifies.
3. A genuinely well-shaped, well-scheduled run still scores well - the new signal is not simply "everything is bad".
4. Full suite green.

## Verification Log

Filed 2026-08-16 from a real hands-on optimization walkthrough (`docs/optimization-walkthrough-06.md`), on a real BuildStream 2.7.0 + `bwrap` + real `gcc 13`/`cmake 3.28` sandbox, 4-core host. Every number above is pasted from that session. `examples/06-macro-micro-optimization` was built as part of this filing specifically so the case is reproducible rather than argued.
