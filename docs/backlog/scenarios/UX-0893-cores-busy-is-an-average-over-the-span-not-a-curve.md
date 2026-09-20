# UX-893: cores busy is an average over the span, not a curve

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-675 | **Found by:** round 131, [`docs/design/in-step-parallelism.md`](../../design/in-step-parallelism.md) §6 item 3 | **Serves:** R5 (the capacity operator distinguishing a box half-idle throughout from one saturated for half the span), R2 second | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

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

## Outcome
