# UX-893: cores busy is an average over the span, not a curve

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-675 | **Found by:** round 131, [`docs/design/in-step-parallelism.md`](../../design/in-step-parallelism.md) §6 item 3 | **Serves:** R5 (the capacity operator distinguishing a box half-idle throughout from one saturated for half the span), R2 second | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

Per-element CPU is read once, at exit. `hook.c` takes one `getrusage`
per process (`tools/native_trace/hook.c:523-528`) and the spine one
`/proc/<pid>/stat` in `write_end`
(`tools/native_trace/spine.c:461`). Everything downstream is therefore
a total divided by a span:

```text
$ sed -n '1018,1023p' bga/correlate.py
    measured_cpu_us = sum(
        (entry.get("cpu_us") or 0) for entry in per_element.values()
    )
    cores_busy = (
        (measured_cpu_us / 1e6) / wall_span if wall_span and measured_cpu_us else None
    )

$ grep -n 'HOST_SAMPLE_INTERVAL_S = ' tools/bst_native_build_tracer.py
686:HOST_SAMPLE_INTERVAL_S = 2.0
```

`cores_busy` is 1.60 on `tests/fixtures/macro_micro` (69786259 µs over
43.508 s). A build that pinned four cores for seventeen seconds and
idled for twenty-six reports the same 1.60. The only series in the
capture is `/proc/stat`, which is whole-machine and cannot be
attributed to an element.

## Required Fix

Sample `/proc/<pid>/stat` `utime+stime` over the traced pid set on the
host sampler's existing 2.0 s tick. The spine already opens and parses
that file (`read_cpu_times`, `tools/native_trace/spine.c:269-280`);
this calls it periodically rather than once, for the pids it is already
tracking.

The sampler is `tools/native_trace/spine.c` (`read_cpu_times`, already
written) plus the host sampler's tick in
`tools/bst_native_build_tracer.py`; the series is declared in
`bga/schemas.py` beside `cpu_time.per_element`.

Publish a bounded per-element CPU-rate series in the report, not the
raw samples in the log — the difference between "wide for half the
span" and "half-wide throughout" is one curve per element, not one row
per tick.

Cost to state in the Outcome as a measurement, not an adjective: one
`/proc` read per tracked pid per 2 s, and the series' bytes against the
report's existing size ratchet.

## Decomposition

