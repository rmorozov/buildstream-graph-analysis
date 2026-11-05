# UX-1380: the doctor's compiler clause in `cli.md` names the order `UX-1374` replaced

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 39 (2026-11-05) | **Serves:** R4 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`docs/guides/cli.md:643` says "`c-compiler` resolves `cc` then `gcc`
exactly as `compile_hook` does". Since `UX-1374` the order is `$CC`, then
the first of `cc`, `gcc`, `clang` (`cli.md:144`, `real-project.md:271`),
and since `UX-1373` doctor answers `ok` with no compiler while a wheel's
prebuilt hook and spine match their stamp (`tools/bga_doctor.py:164-172`).

## Required Fix

The clause states the order `native_prebuilt.compiler()` uses and the
prebuilt case, and a guard reads that function's candidate tuple against
the sentence.

## Out of Scope

Doctor's behaviour, which is right.

## Acceptance Test

The guard reddens when the sentence or the candidate tuple changes alone.

## Outcome
