# UX-379: the hook reads a rusage struct and publishes three of its fields

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-45 (real CPU time), UX-63 (peak RSS from the same struct) | **Serves:** anyone whose build is I/O-bound or contended rather than compute-bound | **Topic:** capture

## Motivation

`hook.c`'s destructor already calls `getrusage` twice — once for
`RUSAGE_SELF`, once for `RUSAGE_CHILDREN` — and writes three fields out
of each:

```c
getrusage(RUSAGE_SELF, &self);
getrusage(RUSAGE_CHILDREN, &children);
...
timeval_seconds(&self.ru_utime), timeval_seconds(&self.ru_stime),
timeval_seconds(&children.ru_utime), timeval_seconds(&children.ru_stime),
(long)self.ru_maxrss, (long)children.ru_maxrss
```

`UX-63`'s own comment names the principle — "`ru_maxrss` from the same
struct already being read". The struct that is already populated, on a
call that has already been paid for, also carries:

| field | what it answers |
|---|---|
| `ru_inblock`, `ru_oublock` | how much this process read and wrote — the I/O dimension bga has none of |
| `ru_majflt` | major faults: the page-pressure signal `UX-378`'s swap advice is currently modelling instead of measuring |
| `ru_minflt` | soft faults, which separate a large working set from a thrashing one |
| `ru_nvcsw`, `ru_nivcsw` | voluntary against involuntary context switches — a process that *waited* against one that was *preempted*, which is CPU contention measured rather than inferred |

None of them is captured. `grep -n "inblock\|oublock\|majflt\|minflt"`
over `hook.c` and `spine.c` returns nothing.

This matters because of what bga currently cannot say. Its whole
vocabulary for a slow element is compute: CPU time, concurrency,
requested jobs against achieved. An element that is slow because it read
a gigabyte off a cold cache, and one that is slow because it was
preempted by fifteen siblings, both present as "low CPU concurrency" —
the same shape, and the report offers the same advice for each. The two
fields that tell them apart are in a struct the hook has already read.

## Required Fix

The END line gains the fields, on the same "zero or more known
`key=value` pairs before `cmd=`" rule `UX-45` established — so a trace
captured by an older hook still parses and reports them as unavailable
rather than as zero.

- `hook.c` writes `inblock`, `oublock`, `majflt`, `nvcsw`, `nivcsw`
  from the structs it already has.
- The parser reads them the way it reads the rusage keys today, and
  `Plane2Fold` folds them per element the way `_CpuTime` and
  `_PeakMemory` already do — a per-element aggregate, not a per-process
  row, so `UX-297`'s streaming shape is unchanged.
- `plane2/v2` publishes the aggregates with their units declared, and
  the trace dictionary gains a row per key, beside `cpu_us` and
  `max_rss_kb` which are the same kind of fact.

The spine cannot supply these — its `/proc` read at the exit-stop is a
different instrument — so a spine-only record carries no key, exactly as
it carries no `max_rss_kb` today.

## Falsification

Capture a project with one element that reads a large file and one that
computes, and assert the I/O-bound element's `inblock` aggregate is
orders of magnitude larger while its CPU time is not. Today neither
element has the field.

The other direction: a hook built before this change still parses, and
its report says the fields are unavailable rather than zero — the same
clause `UX-45` already holds for CPU time.

## Out of Scope

- Host-level I/O. This is per process, which is what the hook can see;
  the host's own counters are `UX-378`'s file.
- Anything that reads these numbers to produce a finding. Capturing them
  comes first, and a finding built on an uncaptured number is the thing
  this repository keeps refusing to write.
