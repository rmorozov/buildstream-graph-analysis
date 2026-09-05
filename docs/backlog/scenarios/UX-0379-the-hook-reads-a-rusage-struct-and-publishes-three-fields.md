# UX-379: the hook reads a rusage struct and publishes three of its fields

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-45 (real CPU time), UX-63 (peak RSS from the same struct) | **Serves:** anyone whose build is I/O-bound or contended rather than compute-bound | **Topic:** capture | **Area:** tools

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

## Outcome

Round 61. Six fields out of the struct, and the whole way through:
`hook.c` writes them, the parser turns them into record fields, the
pairing pass carries them, `Plane2Fold` sums them per element,
`plane2/v2` publishes `resource_pressure`, the terminal renders it
beside `peak_memory`, and four of them annotate a Plane 2 slice.

**Measured, on this host, before writing anything** — a standalone
`getrusage` probe over the same command twice:

```text
                       inblock   oublock   majflt   minflt   nvcsw   nivcsw
gcc -O2 (compute)        74,368        48       15    1,934      81        0
cat 64MB (warm cache)         0         0        0      171       4        0
cat 64MB (cold cache)   135,264         0        5      165      60        0
sh -c true                    0         0        0       66       1        0
```

`inblock` is 0 warm and 135,264 cold for the **same command reading the
same file**. Nothing else bga has can tell those two apart. 135,264 x
512 = 69,255,168 B against a 67,108,864 B file plus the reader's own
binary and libraries, which is where `_IO_BLOCK_BYTES` comes from and
why it is 512 rather than a page.

`nivcsw` was 0 in every row of that table, on an idle host, so it was
measured again under load before being claimed as a contention signal —
the same total work spread over more processes than there are cores:

```text
 processes   nvcsw   nivcsw    wall
         1       1        3    3.8s
         4       5      580    4.0s
        16      15   16,454   15.4s
```

**And then through the real tool.** One generated project, captured
twice with only `-j` changed:

```text
make -jN      procs    preempted   vol. waits   majflt
-j1             603           36       31,227      208
-j16            603       12,706       31,805      221
```

603 processes both times, voluntary waits and faults flat — and
preemption up **353x**. That is the axis, measured rather than inferred
from low CPU concurrency, and it is the number a reader needs to tell
"this element was contended" from "this element was busy".

**Self only, and summed.** Two decisions worth recording because they
point opposite ways from their neighbours. `cutime`/`cstime` are
published because a `make` wrapper does no work itself; these counts are
not, because every child is traced and reports its own, so a parent's
`RUSAGE_CHILDREN` copy would count each block twice. And unlike
`peak_memory`, which must never be summed, these are events: two
processes that each read 100 MB did read 200 MB between them.

**Zero is a measurement here**, which is the opposite of the rule
everywhere else in this file. A read served from the page cache never
reaches the block layer, so `read_bytes: 0` states a fact; the
unmeasured case is a process whose destructor never ran, counted
separately as `unmeasured` and reported as `available: false` when it is
every process.

### Falsification run

Nine mutations against the committed tree. All nine caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | pairing drops the fields again | 2 clauses of `TestPairingCarriesThem` |
| M2 | blocks published as blocks, not bytes | `test_blocks_become_bytes`, `test_the_values_survive_the_pairing` |
| M3 | the fold maximises instead of summing | `test_they_are_summed_and_not_maximised` |
| M4 | no measurement reports zeros rather than unavailable | `test_no_measurement_is_unavailable_and_not_zero` |
| M5 | `hook.c` stops writing `nivcsw` | `test_every_field_is_emitted` |
| M6 | the line buffer goes back to 160 | `test_the_line_buffer_fits_what_it_now_writes` |
| M7 | a record with no counters gets zeros on its slice | `test_a_record_without_them_gets_no_key` |
| M8 | the dictionary loses a row | `test_the_dictionary_documents_each_one` |
| M9 | an older capture's line is zero-filled rather than left absent | `test_an_older_hooks_line_still_parses` |

**M1 is the finding, and it was live rather than injected.** The first
implementation parsed all six onto the event correctly and the report
still said `available: false` on a capture whose raw log carried them:
`stream_records` rebuilds a paired record from a *named list of keys*,
and the new ones were not in it. Every other clause was green at that
moment — the parser clauses, the fold clauses, the annotation clauses —
because each tested its own stage against data it constructed itself.
The gap was the seam between two stages that both worked.

The list now lives once, as `_PRESSURE_FIELDS`, read by the pairing
pass and by the fold, because it had already been written out twice and
the second copy was the one that was wrong.

**M6 is not cosmetic.** `format_rusage` returns 0 when the line does not
fit and the caller then writes *no* rusage at all — so a buffer sized
for six fields and handed twelve silently removes `UX-45`'s CPU time and
`UX-63`'s peak RSS from every record. The clause holds the buffer, not
the fields.

**Published, and reaching the terminal but not the page.** The block
renders beside `peak_memory` and `cpu_time`, and like both of them it is
not in `analyze/v4`'s `ANALYZE_PLANE2_KEYS`, so it does not reach `bga
view`. That gap is older and wider than this item — it is the same shape
`UX-370` closed for `binary_cost` — and is filed as `UX-383` rather than
widened into here.

### Verification Log

```text
$ python3 -m pytest tests/unit/test_the_struct_it_already_read.py -q
17 passed in 0.22s

$ cd <generated project> && bga snapshot -- bst build all.bst
$ python3 -c "json.load(open('.../plane2.json'))['resource_pressure']"
{
  "available": true,
  "per_element": {"mod0.bst": {
      "read_bytes": 0, "written_bytes": 1710592,
      "major_faults": 299, "minor_faults": 31612,
      "voluntary_switches": 8213, "involuntary_switches": 212,
      "measured": 51, "unmeasured": 6, "coverage": 0.894...}},
  "measured": 51, "unmeasured": 6, "note": "..."
}

$ zcat .../plane2.log.gz | grep -m1 '^END.*cc1'
END pid=9 ppid=5 ts=434.339731780 element=mod0.bst inv=1916
  utime=0.019648 stime=0.027508 cutime=0.000000 cstime=0.000000
  maxrss_kb=15696 cmaxrss_kb=0 inblock=0 oublock=0 majflt=61
  minflt=1319 nvcsw=191 nivcsw=5 cmd=.../cc1 -quiet ...
```

Tiered small on landing at 0.22s, which is the default tier and needs no
`tiers.py` entry.
