# UX-609: the invariants docstring lists five of six gates

**Priority:** Low | **Status:** 🟢 Done Open | **Depends on:** UX-602 (which fixed the same defect one layer out) | **Serves:** the reader opening the module to find what it enforces | **Topic:** guards

## Motivation

`UX-602` found Part 33.1 naming four of the six published hard gates
and gave the spec a derived table. The same omission is one layer in:

```text
bga/validation/invariants.py   module docstring lists 5 of 6
missing                        run_identity_consistent
```

`UX-602`'s guard reads the spec against the registry and passes,
because the docstring is neither.

## Required Fix

The docstring's list is derived from the registry, or it stops being a
list — a docstring that enumerates a set nothing checks is the shape
`UX-602` just removed from the spec.

## Out of Scope

- `§32.7.5` and Part 33.1 — done in `UX-602`.

## Acceptance Test

A seventh gate registered — red naming the docstring.

## Outcome

**Premise re-measured at `d4a3d04`, and it holds.** The registry — the
`hard_gates` dict literal, `bga/validation/invariants.py:191` — and the
module docstring, side by side:

```text
ordering_violations_zero      named ("ordering_violations == 0")
critical_path_coverage_full   named
dominator_coverage_full       named
blame_chain_coverage_full     named
occupancy_within_capacity     named in prose ("I6 - occupancy within
                              every capacity the run declared")
run_identity_consistent       ABSENT - no "run_identity", "manifest",
                              "identity" or "I8" in the docstring
```

Six registered, five named, `run_identity_consistent` the missing one:
as filed. Motivation unchanged. The one refinement: occupancy was named
as prose, not as its key, so no key-substring check would have found
five — the count is of gates named, not of keys present.

**Close.** Branch taken: derived, not deleted. The docstring's list is
now the six keys verbatim, in the dict's own order, held to a live run's
published `hard_gates` by a new guard. It cost no lines — the header plus
two key lines replace the three prose lines exactly, so the docstring is
18 lines before and after (cap 25, and this module is not in
`_budgeted_modules()`; it did not grow regardless).

`tests/unit/test_the_gate_docstring_is_the_registry.py` — 5 clauses,
0.38s single-process. Population is `analyze_run(macro_micro/run)` plus
the stored `with_timeline/analyze.json`, per `UX-602`'s shape; no gate
list is restated in the test.

### Mutation table

| # | mutation | reddens | printed |
|---|---|---|---|
| A | **Acceptance Test**: `'seventh_gate_registered': True` in the dict | names-every-published-gate ("a hard gate is published and … the module docstring does not name it"), plus publishes-at-all and order | 3 failed, 2 passed |
| B | drop `run_identity_consistent` from the docstring (the filed defect) | names-every-published-gate, order | 2 failed, 3 passed |
| C | add `retired_gate_full` to the docstring | names-no-unpublished-gate, order | 2 failed, 3 passed |
| D | reorder the docstring's list | order only | 1 failed, 4 passed |
| E | delete the indented block, keep the header | block-parses, names-every, order | 3 failed, 2 passed |
| F | leak `and I6` into the block | block-parses, names-no-unpublished, order | 3 failed, 2 passed |

Each applied, reverted, and the anchor grepped back before the next.

### A clause that did not fully discriminate

Under F the shape check first flagged only `['I6']`: `^[a-z][a-z0-9_]*
[a-z0-9]$` accepts a lowercase prose word, so `and` reached the list and
was caught one clause later, by names-no-unpublished-gate. The check now
requires the snake_case underscore every published key has, and F prints
`['and', 'I6']`. Recorded because the clause was narrower than its
message claimed, not because a mutation failed to redden — all six did.

### Deviation from the Required Fix

None. The Required Fix offered derived or not-a-list; derived was taken,
because "stops being a list" cannot satisfy the Acceptance Test — a
seventh gate reddens nothing in a docstring that names no gates.
`§32.7.5` and Part 33.1 untouched, per Out of Scope.

Committed with `BGA_SKIP_SELECTOR=1`, said here as the hook requires.
`make test-touching` is red on one guard this track did not touch and
cannot fix: `test_every_direction_names_its_reader.py` finds Directions
8 and 9 still marked `partial` with every filing closed — measured red
at `d4a3d04` with this track's diff stashed. The fix is a marker in
`docs/design/directions.md`, a batch-level index, after round 84's six
closes. Everything else in the selector is green: 475 passed, 3 skipped.
