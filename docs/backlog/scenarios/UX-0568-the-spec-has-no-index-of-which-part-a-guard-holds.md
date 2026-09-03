# UX-568: the spec has no index of which Part a guard holds

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-567 (the invariant half of the same index) | **Serves:** the next specification review — this one took five agents | **Topic:** guards

## Motivation

A census of `Part N` mentions across `tests/unit/*.py` names Parts
1.2 through 43 and none of: 2, 6, 17, 20, 22, 23, 25-29, 34, 37-40.
Some of those are prose (2, 34, 40), some are the unimplemented pair
(`UX-564`), some are implemented and simply unnamed — Part 28's
`fetch_build_overlap` reaches analyze/v5 and no file names it. Part
32 is the one Part with a mechanical guard, and it holds; the other
forty depend on a reviewer reading them.

## Required Fix

A Part→guard index as a guard: every `# Part N` heading in the spec
either has a test file naming it or sits on an explicit prose-only
allowlist with a reason; unnamed implemented Parts (28 first) get
their file. And two derivations the contracts guard leaves unheld:
32.4's key list against `AnalysisResult`'s fields (`models.py:548-579`
has `structural`, `run_instance`, `memory_envelope`,
`pipeline_overhead` the spec omits) and 32.1's field list against
`loader.py:42-68` (6 listed, 24 read).

## Out of Scope

- Asserting each Part's *content* — that is what the named guard
  does; the index asserts that one exists.

## Acceptance Test

Mutation: remove Part 28's naming test — red; add a Part heading
with no test and no allowlist entry — red.
