# UX-129: the millisecond does not reconcile the figures it claims to

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-112 (done — this audits its headline number)

## Motivation

UX-112's factorial rightly refuted the +31-44% interaction it was
filed on (round 13 independently confirmed with an **interleaved**
order-controlled run: spine ≈ +1.7s on `examples/08`'s 2003 processes,
no interaction — the original figure was a cold-machine first-run
artifact). But the replacement claim overshoots the data. The storm is
a fixed 2003-process fixture, so every published figure converts to an
absolute and a per-process price:

| source | base | traced | absolute | per process |
|---|---|---|---|---|
| UX-108 | 7.32s | 8.31s | +0.99s | 0.49 ms |
| UX-118 | 4.95s | ~5.84s | +0.65 to +0.89s | 0.32-0.44 ms |
| UX-112 | 4.11s | 6.40s | +2.29s | 1.14 ms |
| round-13 interleaved | 10.9s | 12.6s | +1.7s | 0.85 ms |

UX-112 ships *"the absolute cost barely moved — +1.5 to +2.3 seconds"*
(two of three prior figures are outside that range) and *"roughly a
millisecond per process … reconciles every figure this repository has
published"* (the set spans 0.32-1.14 ms — a 3.6× range). The honest
claim is weaker: **order half a millisecond to a millisecond,
machine-state-dependent** — and it matters because the number is
published in four places (`guides/real-project.md`, `guides/cli.md`,
`design/architecture.md`, the workflow's input help) and drives a
"budget roughly two minutes" fdsdk estimate that the **only real-scale
observation contradicts by ~5×** (the spine capture ran ~+11 minutes
over its predecessor), unremarked in any of them. Three smaller
verification gaps: `matrix.json` is cited as carrying the raw figures
and does not exist in the tree; cell order is unstated on a machine the
file itself says drifted; and the discarded warm-up makes it n=4
against an acceptance asking five. Also `README.md`'s Plane 2 section —
the one doc site UX-112's item 1 names explicitly — still quotes the
superseded +2.7%/+13.5% ratios.

## Required Fix

1. Re-state the price as a measured **range with its spread named**
   (per-process, absolute on the storm, and the fdsdk observation
   beside the extrapolation with the discrepancy owned), in the task
   file and all five doc sites.
2. Publish the raw per-run figures (check in the matrix data or paste
   it; a cited file must exist), state run order, and either run the
   fifth non-warm-up repeat or record n=4 as a deviation.
3. If the fdsdk gap survives a second real-scale spine capture, that
   is a finding about the model (per-process cost is not constant at
   scale) and gets filed on its own evidence.

## Out of Scope

- Re-opening the interaction question (refuted twice, independently).
- The `auto` policy (unaffected: it minimizes the cost whatever its
  exact size).

## Acceptance Test

Every doc site quotes the same range with provenance; the raw figures
exist where the verification log says; `grep -rn '2.7%' README.md`
finds no superseded spine ratio; and the fdsdk budget sentence carries
the measured +11-minute observation next to the extrapolation.

## Fix Implemented

### A fifth measurement, paired

The prior figures disagree by 3.6× partly because none of them was
measured in a way that cancels machine drift — `UX-112`'s own file
records the baseline halving between cells. So the first thing this task
did was measure again, **interleaved and paired**: `off` then `on` inside
each repeat, five non-warm-up repeats, one warm-up discarded,
`--trace-opens` on in both cells (the configuration the workflow runs),
`examples/08-process-storm`, 2003 processes in every run.

| repeat | spine off | spine on | paired delta |
| ---: | ---: | ---: | ---: |
| 1 | 5.72s | 6.42s | +0.70s |
| 2 | 7.12s | 7.91s | +0.79s |
| 3 | 7.27s | 8.12s | +0.85s |
| 4 | 6.98s | 7.76s | +0.78s |
| 5 | 6.99s | 7.80s | +0.81s |
| **median** | **6.99s** | **7.80s** | **+0.79s** |

The paired deltas span 0.15s while the `off` cell alone spans 1.55s —
which is the whole argument for pairing, and the reason the earlier
figures scatter. Per process: **0.39 ms median, 0.35–0.42 ms**. Raw
figures and run order: [`docs/audits/data/spine-cost-storm.md`](../../audits/data/spine-cost-storm.md).

### The reconciliation, restated

| source | base | traced | absolute | per process |
|---|---|---|---|---|
| UX-108 | 7.32s | 8.31s | +0.99s | 0.49 ms |
| UX-118 | 4.95s | ~5.84s | +0.65 to +0.89s | 0.32–0.44 ms |
| UX-112 | 4.11s | 6.40s | +2.29s | 1.14 ms |
| round-13 interleaved | 10.9s | 12.6s | +1.7s | 0.85 ms |
| **this task, paired ×5** | **6.99s** | **7.80s** | **+0.79s** | **0.35–0.42 ms** |

The honest claim is a range: **0.3 to 1.1 ms per process**, with the
spread named as machine state rather than hidden. It now reads that way
in all five doc sites (`README.md`, `guides/real-project.md`,
`guides/cli.md`, `design/architecture.md`, the workflow's `trace_spine`
input help), and `README.md`'s superseded +2.7%/+13.5% ratios — the one
site `UX-112` item 1 named explicitly and did not update — are gone.

`matrix.json` did not exist; the raw figures now live in a file that
does, and `UX-112`'s verification log says so.

### The fdsdk gap: the finding is that the data cannot see it

This is a **correction to round 13's own finding**, and it goes the other
way. The audit reports the spine capture running *"~+11 minutes over its
predecessor"*, contradicting the two-minute extrapolation by ~5×. That
compares the spine run against exactly one hook-only run — the fastest
one. Every published fdsdk capture of the same commit and configuration:

| ref | spine | wall |
|---|---|---:|
| `…-32064333551` | off | 3614.2s |
| `…-32113933158` | off | 3434.4s |
| `…-32122941503` | off | 3405.8s |
| `…-32177690506` | off | 2712.4s |
| `…-32223468993` | **on** | **3261.2s** |

The four hook-only runs span **901.8s — 15.0 minutes** — on identical
inputs. The spine capture sits *inside* that range: 9.1 minutes slower
than the fastest hook-only run, and **2.6 minutes faster than their
median**. Against a predicted cost of 45s–2.5 minutes, a 15-minute
baseline spread cannot resolve it in either direction.

So clause 3's condition ("if the fdsdk gap survives") is not met, and
filing a "per-process cost is not constant at scale" finding on this
evidence would be the same overreach this task exists to correct. What
ships instead is the honest statement, in the workflow help where the
budget is quoted: the extrapolation is an extrapolation, and this job's
own noise floor is larger than the thing it would measure. Establishing
the cost at 127k-process scale needs paired captures on one runner, which
is a scheduled-capture change and is not smuggled in here.

### Deviations, recorded

- **Clause 3 not actioned, deliberately** — see above; the trigger
  condition fails on the data.
- **The two `+2.7%`/`+13.5%` ratios stay in `design/architecture.md`**,
  labelled as the figures that made the opt-in decision, because that
  decision is history and the rule was stated before the numbers. They
  are marked superseded for pricing purposes rather than deleted.
- **n=5 achieved**, so `UX-112`'s n=4 shortfall is not carried forward —
  though it is now moot, since this task re-measured rather than reusing
  that matrix.

## Verification Log

Done 2026-08-19. Ten real builds for the paired matrix plus one
discarded warm-up; five real published capture refs read for the fdsdk
table. Acceptance, item by item:

```text
$ grep -c "2.7%" README.md
0
$ grep -rn "millisecond per process" README.md docs/guides docs/design
(no matches - every site now quotes the range)
$ ls docs/audits/data/spine-cost-storm.md
docs/audits/data/spine-cost-storm.md
```

The workflow's `trace_spine` help carries the 15-minute spread and the
spine capture's position inside it, next to the extrapolated budget.

Incidental, noted rather than filed: `--trace-spine` takes an optional
value, so `bga capture run --trace-spine PROJECT OUT -- …` consumes
`PROJECT` as the flag's argument. It fails loudly (`invalid choice:
'p08'`) rather than silently, and the `=on`/`=auto` form every document
uses is unaffected — but it cost one measurement round here.
