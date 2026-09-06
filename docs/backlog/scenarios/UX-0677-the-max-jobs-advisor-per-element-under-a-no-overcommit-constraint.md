# UX-677: the max-jobs advisor — per element, under a no-overcommit constraint

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-676 (the intervals), UX-230 (what-if pricing), UX-31 (pinned elements) | **Serves:** R4 and R2 — the operator who sets the numbers and the owner whose recipe carries them | **Topic:** analysis | **Shape:** bounded

## Motivation

BuildStream has no cross-element job server, so `builders ×
native max-jobs` is a static product: too small and cores idle, too
large and the elements that happen to overlap overcommit the machine.
The tool names the pinned elements (`UX-31`) and nothing else — an
element whose `max-jobs` is *high* and overlaps four others is the
same defect with the other sign, and the tool is silent.

## Required Fix

Per element: measured cores busy while it built (`UX-675` series
joined to its span) against its resolved `max-jobs` (`UX-377`) and
the builders it overlapped with — then a recommended `max-jobs` per
element that keeps the sum of overlapping jobs under the cores and
the summed peak RSS under host memory. Stated as the fallback it is:
the `UX-679` jobserver removes the need for static numbers where it
can run.

**Three decisions, taken here.** Round 102's track stopped rather
than invent them, correctly — this row was dispatched as a track
before its judgement was taken, which was the orchestrator's error
and not the track's.

**1. The evidence is the series against the span, not `UX-676`'s
interval rows.** `underutilized_intervals` and `overcommitted_intervals`
are capped at 40 rows and ranked; they are a *sample* of the windows,
so joining them per element would be an instrument reading a proxy
for the thing it names (fixing guide §5). Join `UX-675`'s host counter
samples to each element's BUILD span directly.

**2. An element with thin evidence gets a refusal, not a default.**
Where an element's BUILD span carries too few host samples to support
a number, the row for it says so and says why. The threshold is the
track's to measure and state — pick it from the fixture's real sample
spacing rather than a round number, and paste the distribution that
chose it. A recommendation that silently falls back to the run-level
figure is the shape this repository has been burned by.

**3. The constraint is checkable, and it extends an existing
document.** The inequality: at every instant, the sum over elements
building then of their recommended `max-jobs` is at most the host's
cores, and the sum of their measured peak RSS is at most host memory.
A guard verifies the *published recommendation* satisfies it on a real
fixture — not that the formula has the right shape. Publish it as
per-element keys on the document that already carries the capacity
recommendation rather than minting a new contract id.

**Out of this row, and filed as `UX-739`: pricing it by replay.**
The Required Fix said "priced by replay (the `whatif` scheduler with
per-element job counts)". `bga/whatif.py` has no such mode — it
projects elements becoming *instant* over this run's measured
durations, which is different arithmetic. A per-element-job-count
replay is a scheduling simulation that does not exist, and building
one inside this row is the unbounded surface the track flagged.

## Out of Scope

- Writing the numbers into the project — the advice is a table and
  the `bst` variable lines to paste; `bga` does not edit recipes.

## Acceptance Test

On example 06 the advisor recommends raising core.bst above `-j1` and
prices the drop; on a synthetic run with two `-j8` elements
overlapping on four cores it recommends the split that fits.
Mutation: drop the memory constraint — the advisor guard reds on a
run whose peaks exceed RAM.
