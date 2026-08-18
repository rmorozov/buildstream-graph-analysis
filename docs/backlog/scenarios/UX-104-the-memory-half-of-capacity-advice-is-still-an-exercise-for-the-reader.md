# UX-104: the memory half of capacity advice is still an exercise for the reader

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-63 (measured per-task memory), UX-21 (the memory guard's threshold), UX-83 (the Plane 2 plumbing into analyze)

Direction 3, item 5 — see
[`design/directions.md`](../../design/directions.md).

## Motivation

The report's standing memory line is: *"its largest single process
peaked at 1902 MB resident - multiply by however many elements build
concurrently before raising `builders`"*. That multiplication is the
tool's job, and it has every input: per-element peak RSS (UX-63), the
host's memory (run context), the concurrency the run actually reached
(Plane 1), and — since UX-83 — a channel for Plane 2 data into
`analyze`'s capacity advice. Leaving it to the reader has a failure
mode in each direction: raise `builders` into swap (the worst build
slowdown there is, and one no CPU-side signal predicts), or leave
memory headroom unused out of caution.

## Required Fix

1. **The computed envelope**, in the capacity block whenever Plane 2
   memory data is present: from the run's measured per-element peaks,
   the memory cost of the observed concurrency and of each higher
   `builders` value — conservatively (concurrent peaks summed as if
   coincident, and say so), against host memory minus a reserve.
   Rendered as the one sentence the reader currently has to derive:
   *"4 builders of this shape peak at ~7.6 GB of 15.6 GB; 8 would not
   fit"*. This makes the UX-83 arbitration memory-aware too: "more
   builders" advice must clear both the CPU and the memory check.
2. **The trend/compare hook:** compare notes when the candidate's
   memory envelope grew materially (new or changed elements raising
   peak RSS), the same additive-JSON pattern as the marginal gate —
   a note, not a gate, until a noise band for RSS exists.
3. Sweep's knee annotation (UX-83) gains the memory ceiling: a knee
   above the memory-feasible capacity says which constraint binds.

## Out of Scope

- Swap detection at capture time (a different, host-level measurement).
- A hard gate on memory (no noise model yet; same discipline as
  everywhere else).
- Modeling memory *inside* an element's own `-j` (Plane 2 measures the
  element's whole tree; per-job attribution is not needed for the
  builders question).

## Acceptance Test

On the retained fdsdk dual capture: the capacity block prints the
envelope computed from the real 1902 MB peak and the run's real
concurrency, and the number matches the hand calculation the README
currently performs in prose. On `examples/06` (small peaks): the
envelope says memory does not bind before CPU does. Synthetic test: a
run whose measured peaks make `builders+1` exceed host memory gets
capacity advice that refuses the raise on memory grounds even where
CPU has headroom.
