# UX-112: the spine's price is quoted for a configuration the workflow never runs

**Priority:** High | **Status:** 🟢 Done — and the interaction it was filed for is not there | **Depends on:** UX-108 (the per-mode measurement)

## Motivation

UX-108 measured the spine's overhead per **mode** — spine on vs off,
ten builds each on `examples/06`, pooled to **+2.7%** — and the default
(opt-in) followed from it. Round 12 re-measured on the same 4-core
host and confirmed that number for the spine *alone*… and found the
combination is a different animal (fresh cold-cache builds, in-log
`Build` activity time):

| capture flags | Build activity |
|---|---|
| `--trace-spine` only | 41s |
| `--trace-opens` only | 41s, 45s (two runs) |
| `--trace-spine --trace-opens` | **59s (+31-44%)** |

Each mechanism alone is within noise of the other; together they cost
a third of the build. And the combination is not exotic — it is the
**exact configuration the capture workflow runs** (`trace_opens=true`
in every fdsdk capture-context), so the one real-scale spine capture
ever taken (run 32223468993, ~63 min against the predecessor's ~52)
ran precisely the pairing whose price was never measured. It passed
the band verdict only because the band is ±643s wide.

A plausible mechanism (to be confirmed, not assumed): both features
tax process exit — the hook's destructor flushes the open-record
buffers while the spine holds the same process at its ptrace
exit-stop, and the two serialize; neither alone stalls the other. But
the mechanism is secondary; the defect is that the measurement matrix
had three cells and the deployed configuration was the fourth.

## Required Fix

1. **Measure the full matrix** — {spine} × {opens} × the two fixture
   classes UX-108 used (fork-dense `examples/06`, configure-heavy
   `examples/08`), five repeats per cell, pooled — and publish it where
   UX-108's number lives (the task file, `docs/guides/cli.md`'s flag
   docs, and the README's Plane 2 section). The docs currently imply
   +2.7% is *the* spine price; they must quote the combination price
   next to it.
2. If the interaction cost is confirmed material, diagnose the
   mechanism (perf/strace one build) and either fix the contention
   (e.g. flush open records before the exit path the spine stops on)
   or document the pairing as expensive with the workflow guidance
   that follows (spine captures without opens for routine trend runs;
   the combination reserved for deliberate deep captures).
3. The capture workflow's `trace_spine` input help text states the
   measured combination cost, since `trace_opens` is its default.

## Out of Scope

- Changing the opt-in default (UX-108's decision stands unless the
  matrix says otherwise for the spine-alone cell).
- Per-element spine targeting (UX-113 — a different lever on the same
  cost).

## Acceptance Test

The matrix table with all four cells, five runs each, is in this
file's verification log with the raw numbers; the three doc sites
quote the combination cost; and if a code fix was taken, the
combination cell is re-measured to within the budget's distance of
the dearer single mechanism.

---

## Fix Implemented

### The matrix, five repeats a cell, warm-up discarded

> **The 822s below are stale, and were already stale when written
> (`UX-132`).** `UX-123` landed one commit earlier and collapsed exec
> chains, making `examples/06` **813** processes; this file quoted the
> pre-collapse figure fresh, which is exactly the failure `UX-132` was
> filed for — the annotate-what-you-invalidate convention existed only
> where one author remembered it. The timings and the conclusions drawn
> from them are unaffected: 822 vs 813 is a 1.1% change in a divisor
> whose own spread is larger.

| fixture | opens | spine | wall | vs base |
|---|---|---|---|---|
| `examples/06` (822 processes / 30s) | off | off | 30.36s (sd 1.08) | — |
| | off | **on** | 29.35s (sd 1.59) | **-3.3%** |
| | **on** | off | 29.08s (sd 1.10) | -4.2% |
| | **on** | **on** | 29.76s (sd 0.59) | -2.0% |
| `examples/08` (2003 processes / 4s) | off | off | 4.11s (sd 0.63) | — |
| | off | **on** | 6.40s (sd 0.31) | **+55.7%** |
| | **on** | off | 4.31s (sd 0.64) | +4.9% |
| | **on** | **on** | 5.81s (sd 0.81) | **+41.3%** |

### The interaction is not there

This task was filed on a measured +31-44% for the combination "while
each alone is free". Re-measured as a full factorial, that does not
reproduce:

| fixture | spine costs, opens off | spine costs, opens on | interaction |
|---|---|---|---|
| `examples/06` | **-1.00s** | +0.68s | +1.68s (< the spread) |
| `examples/08` | **+2.29s** | **+1.50s** | **-0.79s** |

On the process-dense fixture the spine is **cheaper** alongside opens,
not dearer — opens raises the baseline, so the same absolute cost is a
smaller share. On the compile-bound one every cell overlaps every other
(ranges 27.6-32.3s throughout). Whatever produced the original figure,
a factorial at n=5 does not.

### What is real: about a millisecond per process

The ratio is not a property of the spine. It is a property of the
fixture's baseline, which is why the same cell has been quoted three
times at three magnitudes:

| round | `examples/08`, spine vs hook-only |
|---|---|
| `UX-108` | +13.5% (7.32s base) |
| `UX-118` | +13.2% median (4.95s base) |
| here | +55.7% (4.11s base) |

The absolute cost barely moved — **+1.5 to +2.3 seconds** — while the
baseline halved as the machine warmed. Per process:

| fixture | processes | mean process lifetime | spine cost |
|---|---|---|---|
| `examples/06` | 822 over 30s | ~36ms | ~0 (below the spread) |
| `examples/08` | 2003 over 4s | ~2ms | **+0.75 to +1.14 ms** |

**So the price is roughly a millisecond per process**, which is
invisible when a process lives 36ms and dominant when it lives 2ms.
That single number reconciles every figure this repository has published
for the spine, and it is what the docs now quote — a ratio would be a
fact about the fixture rather than about the tool.

### What follows

`UX-113`'s `--trace-spine=auto` is the answer this measurement points
at: pay the millisecond per process only for the elements the census
says the hook cannot see. On `examples/06` that is no elements at all.

Item 2's diagnosis is therefore not needed — there is no contention to
fix, because there is no interaction. Item 3's help text states the
per-process cost rather than a combination price that does not exist.

## Verification Log

Done 2026-08-19. Forty real builds, cold cache each, first run of every
cell discarded as machine warm-up; `matrix.json` carries the raw
figures.

> **Two corrections from `UX-129` (2026-08-19).**
>
> 1. **`matrix.json` was never checked in.** A cited file that does not
>    exist is a citation to nothing. The raw figures now live in
>    [`docs/audits/data/spine-cost-storm.md`](../../audits/data/spine-cost-storm.md),
>    in a form the repository can keep.
> 2. **The headline overshot its own inputs.** *"Roughly a millisecond
>    per process … reconciles every figure this repository has
>    published"* does not survive the set it claims to reconcile, which
>    spans 0.32–1.14 ms; and *"the absolute cost barely moved — +1.5 to
>    +2.3 seconds"* excludes two of the three prior figures. The claim is
>    now stated as the measured range with its spread named. The
>    *refutation* this task was filed for — no spine × opens interaction —
>    stands, independently reconfirmed twice.
