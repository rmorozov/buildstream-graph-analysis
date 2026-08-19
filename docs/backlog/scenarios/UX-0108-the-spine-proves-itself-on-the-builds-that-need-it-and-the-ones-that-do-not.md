# UX-108: the spine proves itself on the builds that need it, and the ones that don't

**Priority:** Medium | **Status:** 🟢 Done — the budget decided: `--trace-spine` stays opt-in | **Depends on:** UX-106, UX-107

Direction 4, validation — see
[`design/directions.md`](../../design/directions.md).

## Motivation

The spine's value case and its risk case live on different builds. The
value case is a static toolchain — `examples/01`/`02`'s busybox manual
elements, whose Plane 2 capture has been empty since they exist. The
risk case is a process-dense dynamic build — fdsdk's 127k processes,
where per-process event overhead compounds and where the existing
numbers are known and must not move. Neither fixture tests the other's
property, and the default (`--trace-spine` on or off) should be decided
by these measurements, not by optimism — the same discipline every
threshold in this repo already follows.

## Required Fix

1. **Value, on the static examples**: CI's `bst-examples` job captures
   `examples/01` with the spine on — the busybox `sh`/`sleep` processes
   appear with argv, CPU and wall time, and the element-level Plane 2
   report renders for elements that never had one. Ground truth: the
   spine's per-element wall spans must bracket Plane 1's task spans,
   and CPU-vs-wall for `sleep 3` must read ~0 CPU over ~3s wall (a
   known answer no other fixture provides).
2. **Risk, on fdsdk**: one capture-workflow dispatch with the spine on,
   compared against the retained spine-off captures: wall-clock within
   the measured noise band, process count ≥ the hook's 127k (spine
   sees strictly more), CPU totals within the UX-107 reconciliation
   tolerance, and the raw-trace size increase measured against the
   publish budget (UX-57's history says budgets get found out at fdsdk
   scale, so measure before shipping).
