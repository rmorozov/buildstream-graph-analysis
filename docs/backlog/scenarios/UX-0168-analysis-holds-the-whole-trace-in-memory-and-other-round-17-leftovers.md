# UX-168: analysis holds the whole trace in memory, and other round-17 leftovers

**Priority:** Medium | **Status:** 🟡 In Progress — the census, the store and all six one-liners are done; the trace parse streams, but the memory headline it was filed for is **not** met and the reason is measured below (`UX-169`) | **Depends on:** UX-157/UX-148/UX-160 (the landings these trail)

## Motivation

The round-17 review's remaining-sharp-edges list, filed so the
big-project axis keeps a worklist. The headline is capacity:
`load_and_summarize` slurps the entire `trace.log` into one string and
then a full event list (`tools/bst_native_build_tracer.py:3498-3500`).
A multi-hour build with hundreds of thousands of processes means
hundreds of MB to GB of RSS at analysis time — on the machine that
just finished the build, in the phase right after it. The census has
the same shape one size down: `census_project` computes a per-element
dependency closure (`:2259`) that is quadratic-ish on thousands of
elements, serial, announced by one line.

The small ones, each a sentence:

1. `run_teed`'s read loop waits for the pipe's write end to close,
   which every sandbox descendant holds — a sandboxed process that
   daemonizes past bwrap's exit hangs the shim under `--diagnose`
   (`bwrap_shim.py:527-543`). Unlikely under `--die-with-parent`;
   worth a read timeout or a documented limit.
2. `format_sandbox_stderr`'s elided branch indexes
   `row['stderr_path']` without `.get` (`tracer.py:4560`).
3. `SELF_TEST_ARGV = SELF_TEST_ARGV = "…"` double assignment
   (`bwrap_shim.py:570`).
4. The interrupt notice prints between the Plane 2 summary and the
   Plane 1 report ("analyzed above" when half is below).
5. The census summary reads "0 with static binaries (spine traced)" —
   the parenthetical describes the zero elements, which is at best a
   riddle; say "spine not needed" when the count is 0.
6. `--list` and `_warn_if_large` stat-walk the whole store every
   snapshot invocation — seconds on a many-GB store, per run; cache
   or sample.

## Required Fix

Stream the trace parse (line-iterate, aggregate incrementally — the
format is line-oriented and the summarizer's aggregations are all
associative); memoize the census closure. Then the six one-liners.

## Out of Scope

- Trace format changes (the bytes are fine; the reader is not).
- UX-108's overhead measurement (still its own item).

## Acceptance Test

Peak RSS of `bga analyze` on a synthetic 1M-line trace is bounded (a
test generates one and asserts RSS < ~4× the largest single-element
aggregate, or simply < a fixed budget where the old reader exceeds
it); census on 1,000 synthetic elements completes in seconds not
minutes (timed bound). Each one-liner: the riddle wording gone, the
KeyError branch `.get`s, the double assignment single, the notice
placed after both reports, a daemonizing-descendant test times out the
tee rather than hanging.

## What was built

### The census (done, and the bottleneck was not where the item said)

`census_project`'s closure is memoised and iterative rather than
recomputed-per-element and recursive. That alone was worth less than
expected: **2.04s → 1.82s** on a synthetic 1,000-element project (each
element depending on the previous five).

Profiling said where the time really was: **5.0s of 5.9s inside
PyYAML**, because the census parsed every `.bst` file *twice* — once in
`read_declared_build_deps` and once in `_local_source_paths`. One
shared memoised reader (`read_element_yaml`, keyed on path + mtime +
size, using `CSafeLoader` where the binding has it) took the same
project to **1.19s**, a 1.7x cut against the original.

The memo is written so a dependency cycle cannot corrupt it: it stores
only *completed* reachable sets, never a half-finished post-order one.
There is a test for the cycle case even though `bst` rejects cycles,
because "the memo is fast and wrong" is the failure mode that would not
announce itself.

