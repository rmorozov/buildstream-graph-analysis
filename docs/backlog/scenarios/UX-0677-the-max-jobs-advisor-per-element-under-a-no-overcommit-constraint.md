# UX-677: the max-jobs advisor — per element, under a no-overcommit constraint

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-676 (the intervals), UX-230 (what-if pricing), UX-31 (pinned elements) | **Serves:** R4 and R2 — the operator who sets the numbers and the owner whose recipe carries them | **Topic:** analysis

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
the summed peak RSS under host memory, **priced by replay** (the
`whatif` scheduler with per-element job counts) so the advice says
what the build drops to. Stated as the fallback it is: the `UX-679`
jobserver removes the need for static numbers where it can run.

## Out of Scope

- Writing the numbers into the project — the advice is a table and
  the `bst` variable lines to paste; `bga` does not edit recipes.

## Acceptance Test

On example 06 the advisor recommends raising core.bst above `-j1` and
prices the drop; on a synthetic run with two `-j8` elements
overlapping on four cores it recommends the split that fits.
Mutation: drop the memory constraint — the advisor guard reds on a
run whose peaks exceed RAM.
