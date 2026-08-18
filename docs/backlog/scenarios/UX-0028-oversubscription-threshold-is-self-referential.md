# UX-28: the oversubscription check's bar is BuildStream's own defaults, so how sensitive it is depends on the host size rather than on the host

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-12, UX-15, UX-16 (all done - this is a threshold-semantics fix to the check they built)

## Motivation

> **Filed-then-corrected.** This task was originally filed claiming the check "cannot fire on real contention", citing a Plane 2 measurement that `core.bst`'s compile process-lifetime rose from 11.05s to 20.00s between two real runs of `examples/06-macro-micro-optimization`. That evidence does not support the claim and the original framing was wrong: the two runs are not comparable (in the baseline that element ran essentially alone; in the optimized run six elements compiled concurrently), and the run with the *higher* per-element cost was **30.5% faster overall** - that is beneficial parallelism, not oversubscription harm. `UX-09`'s own real 6-configuration table also shows the check firing correctly on the configuration it measured as slowest. The Motivation below is the re-verified defect, which is different and provable. Left visible rather than quietly rewritten, since "don't trust a claim of done without independently re-verifying it" applies to this backlog's own filings too.

`bga/analyzer.py::_check_process_oversubscription` (UX-12, hardened by UX-16, extended by UX-21, delegated to by UX-17) compares this run's potential concurrent-process demand against what BuildStream would run unconfigured:

```python
actual_demand  = builders * resolved_native_max_jobs
default_demand = 4 * min(governing_cores, 8)

if actual_demand > default_demand:    # -> resource_oversubscription
elif actual_demand < governing_cores: # -> resource_undersubscription
```

`default_demand` stops growing at 8 cores, while `governing_cores` does not. So the ratio-to-cores at which the check fires collapses as the host gets bigger:

| governing cores | oversubscription fires above | ... as a multiple of cores | undersubscription fires below |
|---|---|---|---|
| 4 | 16 processes | **4.00x** | 4 |
| 8 | 32 | **4.00x** | 8 |
| 16 | 32 | **2.00x** | 16 |
| 32 | 32 | **1.00x** | 32 |
| 64 | 32 | **0.50x** | 64 |

Two things follow, both real:

1. **The check's sensitivity is a function of the machine, not of the workload.** The same `builders x max-jobs`-to-cores ratio is silent on a small host and a violation on a large one. Nothing physical changes across that boundary; only BuildStream's own default did.

2. **On any host above 8 cores there is a band that is reported oversubscribed while being below one process per core.** Concretely, 8 builders x 5 max-jobs = 40 potential processes on a 64-core host: `40 > 4 * min(64, 8) = 32` fires `resource_oversubscription`, while 40 is also less than 64, which is the condition the very next branch calls *leaving cores idle*. A build using well under half its host is told it is oversubscribed.

The bar itself is also self-referential in a way that is worth naming: "BuildStream's own defaults" is a moving target that says nothing about this host. It happens to be a defensible number on a 4-core machine and an indefensible one on a 32-core machine, and neither fact is visible from the code.

`UX-09`'s real 6-configuration timing table on a real 4-core host is the only measured evidence this repo has about when oversubscription actually costs time, and it also shows what a correct bar has to respect:

| configuration | potential processes | x cores | real wall-clock |
|---|---|---|---|
| 4 builders x 4 max-jobs | 16 | 4x | **6.5s - the fastest of the six** |
| 4 builders x 16 max-jobs | 64 | 16x | 6.4s (~flat) |
| 8 builders x 8 max-jobs | 64 | 16x | 7.2s (**~11% slower**) |

So a bar at one process per core would flag the measured-optimal configuration, and the measured harm appears by 16x. Note also that the two 16x rows *disagree*: same product, different outcome. `UX-09` explains why - each library there had only two source files, so `4 x 16`'s extra `make -j` slots were never claimed. Potential demand overstates real demand, and `builders` is the half of the product that has no such escape hatch.

## Required Fix

Make the comparison about the real governing core count rather than about BuildStream's defaults, and add the sharper signal the product check structurally cannot provide.

