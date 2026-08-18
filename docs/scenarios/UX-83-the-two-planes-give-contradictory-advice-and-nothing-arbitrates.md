# UX-83: the two planes give contradictory advice on the same run, and nothing arbitrates

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-51, UX-45 (both done); UX-09/UX-14 (context)

## Motivation

Measured this round on the macro-fixed variant of `examples/06`
(4-core host, `--builders 4 --max-jobs 4`), from one dual-plane capture:

- `bga analyze` headline: *"Biggest Opportunity: 31.9% of wall-clock
  time is RESOURCE WAIT — try `--capacity N` with a higher N, or
  `bga sweep` to find the real knee point"*;
- `bga sweep --resource PROCESS`: *"Knee point (PROCESS): capacity 5"* —
  a fifth concurrent builder on a host whose four cores are already
  runnable at 16 potential compiler processes, hedged only by a footnote;
- `bga correlate`, same capture: `core.bst` *"runs at only 0.90 cores
  busy … its native build asked for -j1: remove `notparallel`"* — the
  actual fix, which costs zero extra capacity and was verified this
  round at **25.05s → 16.92s (−32.4%)**.

A Plane-1-only reader is steered toward oversubscription; the correlate
reader is steered correctly. Both texts come from the same tool reading
the same build. The capacity axis being unmodeled (UX-09/UX-15) is a
known, documented gap — what is new here is that when the missing
information **is present in the same capture**, the Plane 1
recommendations do not consult it.

## Required Fix

When a Plane 2 report is available for the run (the capture already
produces both artifacts from one invocation), `analyze`'s RESOURCE WAIT
hint and `sweep`'s knee-point line should be conditioned on it:

1. If Plane 2 shows the run's concurrent elements already saturating the
   host's cores (sum of measured cores-busy ≈ host cores during the
   contended window), the hint must say more builders will contend for
   CPU, not recommend them.
2. If Plane 2 shows an element pinned below its requested jobs
   (`pinned_to_one_job`), the hint should name that first — intra-element
   parallelism is free capacity that `--builders` is not.
3. Without Plane 2 data, today's hint + caveat stand unchanged.

Mechanically this is a second consumer of the correlate join, not new
analysis: `analyze --plane2 report.json` (or auto-discovery next to the
run directory) is the missing plumbing.

## Out of Scope

- Modeling CPU contention inside replay/sweep curves (UX-14's standing
  caveat; larger).
- Any change when only Plane 1 exists.

## Acceptance Test

On this round's macro-fixed capture: `bga analyze <run> --plane2
<plane2.json>` must not recommend raising capacity while `correlate` on
the same pair reports a pinned element; the hint must name `core.bst`'s
pinning instead. `bga sweep` with the same input must annotate the knee
line with the measured CPU saturation. Text without `--plane2` is
byte-identical to today's.
