# UX-129: the millisecond does not reconcile the figures it claims to

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-112 (done — this audits its headline number)

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