1. Compare `actual_demand` against `governing_cores` times an explicit, named, documented ratio, and keep BuildStream's default as *context in the message* rather than as the bar.
2. Add a distinct dispatch-level check on `builders` alone: BuildStream really does dispatch that many elements concurrently and each runs at least one process, so more builders than cores oversubscribes the host even at `--max-jobs 1`. This is also what separates `UX-09`'s two same-product configurations.
3. Say what the ratio is and why, in the violation payload as well as the log line.

## Out of Scope

- `UX-29` (`native_max_jobs` never being auto-extracted). That was the *other*, independent reason the check did not fire on a real run; done separately.
- Feeding Plane 2's *measured* concurrency back into the check - the genuinely right long-term answer, and much larger. See `UX-32`, which builds the measurement it would consume.
- `UX-21`'s memory guard, which has its own thresholds and its own separate question.

## Acceptance Test

1. `UX-09`'s measured-best configuration (4x4 on 4 cores) produces no violation; its measured-slowest (8x8 on 4 cores) does.
2. A configuration below one process per core is never reported as oversubscribed, on any host size.
3. The same demand-to-cores ratio earns the same verdict regardless of host size.
4. `UX-15`'s declared-budget precedence and `UX-16`'s `--max-jobs 0` sentinel resolution are unchanged. Full suite green.

## Fix Implemented

`_OVERSUBSCRIPTION_DEMAND_RATIO = 8.0`, applied as `actual_demand > governing_cores * ratio`. The constant carries its own derivation in the source: a bar at or below 4x would flag `UX-09`'s measured-fastest configuration, and the measured harm appears by 16x, so 8x sits strictly between the two real data points and is host-size-independent. It is documented as an honest interpolation between two measurements on one real host, not as a derived constant - including the fact that the two 16x rows disagree with each other.

`default_demand` is still computed and still reported, now purely as context ("BuildStream's own unconfigured default here would be N"), never as the bar. The violation payload gained `oversubscription_ceiling` and `demand_ratio` so a consumer can see what was compared against what.

New `dispatch_oversubscription` violation for `builders > governing_cores`, with its own report line. It is deliberately a separate type rather than folded into the existing one: it is a different failure mode (dispatch concurrency, not potential process count), it is strictly stronger evidence (builders are really dispatched; `max-jobs` slots may never be claimed), and it is what actually distinguishes `UX-09`'s 8x8 from its 4x16.

Tests: 9 new (`tests/unit/test_oversubscription_threshold.py`), pinned to `UX-09`'s real measurements rather than to the constant - measured-best not flagged, measured-slowest flagged, the dispatch check separating the two same-product configurations, the below-one-process-per-core case on a large host, ratio-invariance across five host sizes, plus `UX-15`/`UX-16` behaviour preserved. Four existing `UX-16` sentinel-resolution fixtures were re-pointed at configurations that still exceed the new bar (their subject - that `--max-jobs 0` resolves to `min(cores, 8)` rather than being read as missing - is unchanged and still asserted).

## Verification Log

Filed 2026-08-16 from a real session; **Motivation corrected the same day** after re-verifying the original claim against `UX-09`'s own timing table and finding it unsupported - see the note at the top. The corrected defect was verified by direct computation over the real threshold arithmetic read from `bga/analyzer.py`, and by exercising the real check across `UX-09`'s six measured configurations.

Real verification of the implemented fix, running the real `_check_process_oversubscription` against each of `UX-09`'s measured configurations:

```text
  4x4  on  4 cores  UX-09 BEST           -> ['(silent)']
  8x8  on  4 cores  UX-09 11% WORSE      -> ['resource_oversubscription', 'dispatch_oversubscription']
  4x16 on  4 cores  UX-09 ~flat          -> ['resource_oversubscription']
  1x1  on  4 cores  serial               -> ['resource_undersubscription']
  8x5  on 64 cores  40 procs on 64 cores -> ['resource_undersubscription']
```

Acceptance Test items 1-4 all confirmed. The last row is the corrected defect: that configuration used to report `resource_oversubscription` while sitting below one process per core, and now correctly reports idle capacity instead. The `4x16` row remains a known, acknowledged false positive of any config-level check - `UX-09` measured it as harmless because the extra `make -j` slots were never claimed, which is precisely the potential-vs-realized limitation `_check_process_oversubscription`'s own docstring already names and which `UX-32` would be needed to resolve. Full suite green (687 passed, up from 678), `make lint` clean.