3. **The overhead number**: `examples/06` baseline and the
   configure-heavy fixture (UX-106's budget: <2% wall), five repeats,
   published in this file's verification log. **The default is decided
   by the numbers**: within budget → spine defaults on with the hook
   (coverage should not be opt-in); over budget → stays opt-in and the
   report's coverage line says how to turn it on.
4. Docs follow the outcome: the README's Plane 2 section and the
   real-project guide replace the static-binary disclaimer with the
   census + spine story, per whichever default shipped.

## Out of Scope

- Tuning the tracer beyond what the budget requires (a faster spine is
  its own future task if the numbers demand one).
- Remote-execution sandboxes (Direction 1's standing exclusion).

## Acceptance Test

Items 1-3 *are* the acceptance test; each produces a number or a
rendered report named above, pasted into the verification log. The
decision rule for item 3's default is stated before the measurement
and the shipped default matches it.

---

## Fix Implemented

### The value case: `examples/01` measures a known answer

Every command `examples/01-resource-contention` runs is `sleep 3`
through static busybox. Its Plane 2 capture has been empty for as long
as Plane 2 has existed. With `--trace-spine`, one build, both planes:

```text
Real CPU time (getrusage, 24 from /proc at the ptrace exit-stop): 0.00s across 24 of 24
  work-a.bst    0.00s CPU over   3.01s wall =  0.00 cores busy
  work-b.bst    0.00s CPU over   3.01s wall =  0.00 cores busy
  …
  work-h.bst    0.00s CPU over   3.01s wall =  0.00 cores busy

Peak Memory (largest single process per element):
  work-a.bst    1.5 MB
```

`sleep 3` is the one fixture in this repository whose answer is known
before the measurement: ~0 CPU over ~3s wall, and eight elements doing
identical work must measure identically. Both hold, eight times, to
2ms. The per-element CPU and peak-memory blocks render for elements
that have never had them.

`sleep` arrives as the shell's own command line rather than as a
separate `exec` — busybox runs it as a built-in applet — so what the
argv identifies is the applet, not a second process. The 3.011s and the
0 CPU are the shell's, and they are the sleep's.

Two `bst`-gated tests hold this: the known answer and the
self-consistency it implies. CI's `bst-examples` job now takes the same
capture on every push, with both planes, so the data exists to look at
when a future question needs it.

### A Plane 1 defect the ground truth exposed

The task asks the spine's per-element spans to **bracket** Plane 1's
task spans. They do not, in either direction, and the reason is Plane
1's:

| element | Plane 1 | Plane 2 |
|---|---|---|
| work-a … work-f | 3.004 – 3.005s | 3.010 – 3.012s |
| work-g | **2.687s** | 3.010s |
| work-h | **2.686s** | 3.010s |

Plane 1's spread across eight identical elements is **0.319s**; Plane
2's is **0.002s**. Two of the eight are reported 11% shorter than the
`sleep 3` they ran, which is not imprecise but impossible.
`work-g`'s BuildStream log file is named `…build.20260819-061746.log`
while the wrapper stamped its `START` at `06:17:47.199`: a wrapped line
is stamped when the wrapper *reads* it, and BuildStream flushes in
bursts.

Filed as `UX-110` rather than absorbed into a tolerance here. The test
asserts agreement within 1.0s and says why that is the honest assertion,
which is a deviation from this task's wording, recorded rather than
smoothed.

### The overhead, and the decision it was supposed to make

Ten runs per mode on `examples/06`, five on `examples/08-process-storm`,
a fresh cold cache for every one:

| fixture | processes | hook | spine | overhead |
|---|---|---|---|---|
| `examples/06` (compile-bound, 18 proc/s) | 822 | 45.90s (sd 0.59) | 47.15s (sd 1.36) | **+2.7%** |
| `examples/08` (process-dense, 575 proc/s) | 2003 | 7.32s (sd 0.24) | 8.31s (sd 0.26) | **+13.5%** |

> **Two later corrections (`UX-132`).** The 822 is this parser's count;
> `UX-123`'s exec-chain collapse made it **813** — the timings are
> unaffected, only the divisor. And the *ratios* here were superseded by
> `UX-112`, which measured the price as an absolute rather than a
> percentage of whichever fixture it was measured on; `UX-129` then
> narrowed that to a range. The +0.99s absolute this row carries is the
> figure that survived, and it is one of the four `UX-129` reconciles.

The decision rule was stated before the measurement: within the 2%
budget the spine defaults on with the hook, past it the flag stays
opt-in. **Both fixtures are past it, so `--trace-spine` stays opt-in**,
and the report's own footnote now names it and its price where a reader
is already looking at the gap:

```text
… This bounds what the trace can be missing; it does not measure what it did miss
(UX-105). Re-run with `bga capture run --trace-spine` to record them anyway: a
ptrace process-event tracer sees a process whatever its linkage, at a measured
+2.7% wall on a compile-bound build and +13.5% on a process-dense one, which is
why it is not the default.
```

Two things worth stating rather than rounding away:

- **`UX-106`'s 6.9% was an over-estimate.** That figure came from n=2
  and its own doc said so ("n=2 is weak evidence for the exact figure
  and ample for 'it is not under 2%'"). At n=10 it is 2.7%, and the
  weaker claim was the true one.
- **The cost is not a constant per process.** 1.5ms per process on
  `examples/06`'s four-way parallel compile against 0.5ms on the serial
  storm — a 3× difference in the quantity that would let anyone
  extrapolate to a real project. Neither fixture predicts fdsdk, which
  is why fdsdk was captured rather than modelled.

### The fixture the budget named and no project was

`examples/08-process-storm` exists because `UX-106`'s budget names a
configure-heavy fixture and instructs whoever implements it to build one
if none exists. None did: `examples/06` runs 822 processes across 45s
(18/s) and its wall clock is `cc1plus`, so a per-process cost hides
inside it. The storm runs 2003 in 3.5s (**575/s**) — `cat /dev/null` in
a shell loop, dynamically linked so the hook can see them too, because a
fixture whose processes only one mechanism can see would measure that
mechanism against nothing.

### The risk case: freedesktop-sdk, 127,632 processes

One dispatch of the capture workflow with `trace_spine: true`
([run 32223468993](https://github.com/rmorozov/buildstream-graph-analysis/actions/runs/32223468993),
published as `captures/fdsdk/953683fb-incremental-b4j4-32223468993`),
against the same commit, target, builders and max-jobs as the four
retained hook-only captures. The build exited 0 and the analysis
rendered unchanged.

| | hook-only ×3 | hook+spine |
|---|---|---|
| processes | 127,627 / 127,628 / 127,629 | **127,632** |
| with an observed exit | 119,492 / 119,493 / 119,494 | **120,228** |
| no observed exit | 8,135 | **7,404** |
| CPU total | 8,503.8s / 11,000.1s / 11,744.1s | **10,656.3s** |
| wall clock | 2712.4 / 3405.8 / 3434.4 / 3614.2s | **3261.2s** |
| raw trace | 693,995,599 B | **921,117,665 B** (+32.7%) |

**Nothing double-counted, at scale.** All 127,632 processes are
`spine+hook` — a single class, which is the whole claim `UX-107` makes,
holding at 155× the size of the fixture it was developed on. A naive
union would have reported ~255,000.

**The spine sees strictly more, and what it adds is exits rather than
processes.** Only +3 to +5 processes, because freedesktop-sdk's
toolchain is entirely dynamic — the census finds no static executable
and the spine confirms it saw none across all 127,632, which turns the
census's standing caveat about cache-supplied binaries into a
measurement. The real gain is **+734 processes that now have an observed
exit**: a process replaced by `exec` runs no destructor, so the hook
could never report its CPU or peak RSS, and the spine reads both at the
kernel's exit-stop.

> **Counted by a parser that no longer exists (`UX-123`, 2026-08-19).**
> The +734 and the 127,632 are pre-collapse figures: an `execve` chain
> was one record per image and is now one process, which moved the fdsdk
> trace head from 1833 to 1812. The *finding* is untouched and in fact
> sharpened — exec'd processes are exactly the ones the hook cannot see,
> and collapsing the chain is a better account of them, not a smaller
> one. Re-derive the counts from a fresh capture before quoting them as
> current (`UX-132`).

**Wall clock says nothing here, and that is itself the finding.** 3261.2s
sits inside the hook-only range, and so would almost anything: those
four captures of *the same commit and target* span 2712–3614s, a 33%
spread. The same is true of CPU total (8,504–11,744s across three
hook-only captures — a 38% spread, which is why the spine capture's
+25% against the *most recent* one is not evidence of anything). A band
that wide cannot resolve a 3–13% effect, which is precisely why
`examples/06` and `examples/08` exist and why the default was decided
there.

**The cross-check paid at scale.** CPU measured twice for 119,497
processes, **40 disagreeing** past the 50ms tolerance (0.03%), worst
10.94s on a `doxygen` shell. In aggregate the spine totals 2.9% below
the hook — the same tick-truncation signature that reads as -53.8% on
`examples/07`'s two-millisecond processes and 0.7% on `examples/06`'s
long ones, now measured across three orders of magnitude of process
lifetime.

**The publish budget held, and the raw trace did not.** 921 MB against
694 MB, +32.7% rather than the ~2× the small fixtures showed, because
fdsdk's records carry long command lines that the extra records do not
duplicate. Both are far past the workflow's 40 MB threshold, so both
publish a 4 MB head and a note — no change in behaviour, and the
published tarball grew 7.1 MB → 8.2 MB.

## Verification Log

Done 2026-08-19.

- **Item 1** — one traced build of `examples/01` with both planes; the
  `sleep 3` figures and the eight-element agreement are from it, and two
  `bst`-gated tests re-run the build rather than replaying a fixture.
- **Item 2** — capture run 32223468993, compared against four retained
  hook-only captures of the same commit fetched with `bga baseline -n 4`.
- **Item 3** — 30 real builds: ten per mode on `examples/06` (two
  batches of five, +2.8% and +2.7%, pooled to +2.7%) and five per mode
  on `examples/08`, each with a fresh cold cache.
- **Item 4** — docs updated to the default the numbers chose.

The one thing this task asked for and did not get is its own wording:
the spine's spans do not bracket Plane 1's, and `UX-110` is why.
