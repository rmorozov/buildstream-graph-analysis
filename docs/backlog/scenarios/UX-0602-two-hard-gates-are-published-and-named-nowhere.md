# UX-602: two hard gates are published and named nowhere

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-567 (the I6 gate), UX-566 (the advisory map) | **Serves:** anyone reading `confidence.hard_gates` to decide whether a run is trustworthy | **Topic:** contracts

## Motivation

Architecture review 14 measured the gate list against the Part that
declares it:

```text
$ python3 -c "json.load(...with_timeline/analyze.json)['confidence']['hard_gates']"
['blame_chain_coverage_full', 'critical_path_coverage_full',
 'dominator_coverage_full', 'occupancy_within_capacity',
 'ordering_violations_zero', 'run_identity_consistent']          6
$ sed -n '1913,1926p' docs/spec/specification.md                 4
$ grep -n 'run_identity_consistent\|occupancy_within_capacity' <36 front-of-house .md>
0 hits
```

`occupancy_within_capacity` arrived with `UX-567` this round;
`run_identity_consistent` predates it. Both are published, both gate a
run's trustworthiness, and neither is named in Part 33.1 or in any
document a reader opens.

## Required Fix

Part 33.1's list and the published set agree, derived rather than
restated — the `UX-564` shape, a `§32.7.x` row recording the decision
because Part 33's own text is outside the region a round may edit.
A guard reads `confidence.hard_gates` against whichever list becomes
authoritative, so a seventh gate cannot arrive unnamed.

## Out of Scope

- Editing Part 33's text — the spec outside Part 32 is read-only for a round.

## Acceptance Test

Mutation: publish a seventh gate without recording it — red naming
the key; drop one from the record — red the other way.

## Outcome (round 84, 2026-09-03)

**Recorded**, in spec Part **32.7.5** — six rows, one per published key,
in the order `compute_confidence` writes them. Part 33's text untouched.

### The gap, re-measured at `8f51a26`. All three figures held exactly

```text
$ python3 -c "...json.load(with_timeline/analyze.json)['confidence']['hard_gates']"
['blame_chain_coverage_full', 'critical_path_coverage_full',
 'dominator_coverage_full', 'occupancy_within_capacity',
 'ordering_violations_zero', 'run_identity_consistent']            6
$ sed -n '1913,1926p' docs/spec/specification.md                   4
$ git ls-files '*.md' | grep -v docs/backlog/ | grep -v docs/audits/ | wc -l
36
$ ... | xargs grep -c 'run_identity_consistent\|occupancy_within_capacity'
0
```

### The close

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_hard_gates_are_named.py -q
tests/unit/test_the_hard_gates_are_named.py .......              [100%]
7 passed in 0.28s
```

The population is `analyze_run(macro_micro/run).confidence['hard_gates']`
and the stored `with_timeline/analyze.json` — two runs, never a list
restated in the guard. 32.7.5's `Part 33.1's line` column is read against
33.1's own two fenced blocks, so the four/two split is derived.

### Mutations verified red and reverted (7)

| # | mutation | guard reddened | run |
|---|---|---|---|
| 1 | `'seventh_gate_unnamed': True` into the `hard_gates` dict | `test_every_published_gate_has_a_registry_row`, naming the key | 1 failed, 6 deselected |
| 2 | a `task_coverage_full` row appended to 32.7.5 | `test_every_registry_row_names_a_published_gate` | 1 failed, 6 deselected |
| 3 | the I8 and I6 rows swapped | `test_the_rows_are_in_the_order_the_code_writes_them` **only** | 1 failed, 6 passed |
| 4 | `dominator_coverage` -> `dominator_tree_coverage` in the 33.1 column | `test_the_named_column_is_exactly_part_33_1s_blocks` | 1 failed, 6 deselected |
| 5 | `ordering_violations == 0` moved beside `blame_chain_coverage_full` | `test_each_named_row_quotes_the_line_for_its_own_gate` **only** | 1 failed, 6 deselected |
| 6 | `I8` -> `I88` | `test_each_omitted_gate_cites_the_invariant_that_carries_it` **only** | 1 failed, 6 passed |
| 7 | `run_identity_consistent` renamed in the stored fixture | `test_the_run_publishes_gates_at_all` | 1 failed, 6 deselected |

Each `replace` asserted its anchor first; each was grepped after
applying and after reverting.

### A guard of mine that did not discriminate

The first draft asserted `omitted == ['run_identity_consistent',
'occupancy_within_capacity']` — the finding typed out. It is implied by
the clauses around it (rows == published, named column == 33.1's
blocks), so no mutation could redden it alone. Replaced by
`test_each_named_row_quotes_the_line_for_its_own_gate`, which checks the
one thing they left open — a quoted 33.1 line sitting beside the gate it
is the line for — and reddens alone (mutation 5).

### Deviation from the Required Fix

One, a boundary rather than a narrowing. 32.7.5 moved Part 32's end from
1910 to **1939**, and two guards read that off the headings and require
`docs/contributing/fixing-guide.md` item 12 to quote it:

```text
FAILED test_the_process_documents_derive_their_figures.py::...[fixing-guide.md]
  does not carry the figure the tree gives: ['Part 32 spans 1515-1939']
FAILED test_the_spec_outside_part_32_is_read_only.py::...quotes_the_range...
  the fixing guide's item 12 does not say Part 32 spans 1515-1939
```

That file is another track's this round, and one track cannot know the
number: a second track adding a `32.7.x` row makes it neither 1939 nor
theirs. Left for the merge, derived once there. The read-only digest is
unchanged — every byte of this item is inside Part 32.

`bga/validation/invariants.py`'s module docstring names five of the six
gates; `run_identity_consistent` is absent there too. Outside this
item's surface — worth a row.