Not exercised here: `CSafeLoader`. This machine's PyYAML 6.0.1 has no
`_yaml` extension and no network to build one, so the selection line is
covered by a unit test and *not* by the timing measurement above — the
1.19s is the pure-Python loader.

### The store (done)

`snapshot_size_bytes` memoises into `<snapshot>/.size`, keyed on a
`_tree_signature` — the directory count and newest directory mtime,
which costs one stat per *directory* instead of one per *file* and
still notices every file added, removed or renamed anywhere in the
tree. Measured on a synthetic 50k-file, 10-snapshot store:

| | first call | repeat |
|---|---|---|
| before | 0.89s cold / 0.19s warm | 0.19s |
| after | 0.24s | **0.025s** |

The memo excludes itself from the total, is dropped when the signature
moves, and a store it cannot write to simply pays the walk.

### The parse streams — and the memory headline does not land

`load_and_summarize` passes the file handle to `parse_trace_lines`; the
whole-file string is gone from the shipped path. In isolation that is
real: on a 56 MB / 400k-event trace the parse goes from **365 MB to
215 MB** allocated (`tracemalloc`), **395 MB to 243 MB** by RSS.

End to end it changes nothing, and this is the deviation worth
recording rather than burying. `bga analyze` on the same trace:

```text
streaming (shipped)   400000 processes; 17.9s; 635 MB RSS / 545 MB allocated
pre-UX-168 read()     400000 processes; 17.7s; 635 MB RSS / 545 MB allocated
```

A methodology note, because it cost a red test to learn: Linux does not
reset `ru_maxrss` across `exec`, so a measurement taken in a subprocess
of a large parent reports the *parent's* high-water mark. The guard
passed alone and failed in the full suite with both sides reading
298.52734375 MB exactly — pytest's own peak, inherited twice. Every
comparison here is `tracemalloc`, which a parent cannot contaminate.

Because the string is freed long before the peak. Where the peak
actually is, measured cumulatively in one process:

```text
baseline              19 MB
after parse          246 MB   (400k events)
after pair+merge     517 MB   (400k records)
after full report    917 MB   (400k entries in report["processes"])
```

So UX-168's acceptance bound — "peak RSS of `bga analyze` on a
synthetic 1M-line trace is bounded" — is **not met**, and streaming the
reader was never going to meet it. The cost is the per-process dict,
held three times over in three shapes. That is a representation change,
not a reader change, and it is filed as `UX-169` rather than claimed
here.

The test file states the same distinction: the RSS comparison is
labelled a *measurement* (it holds by construction — the slurping side
pays whatever the streaming side pays, plus the file), and the guard a
revert actually reddens is the one that makes `parse_trace_log` fatal
inside `load_and_summarize`.

### The six one-liners (all done)

1. `run_teed`'s read loop takes a 1s timeout and reaps the child once
   the pipe goes quiet, so a sandbox descendant that daemonizes past
   `bwrap`'s exit no longer wedges the shim. `_reap` keeps the wait
   status rather than discarding it, which the UX-140 exit contract
   needs. Falsified: with the timeout removed the guard sits for the
   orphan's full 30s and fails.
2. The elided branch `.get`s `stderr_path`, so a pre-UX-148 record
   renders instead of raising `KeyError` while formatting a *failure*
   report.
3. `SELF_TEST_ARGV` is assigned once.
4. The interrupt notice says "every figure that follows" — it prints
   before the analysis, not after it.
5. A census with no static binaries reads "none with static binaries
   (the spine is not needed)" instead of "0 with static binaries (spine
   traced)".
6. Covered by the store memo above, including an end-to-end guard that
   `_warn_if_large` goes through it.

17 guards in `tests/unit/test_trace_stream_and_census_scale.py`; every
mutation falsified red except the two noted above as measurements
rather than guards (the RSS comparison, and the 1,000-element timing
bound, which asserts "seconds not minutes" and would not redden on the
memo's removal).
