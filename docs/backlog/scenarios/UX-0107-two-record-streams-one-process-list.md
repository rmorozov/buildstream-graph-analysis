# UX-107: two record streams, one process list

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-106 (the spine records), UX-105 (the census) | **Topic:** capture | **Area:** tools

Direction 4, integration — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Once `UX-106` lands, a dynamically-linked process is recorded **twice**
— a spine record (argv, timestamps, exit, per-process CPU, peak RSS)
and a hook record (the same lifecycle plus opens and children-rusage) —
while a static process has only the spine record. Consumed naively that
double-counts every dynamic process's CPU and concurrency, which would
corrupt every Plane 2 analysis in the name of fixing coverage. And the
report's coverage language is still the pre-spine disclaimer: a global
footnote, not a number.

## Required Fix

1. **Join and dedupe in the trace parser**: match spine and hook
   records per process on (invocation id, pid, START timestamp within
   a small tolerance — same sandbox pidns, same monotonic clock, so
   the join is exact in practice). One process, one merged entry:
   spine fields as the base, hook fields (opens, cutime/cstime) as
   enrichment. A hook record with no spine partner (spine off, or
   pre-spine captures) passes through as today — **old captures parse
   unchanged**.
2. **Provenance per process**: each merged entry carries
   `coverage: spine+hook | spine-only | hook-only`. Every analysis
   keeps working over the union; opens-dependent findings (UX-46
   declared-vs-used) compute over hook-covered processes only and say
   what share that is.
3. **Coverage becomes measured**: the report's per-element
   "(N% of this element's processes were measured)" and the global
   NOTE are recomputed from the union — with the spine on, process
   coverage is 100% by construction and the line says what remains
   partial (opens). The `UX-105` census cross-checks it: a static
   binary in the census with no spine records and no hook records is
   a *finding* (the tracer missed something), not a footnote.
4. **CPU reconciliation**: spine `utime/stime` is per-process; the
   hook's END additionally carries `cutime/cstime` (children it
   reaped). The merged model uses per-process self time only for
   sums — the double-count risk this task exists to prevent — and
   keeps the reaped-children figures as consistency evidence (the
   UX-53 pattern: a quantity computed twice is a free test; disagree
   beyond tolerance → flag the capture).

## Out of Scope

- The tracer itself (`UX-106`).
- Real-scale validation and defaults (`UX-108`).
- Chrome-trace export changes beyond passing merged entries through.

## Acceptance Test

On a dual-stream capture of `examples/06` (all-dynamic): every process
is `spine+hook`, total CPU equals the hook-only capture's total within
tolerance (nothing double-counted), and UX-46 output is unchanged. On
`examples/01` (static busybox): processes appear as `spine-only`,
per-element coverage reads 100% process / 0% opens, and declared-vs-
used correctly reports itself unmeasurable for those elements rather
than reporting "no unused dependencies". A pre-spine capture (the
retained fdsdk `native-report.json`) re-parses byte-identically.

> **No longer true after `UX-123` (2026-08-19).** Byte-identical
> re-parsing was a property of *this* parser, and the exec-chain collapse
> deliberately changed what old captures render as — the fdsdk trace head
> went from 1833 processes to 1812. The acceptance clause was correct when
> run and is now a record of a parser that no longer exists; the standing
> requirement it expressed (an old capture must still parse, and must not
> silently change meaning) is carried by `UX-123`'s own verification.

---

## Fix Implemented

`merge_record_streams` / `compute_stream_coverage` /
`compute_element_opens_coverage` in `tools/bst_native_build_tracer.py`,
between `pair_events` and `summarize`, so every consumer of a Plane 2
report — text, JSON, Chrome trace, the correlation — sees one process
list and never chooses which stream to trust.

### The double-count, closed

`examples/06`, one build, both mechanisms live:

| | records | processes | CPU total |
|---|---|---|---|
| dual-stream, naive | 1644 | **1644** | **112.61s** |
| dual-stream, merged | 1644 | 822 | 58.47s |
| hook-only, run 1 | 822 | 822 | 61.30s |
| hook-only, run 2 | 822 | 822 | 57.85s |

> **Superseded by `UX-123` (2026-08-19).** These 822s are this parser's
> counts, and `UX-123`'s exec-chain collapse changed them: an `execve`
> chain is one process, not one per image, so `examples/06` now reports
> **813**. The figures above stay because the *claim* they support — the
> merge halves the process count and the CPU total, and lands inside the
> range two hook-only builds produce — is what was measured and is
> unaffected. Only the absolute counts moved. (`UX-132`: a fix that
> changes a number an earlier task file quotes annotates that file in the
> same commit.)

Every process joined on `(invocation, pid)` with a START inside
`MERGE_START_TOLERANCE_S`, all 822 `spine+hook`, and the merged CPU
total lands inside the range two hook-only builds of the same project
produce. The naive figure is not a rounding error: it is every
dynamically-linked process counted twice.

### The crossing the process count could not reveal

Pairing a START with an END keyed on `(invocation, pid)` is correct with
one mechanism writing. With two it pops **the spine's START for the
hook's END**, and vice versa — while the process count, the coverage
classes, the durations and the element attribution all stay right, so
nothing downstream flinches.

What gave it away was a resolution that cannot exist:

```text
END pid=9 … utime=0.013204 stime=0.017606 … cmd=…/cc1plus     ← the hook
END pid=9 … utime=0.010000 stime=0.010000 … src=spine cmd=…   ← the spine
```

`/proc/<pid>/stat` reports whole `USER_HZ` ticks. A record tagged
`src=spine` carrying `utime=0.013204` is carrying somebody else's
measurement. `pair_events` now keys on the mechanism as well, and the
test that pins it asserts each record keeps *its own* numbers rather
than asserting the counts, which were never wrong.

