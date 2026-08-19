# UX-112: the spine's price is quoted for a configuration the workflow never runs

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-108 (the per-mode measurement)

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
