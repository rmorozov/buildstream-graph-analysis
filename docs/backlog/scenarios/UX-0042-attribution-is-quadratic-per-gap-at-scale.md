# UX-42: attribution re-derives resource saturation from scratch per wait gap, so a 1200-element build takes 68s to analyze

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — (P1-16/P1-21 did earlier performance work on different functions) | **Topic:** analysis

## Motivation

Round-2 scale probe. A 1202-element run - roughly a six-minute real build - takes **68 seconds** to analyze:

```text
$ time bga analyze -d /tmp/run-scale-1200
real  1m7.784s

$ time bga analyze -d /tmp/run-06-ux31      # the 11-element example, for contrast
real  0m0.258s
```

`cProfile` over the same analysis is unambiguous about where it goes:

```text
   ncalls  tottime   cumtime  function
        1    0.006   197.240  bga/analyzer.py:998(analyze)
        1    0.007   194.055  bga/analyzer.py:433(_compute_attribution)
     1355    0.498   193.918  blame_chain.py:788(_classify_wait_gap)
     1355  101.235   193.351  blame_chain.py:446(_resource_saturation_intervals)
112269344   25.387    34.104  enum.py:1232(__hash__)
110546740   18.141    18.147  {built-in max}
110522846   17.499    17.500  {built-in min}
```

(Wall-clock under the profiler is ~3x the unprofiled 68s; the *proportions* are the point.) **98% of the analysis is one function**, called once per wait gap, and it performs **112 million `Resource` enum hashes**.

The cause, read from `bga/attribution/blame_chain.py::_resource_saturation_intervals`, is a per-gap `O(N²)`:

