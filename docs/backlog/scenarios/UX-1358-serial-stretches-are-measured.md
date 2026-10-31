# UX-1358: an element's serial stretches are measured, and "already compute-bound" is refused while they are large

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R2, R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_serial_stretch_is_measured_not_averaged.py`

## Motivation

`bga correlate` says `bootstrap/gcc.bst` (40.2 min, 18.2% of the path) is "already compute-bound at 2.57 cores busy - nothing to gain from its parallelism". The same native report's `redundant_operations` holds a serial `autoreconf2.69` loop: 105 runs, 691 s across three gcc elements, 436 s in `bootstrap/gcc.bst` alone, one process at a time. A mean of cores busy is a proxy for "can this go faster with the same work"; the wall time spent at one busy process is the reading.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Plane 2 publishes, per element, the wall seconds its sandbox spent at or under one core busy - read from the per-element CPU sampler (utime+stime of every host process under the sandbox, per tick), never from a count of live or classified processes - and the command signatures alive longest in that time. Observed process concurrency (processes alive, all of them) is published apart and never as the CPU claim. Coverage is stated: no samples, too little of the span sampled, or a saturated host make the share **unknown with a reason**, and correlate then says "serial share is unknown" rather than either "already compute-bound" or refusing. Correlate refuses "compute-bound" when a measured share exceeds a stated line, and names the owning commands instead. The real-project capture samples CPU.

**Review correction (owner, on `6fc64c560`):** START/END intervals say a process is alive, not running: a waiting parent and its child counted two during serial work, one multithreaded process counted one while using several cores, and `WORK_BINARIES` misses an autoreconf/perl stretch. The first version's `serial_wall_s` was time at <=1 live `WORK_BINARIES` process - a proxy. Its >=400 s fixture check could not establish the claim.

## Out of Scope

Splitting configure from build phases (UX-102 owns that). Per-thread run-queue wait (`schedstat`) as a demand reading: contention is gated by the host's idle cores instead.

## Acceptance Test

Guards in `tests/unit/test_a_serial_stretch_is_measured_not_averaged.py`, each reddened by its own mutation: `collect2` waiting on `ld` (two live work processes, 1.0 core) is 100 s serial; one `ld.lld --threads=4` (one process, 4.0 cores) is 0 s; an autoreconf loop with zero classified work processes at 1.0 core is 40 s serial owned by `autoreconf2.69`; a low window beside 0.1 idle host cores is contended and the share unknown; children reaped between two ticks read 4 cores from the parent's `cutime`; the invocation log alone (no `--jobserver`) names the sampler's roots; an element with no samples, or a report that predates the fields, is unknown and correlate prints `serial-share-unknown`. On the fdsdk capture (`/home/claude/fdsdk-cap`, no sampled fields) `bga correlate` prints no "nothing to gain" sentence and `bootstrap/gcc.bst` reads unknown. The >=400 s `autoreconf2.69` reading on `bootstrap/gcc.bst` is the recheck capture's, read by the walker on its page.

## Decision

- `tools/bst_native_build_tracer.py`: the sampler writes `reaped_us` (cutime+cstime) beside `cpu_us` and a host row (`/proc/stat` busy/total) per tick, and follows the always-written invocation log as well as `--jobserver`'s decision rows, so every traced capture samples. `element_cpu_windows` turns rows into `(t0, t1, cores, host idle cores)` per element: a root's level is its tree's `cpu_us + reaped_us`, keyed through the invocation correction.
- A window is serial at <= `SERIAL_CORES_LINE` 1.25 cores (one core plus correlate's own `_COMPUTE_BOUND_CORES` margin: one thread accrues at most 1.0 core per window, a waiting parent ~0) beside >= `SERIAL_IDLE_CORES` 1.0 idle host core; a low window on a busier host is contended. `per_element_parallelism[]` publishes `cpu_sampled_s`, `cpu_contended_s`, `serial_wall_s`, `serial_share` (over uncontended sampled time), `serial_cores_line`, `serial_unknown`, `serial_owners`, `observed_process_concurrency` and `observed_process_concurrency_in_serial`. Unknown under `SERIAL_MIN_COVERAGE` 0.5 of the span sampled or uncontended. Additive: no schema bump.
- `bga/correlate.py`: `_compute_bound_step` - unknown -> `serial-share-unknown` with the reason; share over `_SERIAL_SHARE_LINE` 0.15 -> `serial-stretch`; else `already-compute-bound`. `bga/findings.py`'s `serial-stretch` reads known shares only.
- Page: unchanged code; the element card prints the join's advice.

## Outcome (2026-10-31, review rework)

**Gap measured** (owner's review of `6fc64c560`; fdsdk capture `/home/claude/fdsdk-cap`, `python3 -m bga.cli correlate run native-report.json` at `50120b532`):

```text
bootstrap/build/gcc-stage2.bst, bootstrap/gcc.bst, components/_private/gcc-base.bst (3 elements ...):
  - already compute-bound at 2.6-3.4 cores busy — nothing to gain from their parallelism; shortening them means less work
