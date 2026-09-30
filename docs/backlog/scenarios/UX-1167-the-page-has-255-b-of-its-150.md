# UX-1167: the page has 255 B of its 150,000 B budget left, and every viewer row now pays with cuts

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk; the page-byte and control budgets at `8b7e3d3b` (2026-09-30) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_ceilings_table_states_each_bound.py::test_each_row_states_the_value_its_constant_holds`; the bound itself: `tests/unit/test_the_viewer_js_ships_compressed.py::test_the_page_half_is_under_its_bound`

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

At `8b7e3d3b` the golden page is 149,745 of 150,000 B (255 B left); `xl_both` controls 886 of 900; `macro_micro` opened words 12,483 of 13,200; `xl_both` height 42,002 of 43,500. Round 155's seven tracks summed +990 B against ~849 B of headroom and the merge sat 34 B over before it recovered with no budget raised.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Owner, round 156 (2026-09-30): Ruslan chose "Raise to 160 KB" on the round-156 decision card, relayed by the orchestrator mid-track.

```text
Route:     PAGE_BUDGET_B 150,000 -> 160,000 B. Reason measured: golden's page half is 149,762 B at 3e6feb45 (238 B under), and round 156's six page rows land on it at ~150 B each
Rejected:  the brief's first route, "keep 150,000 and move the weight" (a literal-aware JS indentation strip) - superseded by the owner's call before any code; its measured yield is in the Outcome for a later row
Kept:      the 900-controls cap on xl_both (886 measured); no measured need to move it
Files:     tools/bga_view.py (the constant); docs/guides/cli.md (the ceilings row); the budget notes in test_the_report_you_can_attach.py and test_the_viewer_js_ships_compressed.py; tests/unit/test_the_ceilings_table_states_each_bound.py
Guard:     each cli.md ceilings row's stated value equals its constant - the reach guard finds a row per bound but never read its number
Mutation:  PAGE_BUDGET_B back to 150_000 with the doc at 160,000; the doc back to 150,000 with the code at 160_000; PAGE_BUDGET_B = 149_000 (below the page)
```

## Required Fix

The owner decides whether the 150,000 B budget and the 900 controls cap stay. The row names the decision; it does not take it: keep both (each viewer row pays for its bytes with cuts), raise one with a measured reason, or move the weight (the exporter's minifier, the shared strings) so the ceiling is not the constraint.

## Out of Scope

Any change to the budgets before the owner decides; the viewer rows that spend it.

## Acceptance Test

The owner's answer is written into the budget guards' docstring line and this row's Outcome, and the next viewer row is briefed against it.

## Outcome

**Gap measured** (golden, `tools.bga_view.export` over `tests/pages.py`'s fixture, at `3e6feb45`):

```text
                 page_bytes   module (b64 gz)   style.css   rest    budget    headroom
golden           149,762      111,732           31,204      6,826   150,000   238
macro_micro      149,762      111,732           31,204      6,826   150,000   238
```

**Close measured**: `PAGE_BUDGET_B = 160_000`; the same page is 149,762 B, 10,238 B under. `PYTEST_XDIST= pytest test_the_viewer_js_ships_compressed.py test_the_ceilings_reach_a_reader.py test_the_report_you_can_attach.py test_the_exports_data_half_has_a_budget.py test_the_ceilings_table_states_each_bound.py`: 59 passed, including `test_the_export_boots_and_a_stack_names_a_source_line` and the `DATA_DWARFS_PAGE` ratio clauses at 160,000.

The route not taken, measured for a later row (`_viewer_module()` gzipped and base64'd as `_module_blocks` does): stripping every line's leading whitespace takes the module from 111,732 to 106,584 B (-5,148 B). The naive strip is unsafe inside a multi-line template literal, so a real one has to be literal-aware (`_comment_spans`' scanner). Tightening `style.css` around `{};:,>` takes 31,202 to ~27,720 B (-3,480 B). The stylesheet ships uncompressed.

`xl_both` controls, 886 of 900 (`button, input, select, a` with every chapter opened, 1440x900): `a` 214 (nav holds 117 controls), `a.inspect` 96, `a.element` 81, `button.collapse` 79, `button.mark-this` 72, `button.json-toggle` 46, `button.describe` 37, `button.copy-sql` 32, `button.fold-more`/`focus-this` 24 each, `list-prev`/`copy-rows`/`input.copy-markdown` 23 each, `a.path-box` 22. Links are 413 of the 886. By section: nav 117, horizon 74, bottleneck 63, findings 59, parallelism 47.

**Mutation table** (the three budget files plus the new guard, 42 tests):

| mutation | reddened | count |
|---|---|---|
| `PAGE_BUDGET_B = 150_000`, cli.md at 160,000 | `test_each_row_states_the_value_its_constant_holds` (new guard alone: nothing else sees the drift) | 1 failed, 41 passed |
| `PAGE_BUDGET_B = 149_000` (below the page) | the new guard, `test_the_page_half_is_under_its_bound`, `test_the_page_itself_stays_within_its_budget`, `test_the_page_is_a_backstop_away_from_where_it_is` | 4 failed, 38 passed |
| cli.md row back to `150,000 B`, code at 160,000 | `test_each_row_states_the_value_its_constant_holds` | 1 failed, 41 passed |

Reverted from a copy each time. All green after.
