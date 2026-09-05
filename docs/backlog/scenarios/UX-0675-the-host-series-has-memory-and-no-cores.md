# UX-675: the host series has memory and no cores

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-378 (host-samples.jsonl), UX-437 (the host tracks on the trace) | **Serves:** R4, asking whether the cores were busy | **Topic:** capture | **Shape:** judgement

## Motivation

The one series the capture keeps about the host is memory:

```text
tools/bst_native_build_tracer.py:678-690   _MEMINFO_KEYS, _VMSTAT_KEYS (pgmajfault, pswpin, pswpout) — no CPU field
tools/bga_timeline.py:502-503              CONCURRENCY_COUNTER = "traced processes running", unit "processes"
bga/viewer/questions.js:518-536            concurrency-curve: the reader is told to compare it "against the machine's core count" themselves
```

Processes running is not cores busy — a process blocked on I/O or a
lock holds a slot and no core — so the CI owner's question ("were
the cores the binding resource?") has no series to be answered from.
Plane 2's rusage gives CPU *totals* per process at exit
(`hook.c:353-397`), which cannot be placed in time.

## Required Fix

The host sampler reads `/proc/stat` beside `/proc/meminfo` on the
same tick: busy cores (delta of non-idle jiffies over the interval,
divided by the tick), load average, and the core count. Three more
counter tracks on the trace beside the five memory tracks (`UX-437`'s
shape), `bga:*` units declared, and the trace dictionary row. The
sample is what `UX-676` reads.

## Out of Scope

- Per-process CPU over time — rusage is at exit by design; the host
  series is the cheap instrument, and it is the one the question
  needs.

## Acceptance Test

A capture's `host-samples.jsonl` carries `cpu_busy_cores`, `load1`
and `cores` per tick; the trace has the three tracks; mutation: drop
the `/proc/stat` read — the sampler guard reds.

## Outcome

**The gap, measured.** The one series the capture kept about the host
was memory. `read_host_sample()` read `/proc/meminfo` and
`/proc/vmstat` and nothing else, so the CI owner's question had no
series behind it:

```text
$ python3 -c "from tools.bst_native_build_tracer import read_host_sample; print(sorted(read_host_sample()))"
['cached_kb', 'mem_available_kb', 'mem_free_kb', 'mem_total_kb',
 'pgmajfault', 'pswpin', 'pswpout', 'swap_free_kb', 'swap_total_kb']
```

**The close, measured.** Sampled at `interval_s=0.05` around a
three-million-iteration integer loop on a four-core host:

```text
t         cpu_busy_cores  cores  load1
3082.186  1.770           4      0.08
3082.278  1.087           4      0.08
3082.329  1.961           4      0.08
3082.380  0.392           4      0.08
3082.431  0.000           4      0.08
```

The curve rises while the loop runs and falls to 0 after it, which is
the discrimination `traced processes running` cannot make.

**The mutation table.** Five, each reddening a named clause.

| mutation | clause that reds |
|---|---|
| drop `read_cpu_sample()` from the sampler | `test_a_sample_names_the_three_it_reads`, `..._lands_exactly_where_a_tick_can_resolve_it` |
| publish `cpu_busy_cores` whatever the gap | `..._lands_exactly_where_a_tick_can_resolve_it` |
| count `guest`/`guest_nice` as busy | `test_idle_and_iowait_and_guest_are_not_busy` |
| count `iowait` as busy | same |
| drop `MILLI` from the `cpu_busy_cores` row | `test_the_fractional_cpu_series_survives_an_int64_counter` |

**Three deviations.**

*`bga:*` units are not declarable here.* The Required Fix asks for
them; `bga:*` quantities (`bga/schemas.py`) govern payload fields, and
the trace's counter units are free `unit_name` strings with no
vocabulary to join. This item adds no payload field, so the
declaration it can make is the trace-dictionary row. `UX-676` puts the
series into a payload and declares the quantity there.

*`milli` units instead of a double counter.* `counter_value` is an
`int64` (`track_event.proto`, field 30) and two of the three values are
fractional. The correct fix is `double_counter_value`, and it is
declined: `tests/fixtures/perfetto_field_numbers.json` pins field
numbers against a file it records the sha256 of, and none of `main`,
`v49.0` or `v48.1` hashes to the recorded
`c99a6aaa72fec1afa7b1450e7d9461ee5a9ba02f46176eeffa1869a18d6a94ff`, so
a new key could not be added with the provenance the fixture exists
for. Scaling by 1000 is `HOST_COUNTERS`' own `KB` move and loses
nothing at the 0.005-core quantisation of a two-second sample.

*One clause the field selection could not have.* `guest` and `iowait`
are both 0 on this host, so a sampled reading cannot tell the right
sum from three wrong ones. `_busy_jiffies()` exists as a seam and the
clause constructs the kernel's line instead.

**One thing tried and reverted, measured.** The `concurrency-curve`
sentence that told the reader to supply the core count themselves —
the line this item's Motivation cites — now points at `host cores
busy`. A canned question to go with it does not: adding one takes the
library 17 → 18 and reds 16 clauses across five files, and the last of
them (`test_every_library_query_is_reachable_from_a_finding`) cannot
pass until a finding names CPU utilization, which is `UX-676`'s. Filed
as `UX-717` with the count and the blocked clause recorded, rather
than carried here.