grep -c "nothing to gain" -> 3
cpu_time.per_element_series keys: ['buildstream-build', 'expat', 'libselinux', 'libsepol', 'unknown']   # pre-UX-1314 sampler, no bootstrap/gcc.bst
```

`serial_wall_s` was time at <=1 live `WORK_BINARIES` process. The capture workflow defaults `jobserver: off`, and since `UX-1314` the sampler took its roots only from `--jobserver`'s decision rows, so a default capture sampled nothing.

Real `/proc`, the tracer's own `ElementCpuSampler` at 2 s through the invocation log (`probe.py`, 4-core host at load 11.6-12.8, another session's suite running):

```text
parent-waits-for-child             cores=[0.78, 0.71, 0.93, 0.81, 0.78]   host idle=[0.0 x5]
one-process-four-threads           cores=[0.78, 0.73, 0.69, 0.76, 0.77]   host idle=[0.0 x5]
four-wide-children-under-a-tick    cores=[0.72, 0.71, 0.68, 0.64, 0.71]
  self only (no reaped_us)         cores=[0.0, 0.01, 0.01, 0.0, 0.01]
idle-sleep                         cores=[0.0 x6]
```

Two more proxies, both measured: per-pid self time misses every process shorter than a tick (0.00-0.01 against 0.64-0.72 with `cutime`), and on a saturated host a four-thread process gets 0.69-0.78 cores, so a low rate alone would call it serial. Hence `reaped_us` and the host-idle gate.

**Close measured** (`python3 -m pytest -q -p no:xdist tests/unit/test_a_serial_stretch_is_measured_not_averaged.py`):

```text
11 passed in 0.85s
collect2+ld, 1.0 core: observed_process_concurrency 2.0, serial_wall_s 100.0, serial_share 1.0
ld.lld --threads=4, 4.0 cores: observed_process_concurrency 1.0, serial_wall_s 0.0
autoreconf loop (work_process_count 4, none in it), 1.0 core: serial_wall_s 40.0, share 0.4, owners[0] autoreconf2.69 40.0 s
0.7 cores beside 0.1 idle: serial_unknown "the host had under one idle core for 100% of its sampled time"
make + four reaped cc1 in one tick: 4.0 cores; invocation log only: rows for root 5100
no samples: serial_unknown "no CPU samples for this element" -> serial-share-unknown
```

Same capture, after: `grep -c "nothing to gain"` -> 0, and the gcc group reads "2.6-3.4 cores busy on average, but their serial share is unknown (the native report has no sampled serial time), so this does not call them compute-bound". The >=400 s `autoreconf2.69` reading waits on a recapture; no `bst` on this host, so no end-to-end capture ran here.

**Mutation table** (`mutate.py`: copy, mutate with an asserted landing, run the guard file, restore from the copy)

| mutation | reddened | count |
|---|---|---|
| M1 a window's rate is its live-process count (the reviewed proxy) | parent-waits, four-thread, autoreconf, correlate, page | 5 failed |
| M2 a window's rate capped at one core | four-thread, reaped-children, autoreconf, correlate, page | 5 failed |
| M3 owners only from `WORK_BINARIES` | autoreconf, correlate, page | 3 failed |
| M4 correlate reads an unknown stretch as share 0 | unknown[unsampled], unknown[predates] | 2 failed |
| M5 a low window on a saturated host counted serial | contended | 1 failed |
| M6 `reaped_us` dropped from the level | reaped-children | 1 failed |
| M7 the invocation log not followed | invocation-log | 1 failed |

Reverted: 11 passed. M1 and M2 each redden the other counterexample's neighbours because both run through the same window test; each guard also has a mutation that reddens it alone or with its own consumers.

**Beyond the brief** (for the orchestrator's deviation line): the brief named the sampled rate; measurement added two corrections it did not name - children reaped between ticks (`cutime`) and a host-idle gate for contention - and the sampler now follows the invocation log, so the capture workflow samples without a workflow edit. `make test-touching`: 18 failed, 6608 passed; 14 of the 18 fail identically at `50120b532`, the other 4 (doc key names, schema dashes) were this change's and are fixed.
