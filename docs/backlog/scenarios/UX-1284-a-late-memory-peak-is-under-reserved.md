# UX-1284: a link step that peaks above every compile before it is reserved at the compile's size

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1134 | **Found by:** Ruslan's promotion question on round 166 (2026-10-02): what stands between `auto` and arbitrary configurations | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** owner:CodSpeed Graviton

**Guard:** none — open, no guard named yet

## Motivation

UX-1134's gate learns an element's per-job size from its finished
jobs and holds while a live job is bigger than every finished one.
A link or LTO step at the end of an element can peak at several
times its compiles (lto1, a large static link), and it starts after
the gate has already settled on the compile's size with the pool
widened to fit it. No example has that shape: `16-memory-bound-giant`
is cc1-bound all the way, 2.8 GB per job. Inferred, not measured.

## Decomposition

Input classes: an element whose final link peaks at k x its compile
(k = 2, 4); an `-flto` element under `lto1` with jobserver width.
Journey: a new `examples/17-*` shape, a `graviton_arms.sh` leg, the
UX-1014 table.

## Required Fix

An example whose last step peaks above its compiles, its Graviton
reading under `off` and `auto`, and, if `auto` loses there, a gate
that keeps the reserve for the step it has not seen yet.

## Out of Scope

Choosing the linker; `-flto` partitioning policy.

## Acceptance Test

The new leg's `off` and `auto` walls and peak memory, run id pasted,
with `auto` completing.

## Outcome