1. It scans all `self.tasks` to build `relevant_others`, constructing two sets per task (`set(required_with_capacity) & set(other.resources)`) - that is where the enum hashing comes from.
2. For each boundary sub-interval within the gap (up to `O(N)` of them, since every other task's start and finish is a boundary), it scans `relevant_others` **again** to count occupancy.

So the work is `O(gaps x tasks x boundaries)`. At 1355 gaps and 1202 tasks that is ~10⁸ inner iterations, which matches the profile exactly.

The correctness of the function is not in question - `UX-19` made it a real multi-cycle sweep for good reason. What is wrong is that it re-derives, from scratch and per gap, an occupancy timeline that is a property of *the whole run* and does not change between gaps.

Two things make this worse than a generic "it's slow at scale" complaint:

- **`bga graph` costs the same 67 seconds.** The narrower subcommands are documented as "thin, narrower slices of the same full `analyze` report - reach for one of them instead of grepping `analyze`'s output", but `bga graph` renders no attribution and still pays for all of it. See `UX-47`.
- **`bga sweep` runs the whole replay across a capacity range in 14.8s** on the same run - so the expensive part is not "there is a lot of data here".
- **The machinery to avoid it already exists.** `bga/occupancy/sweep.py` computes exactly this - a per-resource occupancy interval sweep over the whole run - once, and the analyzer already calls it.

## Required Fix

Compute the resource-occupancy timeline **once per run**, then have `_resource_saturation_intervals` answer each gap by slicing that precomputed structure rather than rebuilding it.

Concretely, when picked up:

1. Build, once, per resource: the sorted list of change points and the occupancy count in each resulting interval - which is what `bga/occupancy/sweep.py::compute_occupancy_stats` already produces. Check whether its existing output can be consumed directly before adding a second, parallel structure.
2. Per gap, binary-search into that timeline for the window and emit the maximal constant-saturation sub-intervals. That turns each gap from `O(N²)` into `O(log N + k)` for `k` intervals actually inside the window.
3. Holder attribution (which tasks were holding the resource during a saturated interval) needs the same treatment - an interval → holders index built once, not a rescan per interval.

Two cheap, independent wins worth taking in the same pass even if the restructure is deferred: hoist `set(other.resources)` out of the inner loop (it is rebuilt per gap per task), and key the capacity dict by something cheaper to hash than an enum member in the hot path.

**Do not weaken the analysis to buy speed.** `UX-19`'s re-saturation sweep and the holder-attribution detail are load-bearing for `I4`; the output of this function must be identical before and after, and the acceptance test below says so.

## Out of Scope

- `UX-47` (narrow subcommands paying for work they discard). Independent, and cheaper - fixing it would make `bga graph` fast even before this lands, but would not help `bga analyze`.
- Any change to what attribution *means*. This is purely how it is computed.

## Acceptance Test

1. `bga analyze -f json` output is **byte-identical** before and after on every fixture in `tests/fixtures/topologies.py`, on the `mixed_task_kinds` golden fixture, and on a real `examples/06-macro-micro-optimization` capture.
2. The 1202-element scale fixture analyzes in a small fraction of the current 68s (a target worth committing to when the approach is chosen - an order of magnitude is the reasonable ask given the complexity change).
3. The determinism harness (`I11`) still passes N-run byte-identical.
4. A profile of the same run no longer shows `_resource_saturation_intervals` as the dominant cost. Full suite green.

## Fix Implemented

A per-resource occupancy timeline (`_ResourceTimeline`) is built **once per run** and sliced per gap by binary search, replacing the per-gap rebuild.

The correctness argument that makes the slicing exact: because the boundary set already contains every relevant start and finish inside the window, within any sub-interval each task either *fully covers* it or does not overlap it at all. So the original's `other.start_us <= t1 and other.finish_us >= t2` test is simply "is this task holding the resource at `t1`" - an indexed lookup rather than a rescan. Holder time is then `t2 - t1` for every holder, with no per-task overlap arithmetic.

Per gap this is `O(log N + k)` for `k` intervals actually inside the window, against the previous `O(tasks x boundaries)`.

Two cheap wins the doc also asked for came from the follow-up profile rather than from guessing: holders are stored as `(key_str, task)` pairs so the inner loops never call `TaskKey.__eq__` (8.5M calls) or `str(task_key)` (2.5M) again.

### Results

```text
$ time bga analyze -f json /tmp/run-scale-1200
before   1m35.531s
after    0m03.164s          <- 30x
```

`_resource_saturation_intervals` fell from **101s self / 193s cumulative** to **0.8s self / 2.1s cumulative** under the profiler, and is no longer the dominant cost - acceptance test 4. `bga analyze` on `examples/06` is unchanged at ~0.3s; this was never a small-graph problem.

### Byte-identity, and the two bugs the oracle caught

Output is byte-identical before and after on all five fixtures - `examples/06` baseline, `optimized/`, the `--builders 2` capture, the `mixed_task_kinds` golden fixture, and the 1202-element scale run - and the determinism harness reports the same hash across three consecutive scale runs.

**Byte-identity on real fixtures was not sufficient to establish correctness**, which is worth recording. A dedicated oracle test (`tests/unit/test_resource_saturation_timeline.py`) transcribes the original algorithm naively and compares against it across generated shapes, and it caught two real segmentation defects that all five real fixtures had missed:

1. **Zero-duration tasks contribute boundaries.** A structural element with `start == finish` can never *hold* a resource across a non-empty interval, but the original still added its timestamp to the boundary set. The first version of the timeline dropped such tasks entirely, merging two sub-intervals into one.
2. **A task's own boundaries are not boundaries of its own gap.** The original skipped `other.task_key == task.task_key` when building the boundary set; the shared timeline naturally includes every task, so the waiting task's own start/finish produced spurious splits. Fixed by tracking how many tasks contribute a boundary at each point, so a point contributed *only* by the waiting task can be dropped - two points to check per gap, so it stays `O(1)`.

Neither changed a saturation verdict or a holder set; both changed how the gap was *segmented*, which `_build_holder_info` merges over - which is exactly why the real fixtures did not catch them, and why "the output is identical" would have been a false negative for this class of bug.

Tests: 9 new, all oracle comparisons plus one asserting the per-run structure is built once and reused. Full suite 812 passed (up from 803), `make lint` clean.

## Verification Log

Filed 2026-08-16 (round 2). Both timings are real `time bga ...` runs on the same host. The profile is a real `cProfile` of the same analysis, sorted by cumulative time. The complexity characterization was read from `bga/attribution/blame_chain.py:446-510` directly, and cross-checked against the profile's own call counts (1355 calls, 112M enum hashes) rather than asserted from the code alone. The 1202-element fixture is synthetic - a real capture at that size was not available in this session - so this task exercises the *analysis* side at scale, not the capture side; the generator uses a real dependency-respecting greedy schedule onto 16 builders, so the trace is internally consistent rather than random.

Reproduce with `tools/gen_synthetic_scale_run.py /tmp/run-scale-1200`, committed in the same round so this doc's acceptance test is runnable. The 68s and the profile above are from the original ad-hoc run (3206 edges); the committed fixture is slightly denser at 3500 edges and analyzes in **115s**, which is the same defect a little worse - the cost is superlinear in exactly the way the complexity argument predicts, so the denser graph is the more honest fixture to hold the acceptance test against.
