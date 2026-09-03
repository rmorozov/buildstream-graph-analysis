# UX-598: two of the four percentile rows publish no distribution

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-260 (the percentiles), UX-303 (the spread drawn), UX-581 | **Serves:** the reader who trusts Direction 11's table | **Topic:** contracts

## Motivation

Direction 11's table says `yes` for four quantities. Measured in
round 83, two of them publish a `bga:distribution` and two do not:

```text
git grep -n "_distribution(" bga/schemas.py
  1977   element_duration_distribution
  1983   blast_radius_distribution
```

Sandbox tax per element and processes per element are the two the
table promises and the schema does not carry. `UX-581` dated the
table rather than correcting it, because correcting it is either
publishing the two or withdrawing the rows — which is this item.

## Required Fix

The two missing quantities publish `bga:distribution` like their
siblings, or Direction 11's table withdraws their `yes` with the
measurement above beside it. A guard derives the table's `yes` rows
from `bga/schemas.py`, so the pair cannot drift apart again.

## Out of Scope

- The percentile rule itself (`UX-260`) — declined: the rule holds; its table is what drifted.

## Acceptance Test

Mutation: mark a fifth quantity `yes` in the table with no
distribution behind it — red; remove a distribution the table
claims — red.

## Outcome (round 84, 2026-09-03)

**The Motivation was falsified, and the fix is the half it did not
name.** All four `yes` rows publish a distribution; two of them were
declared by nothing, which is what the reader actually meets.

### The gap, re-measured before implementing

The filing's grep held, and means something else:

```text
$ git grep -n "_distribution(" bga/schemas.py
  1980 element_duration_distribution      1986 blast_radius_distribution
$ python3 -c "from bga.correlate import _scale_of; print(sorted(_scale_of(p, n)))"
['process_count_distribution', 'sandbox_tax_distribution']
```

`bga/schemas.py` is a proxy for "what publishes a distribution": the
other two are emitted by `_scale_of` into `correlate/v2`, where the
grep cannot see them. `UX-260`'s own Outcome table says so, and
`DISTRIBUTED_QUANTITIES` in `bga/analyzer.py` carries all four. Neither
branch of the Required Fix applies — nothing was unpublished, and
withdrawing the rows would make the table wrong the other way.

What *was* true: `_CORRELATE_OPTIONAL` did not list either key and
`_CORRELATE_HINTS` had no entry, so every percentile inside them
reached the reader as a bare number — `UX-343`'s defect, in the
contract the join emits.

### The close

Both now carry `bga:distribution` through the same `_distribution()`
helper their siblings use:

```text
sandbox_tax_distribution -> n duration_us investigate
   p50: {'bga:quantity': 'duration_us', ...}
process_count_distribution -> n count investigate
   p50: {'bga:quantity': 'count', ...}
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_percentile_rows...py -q
6 passed in 0.20s
```

Direction 11's table gained a `key` column naming each row's entry in
`bga/analyzer.py`, so the `percentile?` cell is *derived* from the
recorded split rather than compared to it by a reader. The dated note
and the Status line carry the measurement above.

### Mutations verified red and reverted (7)

| # | mutation | guard reddened | run |
|---|---|---|---|
| 1 | the `sandbox_tax_distribution` hint removed — the defect put back | `test_each_yes_declares_bga_distribution`, naming the key | 1 failed, 5 deselected |
| 2 | the `sandbox_tax` cell flipped to **no** | `test_every_cell_is_its_keys_membership` **only** | 1 failed, 5 passed |
| 3 | the `process_count` row deleted | `test_every_distributed_quantity_has_a_row` **only** | 1 failed, 5 passed |
| 4 | `shapes['process_count_distribution'] = ...` -> `pass` | `test_each_yes_publishes_a_distribution_shape` | 1 failed, 5 deselected |
| 5b | `share_of_critical_path_distribution` declared and typed | `test_no_quantity_answering_no_grew_one` | 1 failed, 5 deselected |
| 6 | a row's key unbackticked | `test_the_table_parses_to_rows_with_keys` | 1 failed, 5 deselected |
| 7 | a fifth `DISTRIBUTED_QUANTITIES` entry, in no table | `test_every_distributed_quantity_has_a_row` and the key-map clause | 2 failed, 4 passed |

Each `replace` asserted its anchor first; each was grepped after
applying and after reverting.

### A mutation that did not discriminate

The first attempt at 5 added the hint without the
`_CORRELATE_OPTIONAL` entry. It went red on `KeyError: correlate/v2:
view-hint for unknown key` — the schema builder refusing, not my
assertion. Rejected and rewritten as 5b, which declares the key
properly and reaches the clause.

### Deviation from the Required Fix

The disjunction it offered — publish the two, or withdraw their `yes` —
is answered by neither, because its premise did not survive
re-measurement. The rows stay `yes`, the two published keys gain the
declaration they lacked, and the guard derives the cells from
`bga/analyzer.py` rather than from `bga/schemas.py`, which is the proxy
that produced the wrong count. `bga/analyzer.py` and `bga/correlate.py`
were read and mutated but not changed.
