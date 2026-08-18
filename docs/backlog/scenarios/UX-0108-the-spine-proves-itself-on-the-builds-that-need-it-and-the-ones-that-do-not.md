# UX-108: the spine proves itself on the builds that need it, and the ones that don't

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-106, UX-107

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
