# UX-530: a real capture reaches the track ceiling, and the timeline is dropped whole

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-430 (the ceiling), UX-406 (the spine double-count that halves the room) | **Serves:** anyone capturing a C++ project with a few hundred processes per element | **Topic:** capture

## Motivation

```text
ex06 cold capture, Plane 2 records ×10 (offset pids): 8,130 processes on 11 elements
trace tracks       842 → 8,159          TRACE_TRACK_BUDGET 8,000  (bga_view.py:696)
export             timeline refused whole; recipe written           (bga_view.py:1033-1063)
```

About 740 processes per element is a real C++ shape, and the spine
(`UX-406`) counts every process twice, so the ceiling is met at half
that. `export()` refuses the whole timeline rather than trying the
degradations its own recipe names (`--planes 1`, a coarser grain).

## Required Fix

`export()` degrades before it refuses: `--planes 1`, then the
process grain the recipe names, then refusal — each step stated in
the page's handoff sentence. And the ceiling counts *processes*,
not slices, so the spine's second slice does not halve the room.

## Out of Scope

- Raising the ceiling — `UX-430` measured why it is where it is.

## Acceptance Test

The 8,130-process capture exports with a Plane-1 timeline and a
sentence saying why; mutation: remove the degradation step — the
export refuses again.