surfaces: `tools/native_trace/spine.c` (call `read_cpu_times` on a tick, not only in `write_end`), `tools/bst_native_build_tracer.py` (the host sampler's tick and the per-element reduction), `bga/schemas.py` (the series beside `cpu_time.per_element`)
guards: `test_the_cpu_series_separates_shape_from_total.py` (new); the report's existing size ratchet must stay green
gap: a process that starts and exits inside one 2 s tick contributes to the total and not to the curve — a known undersampling to state, not to hide
track: independent of UX-891, UX-892 and UX-894; validated against UX-891's floor
gate: not yet scheduled

Input classes: a pid alive across several ticks → a rate series; a pid
shorter than one tick → total only, absent from the curve; a `/proc`
read that fails mid-build → the series ends, it does not read zero; a
pid that exits between ticks → the exit-time read closes it; an element
with no traced pid → absent, as `cpu_time.per_element` already is.

## Out of Scope

Attributing `/proc/stat` busy-cores to elements — it is whole-machine,
and per-element CPU comes from per-element reads or is absent
(section 7 of `in-step-parallelism.md`). Changing the tick interval.
Changing
`cpu_time.total_cpu_us` or anything `UX-891`'s floor reads: the total
stays the exit-time sum, and the curve is published beside it.

## Acceptance Test

`tests/unit/test_the_cpu_series_separates_shape_from_total.py`: two
synthetic elements with identical `cpu_us` and identical spans, one
front-loaded and one flat, get different published series and the same
`cores_busy`. Sampling is absent, not zero, for a pid whose `/proc`
file could not be read — the rule `hook.c:523-528` already states for
an unmeasured CPU time.

**Mutations** (`falsify`):

1. Return the same cumulative jiffies on every tick. The series flattens;
   the total does not move. Catches a rate published as a level.
2. Drop every sample but the last. The series is absent; `cores_busy`
   is unchanged. Catches a curve reconstructed from the total.
3. Make one pid's `/proc` read fail. That element's series is absent
   and the others are unchanged. Catches an unreadable pid billed as
   idle.

## Outcome (round 132, 2026-09-20) — 🟢 Done

**Premise:** held. Per-element CPU is read once, at exit, so everything
downstream is a total divided by a span.

### The gap, measured

```text
$ sed -n '1018,1023p' bga/correlate.py
    measured_cpu_us = sum(
        (entry.get("cpu_us") or 0) for entry in per_element.values()
    )
    cores_busy = (
        (measured_cpu_us / 1e6) / wall_span if wall_span and measured_cpu_us else None
    )
```

`cores_busy` is 1.60 on `tests/fixtures/macro_micro` (69,786,259 us
over 43.508 s). A build that pinned four cores for seventeen seconds
and idled for twenty-six reports the same 1.60.

### After

```text
two elements, 8 core-seconds each over the same four ticks:
  front.bst  [4.0, 4.0, 0.0, 0.0]
  flat.bst   [2.0, 2.0, 2.0, 2.0]
  same total, same cores_busy, two curves
```

`cpu_time.per_element_series` is the rate between consecutive samples,
published beside the totals and never instead of them —
`total_cpu_us` and every per-element total stay the exit-time sum that
`UX-891`'s floor reads. A pid shorter than one tick has no second
sample and is in the total and absent from the curve, stated rather
than hidden. A `/proc` read that failed ends a series rather than
reading zero, the rule `hook.c:523-528` already states.

Cost, measured rather than described: one `/proc/<pid>/stat` read per
live traced pid per 2.0 s tick (210 us on this host), and the curve is
capped at 200 points per element.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| D1 | a rate published as a level | `test_two_elements_with_one_total_have_two_curves` (1) |
| D2 | a lone sample given a rate from an assumed zero | `test_a_pid_shorter_than_one_tick_is_absent_from_the_curve` (1) |
| D3 | an element's pids collapsed into one series | `test_one_element_with_two_pids_sums_them_at_the_same_instant` (1) |
| D4 | the ticks after a failed read billed as idle | `test_a_read_that_failed_ends_the_series_and_does_not_read_zero` (1) |
| D5 | the curve unbounded | `test_the_curve_is_bounded` (1) |
| D6 | an unreadable pid billed as zero | `test_a_pid_with_no_proc_entry_is_none_and_not_zero` (1) |

**A mutation that did not discriminate, first time.** D2 first gave a
lone sample a rate from `(0.0, 0)` and stayed green: that fixture's
only sample was stamped `t=0.0`, so the window was zero and the
existing `window <= 0` guard caught it — a second defence, not the
clause's own. The sample is stamped `t=2.0` now, which is where a
process that lived inside one tick is really sampled, and D2 reddens.

### Deviation from the Required Fix

The sampler is the tracer's own thread, not `spine.c`'s
`read_cpu_times` on a tick. The spine's loop blocks in
`waitpid(-1, __WALL)` and has no timer, so a tick there fires on tracee
events — none of which arrive during exactly the long compile the curve
exists for — and giving it one means a non-restarting signal handler in
the file whose whole promise is never to change the build. The new
sampler reads the same two `/proc/<pid>/stat` fields on the host
sampler's existing 2.0 s tick, over the pid set it follows from the raw
log both planes append to, so it covers hook-traced and spine-traced
processes alike. The samples land in scratch, not in the snapshot: `bga snapshot`
points `--raw-log` into a directory whose file list is a contract, and
the curve is a reduction the report carries — so no new flag, no new
store name and no new snapshot file.

```text
make test: 8955 passed, 174 skipped, 1 warning in 329.80s (0:05:29)
make lint: All checks passed! / clean: 567 finding(s) match tests/quality_baseline.json
```
