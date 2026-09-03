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

## Outcome

**The census, re-run at `5b4c05f`** — the Motivation's list is wrong in
both directions, because `UX-564` and `UX-566` landed after it:

```text
spec Part headings: 45   test files scanned: 439
unnamed by any test file (13): [0, 2, 6, 17, 20, 22, 25, 26, 28, 29, 34, 40, 44]
```

The Motivation named 23, 27, 37, 38, 39 as unnamed; all five are now
named (`test_the_declared_signals_are_the_published_ones.py`,
`test_the_spec_says_which_parts_are_advisory.py`). It missed 0 and 44,
and the range is Part 0..44, not "1.2 through 43". Part 34 left the
list with `UX-567`. Part 28's premise stands: implemented, published to
`analyze/v5`, named by nothing.

**The two derivations, measured** — both figures in the Motivation are
low:

```text
$ 32.4's block vs dataclasses.fields(AnalysisResult)
9 declared, 21 fields, 12 undeclared (not 4): structural run_id
run_instance memory_envelope plane2_absence total_duration_us
pipeline_overhead timestamp_agreement element_kind_summary
capacity_verdict plane2_capacity capacity_recommendation

$ 32.1's block vs load_run_context
6 declared, 21 top-level keys read (not 24), 15 undeclared
declared-but-never-read: none, in either direction
```

**The close, measured.**

```text
$ python3 -m pytest tests/unit/test_every_part_has_a_guard.py \
    tests/unit/test_fetch_build_overlap.py -q
31 passed in 0.78s

$ make test-touching   17 file(s) selected · 411 passed, 3 skipped in 10.44s
$ make test-small      3783 passed, 36 skipped in 25.91s
$ make test-medium     2289 passed, 53 skipped in 175.69s
```

The index is not vacuous: it asserts 45 headings, 441 scanned files and
33 Parts named by at least one, and it excludes itself from the
population — an index is not its own evidence. Before that exclusion its
own docstring example made it the sole namer of Part 12.

**Mutations.**

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | strip all four `Part 28` mentions from `test_fetch_build_overlap.py` | `test_every_heading_has_a_guard_or_a_row`, naming Part 28 | 1 failed, 20 passed |
| 2 | add `# Part 45 — A Heading Nobody Guards` to the spec | the same, naming Part 45 | 1 failed, 20 passed |
| 3 | name `Part 22` in `test_phase_and_occupancy.py` | `test_an_allowlisted_part_that_gained_a_guard_leaves_the_list` | 1 failed, 20 passed |
| 4 | `cpu_accounting=data.get(...)` → `None` in the loader | `test_every_declared_field_is_one_the_loader_reads` | 1 failed, 20 passed |
| 5 | add an undeclared field to `AnalysisResult` | `test_every_field_32_4_omits_is_a_declared_addition` | 1 failed, 20 passed |
| 6 | `fetch_only_prefix = 0` in `compute_fetch_build_overlap` | 4 of Part 28's guards, prefix and partition | 4 failed, 6 passed |
| 7 | one-kind runs return a zeroed `FetchBuildOverlap` instead of `None` | both trace-only cases | 2 failed, 8 passed |

A first attempt at 7 (`if False:` on the guard clause) was **rejected**:
it failed with `ValueError: min() arg is an empty sequence`, which names
the crash and not the claim.

**Guards that did not discriminate:** the first form of mutation 1 —
editing only the module docstring — left three other `Part 28` mentions
and the index stayed green. Correctly: the claim is that *some* file
names it.

**Deviation from the Required Fix.** The allowlist is two lists, not
one. `PROSE_ONLY` (0, 2, 40, 44) is what the Required Fix asks for;
`UNGUARDED` (20, 22, 29) is for implemented Parts that assert nothing,
because calling them prose-only would be false. It is capped at its
current three so it can shrink and not grow. Parts 6, 17, 25 and 26
were held by existing guards under other names and now name their Part
in one docstring line each, rather than getting a duplicate file. Both
key allowlists live in the test file, not in Part 32.
