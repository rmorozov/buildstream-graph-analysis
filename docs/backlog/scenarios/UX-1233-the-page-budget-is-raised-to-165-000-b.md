# UX-1233: the page budget is raised to 165,000 B for round 161's eleven viewer rows

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 161's architect read of the page budget (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_ceilings_table_states_each_bound.py::test_each_row_states_the_value_its_constant_holds`; the bound itself: `tests/unit/test_the_viewer_js_ships_compressed.py::test_the_page_half_is_under_its_bound`

## Motivation

At `cd2466b2` the page half is 159,146 of `PAGE_BUDGET_B` 160,000 B on golden and macro_micro (`tools.bga_view.export` over `tests/pages.py`'s fixtures): 854 B for eleven viewer rows (UX-1219..1229), where round 155 spent ~990 B on seven.

## Decomposition

Input classes: `golden` and `macro_micro`, the two fixtures the budget guard exports.

## Required Fix

The owner decides whether the budget moves; the row carries the answer into the constant, cli.md's ceilings row and the budget notes.

## Out of Scope

The literal-aware whitespace strip UX-1167 measured at -5,148 B (a route not taken); the 900-controls cap.

## Acceptance Test

cli.md's ceilings row states the constant's value; the page-half guard reds under a constant below the page.

## Decision

Owner, round 161 (2026-10-01): Ruslan chose "Raise to 165 KB" on the round-161 decision card, over "Keep 160 KB" and "Strip whitespace".

```text
Route:     PAGE_BUDGET_B 160,000 -> 165,000 B
Files:     tools/bga_view.py, docs/guides/cli.md, tests/unit/test_the_viewer_js_ships_compressed.py, tests/unit/test_the_report_you_can_attach.py
Guard:     test_the_ceilings_table_states_each_bound.py reads cli.md's value against the constant
Mutation:  cli.md back to 160,000 with the code at 165_000; PAGE_BUDGET_B = 159_000 (below the page)
Class:     product
```

## Outcome

**Gap measured**: 159,146 of 160,000 B (854 B) at `cd2466b2`, golden and macro_micro alike (the architect's export reading).

**Close measured**: `PAGE_BUDGET_B = 165_000`. `PYTEST_XDIST= pytest -p no:randomly test_the_viewer_js_ships_compressed.py test_the_ceilings_reach_a_reader.py test_the_report_you_can_attach.py test_the_exports_data_half_has_a_budget.py test_the_ceilings_table_states_each_bound.py`: 60 passed in 32.60s.

**Mutation table**:

| mutation | reddened | count |
|---|---|---|
| cli.md row back to 160,000 B, code 165_000 | `test_each_row_states_the_value_its_constant_holds` | 1 failed |
| `PAGE_BUDGET_B = 159_000` | `test_the_page_half_is_under_its_bound` | 1 failed |