### Which CPU figure the merged model uses — measured, not assumed

The task says spine fields as the base, hook fields as enrichment. That
is right for the lifecycle and wrong for CPU, and only the measurement
says so. `/proc` truncates to 10ms ticks; `getrusage` resolves
microseconds:

| population (`examples/06`) | spine | hook |
|---|---|---|
| 34 processes over 200ms | 45.25s | 45.59s (**0.7% apart**) |
| 531 processes under 20ms | 0.83s | 3.82s (**4.6× apart**) |

A build made of short-lived processes is exactly where the difference
matters: on `examples/07` the spine's total is **-53.8%** against the
hook's, and 145 of 189 processes there used less than one tick, so the
spine reports them as zero. The merged entry therefore takes the hook's
`cpu_us` wherever it exists, keeps both as `spine_cpu_us` /
`hook_cpu_us`, and records which one it used in `cpu_source`. The
lifecycle stays the spine's — its span brackets the hook's on all 822
real pairs, because it starts at the kernel's exec-stop and ends at the
exit-stop.

Where no hook figure exists — every static process — the spine's
truncated one is all there is, and the report says so rather than
letting the number pass as exact:

```text
24 process(es) carry only the spine's tick-truncated CPU time - statically
linked, or gone before the hook's destructor could run - so their share of the
CPU total is a lower bound, and a short-lived one among them reads as zero.
```

### A per-process tolerance cannot see a systematic offset

663 pairs on `examples/06`, every one agreeing to within a clock tick,
and their totals 7.4% apart. `UX-53`'s "a quantity computed twice is a
free test" only pays if the test is run at both scales, so the
reconciliation reports the aggregate as well as the outliers — and
neither figure is replaced by their mean, because averaging two
measurements hides that they differed.

### Coverage, as a number

```text
Process coverage: 822 process(es) - 822 spine+hook
  CPU measured twice for 663 process(es) … every pair agrees to within a clock tick.

Process coverage: 24 process(es) - 24 spine-only
  24 were seen only by the ptrace spine - statically-linked, so fully measured
  except for opened paths, which need the in-process hook. Opens coverage: 0%.
```

and the `UX-105` footnote, which fired identically whatever the truth
was, now states what this capture measured:

```text
NOTE: 5 static executable(s) are staged (cat, env, sh, sleep (+1 more)) and the
ptrace spine recorded 24 process(es) the LD_PRELOAD hook could not have seen.
The blind spot the census bounds is measured here, not merely disclaimed.
```

A third case the census alone could not close: static binaries staged
and **none exec'd**. The census bounds the risk, the spine shows the run
did not hit it, and the report says that instead of warning.

### Declared-vs-used stops being silent where it matters most

`examples/01`'s elements have no opens at all, so `UX-46` skipped them
entirely — which reads as "nothing to report" in precisely the case
where the honest answer is "nobody could look". With the spine on, the
share is counted:

```text
Declared build dependencies never read: 0 candidate(s) across 0 element(s)
  work-a.bst   UNCOVERED - 0 of 3 process(es) run for this element were reachable
               by the LD_PRELOAD hook - every one was statically linked and seen
               only by the ptrace spine, so its read set is unmeasured rather
               than empty
  …
  Computed over the hook-covered processes: 0 of 24 (0%), and 0 of 8 element(s)
  had every process covered. The rest are listed UNCOVERED above rather than as
  having no unused dependencies.
```

Partial coverage is treated exactly as a dropped-path read set already
was — `uncovered`, naming the share — because a process the hook never
entered could have opened the very file about to be called unread.

**One thing the first implementation got wrong, caught by running it.**
Pulling *every* element with coverage data into the analysis reported
nine fully-traced `examples/06` elements as "may be built entirely by
statically-linked processes": that capture had no opens because it was
taken without `--trace-opens`, not because anything was static. A wrong
reason where there had been no claim at all is worse than the gap. Only
elements the hook provably never entered are added.

### `UX-46` unchanged where it was already working

`examples/07-declared-vs-used-dependencies` exists to test the detector
in both directions. Two cold builds, one flag apart:

```text
hook only:   1 candidate(s) across 1 element(s); 4 dependency edge(s) confirmed used
               unrelated.bst  never read: base.bst  (5 staged file(s))
hook+spine:  1 candidate(s) across 1 element(s); 4 dependency edge(s) confirmed used
               unrelated.bst  never read: base.bst  (5 staged file(s))
               Computed over the hook-covered processes: 234 of 234 (100%) …
```

Same verdict, same discrimination, one added sentence about scope. 234
processes both times — 468 records merged to 234.

### Old captures

The retained freedesktop-sdk capture, re-rendered by this build and by
the one before it:

| path | result |
|---|---|
| raw log → text report | **byte-identical**, 131 lines |
| saved `native-report.json` → text report | **byte-identical**, 298 lines |
| raw log → JSON | +`stream_coverage`, +`src`/`coverage` per process; **every pre-existing value equal** across 2339 processes |

The JSON gains two per-process keys and one top-level key, which is what
"provenance on every entry" means; nothing that was there before
changed, and nothing a reader sees does.

Tests: 27 new in `tests/unit/test_stream_merge.py`, one `bst`-gated and
running a real dual-stream build of `examples/01` to pin the acceptance
clause that matters — that declared-vs-used reports itself unmeasurable
rather than clean. CI's pinned `bst` tier moves 18 → 19. Suite:
1366 → 1392.

## Verification Log

Done 2026-08-19. Every table above is from a real capture: four builds
of `examples/06` (two per mode), two cold builds of `examples/07`, one
traced build of `examples/01`, and the freedesktop-sdk capture re-parsed
by both this build and its predecessor in a git worktree so "identical"
means diffed, not assumed.
