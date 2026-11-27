# UX-1380: the doctor's compiler clause in `cli.md` names the order `UX-1374` replaced

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 39 (2026-11-05) | **Serves:** R4 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_doctor_clause_names_the_compiler_order.py`

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

**Gap measured.** `docs/guides/cli.md` (line 664, not 643) said
"`c-compiler` resolves `cc` then `gcc`"; `tools/native_trace/prebuilt.py:53`
`compiler()` reads `$CC` (one that does not resolve is an error, no
fallback), then `CANDIDATES = ("cc", "gcc", "clang")`; `check_compiler`
in `tools/bga_doctor.py` answers `ok` first while `find("hook.so")` and
`find("spine")` both hold.

**Close measured.** The clause reads "resolves `$CC`, then the first of
`cc`, `gcc`, `clang` on `PATH`, exactly as `compile_hook` does", plus a
sentence for the prebuilt case. The guard imports `CANDIDATES` and reads
the clause: `3 passed`.

| mutation | reddened | run |
|---|---|---|
| clause order `cc`, `clang`, `gcc` (sentence alone) | `test_the_clause_names_the_candidates_in_the_functions_order` | 1 failed, 2 passed |
| `CANDIDATES = ("cc", "clang", "gcc")` (tuple alone) | same | 1 failed, 2 passed |

The same-length tuple mutation left a stale `.pyc`, so the revert read
red; clearing `__pycache__` returned 3 passed.

**Deviation.** `make test-touching` is blocked in a worktree (`UX-1041`);
ran the touching list's doctor/guide/register files instead, 1931 passed,
4 failed: `test_the_skills_point_at_the_guides.py` on the absent
`tests/ci_reference.json`, not touched here.
