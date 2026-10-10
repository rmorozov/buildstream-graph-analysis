# UX-1342: the headline's "top 3" and the work order name two different triples

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** walk seed 5 (2026-10-07), finding 3 | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_order_says_why_it_is_not_the_table.py`

## Motivation

On `tests/fixtures/macro_micro` at `3e3657a7`, `bga analyze` text: the
headline table's top 3 is core/lib-b/lib-d (12.1 + 4.0 + 4.0 s), the order
reads "core.bst (31.1 s) -> codegen.bst (24.1 s, pays off after the step
before) -> lib-b.bst", and one line below "codegen.bst (7.0 s) - ... worth
nothing to fix today". `bga whatif --element codegen.bst`: "43.200s ->
43.200s (saves 0.000s)". `UX-1135` made the joint figure honest (23.1 s,
matching `whatif` on core+codegen+lib-b); the two triples remain.

## Decomposition

Input classes: a run whose top savings are independent; one where a saving
pays only after another (codegen after core); one with fewer than three
elements worth fixing. Journey: `macro_micro`, example 06.

## Required Fix

Open: one triple across the headline and the order, or a sentence naming
why they differ (codegen pays only after core).

## Decision

Route:     A sentence, not one shared triple. In `_outlook_findings` (`bga/findings.py:1819-1830`), take the joint-saving elements missing from the `time-concentration` table (`[d['element_uid'] for d in path_elements_by_duration(result)[:TIME_CONCENTRATION_SHOWN_MAX]]`); when that set is non-empty, append one detail line after "In this order:": `    Not the table above: each step is re-ranked once the steps before it are done, so {_and(absent)} {'enters'|'enter'} here and not there`. On macro_micro it names codegen.bst. ~8 lines of code, ~35 of test.
Rejected:  one triple from the table's ranking: the joint figure would lose the codegen compounding UX-1135 made honest and `whatif` confirms.
Rejected:  one triple from the horizon: the table would print codegen.bst saving 0 s alone, a false row; both triples contradict UX-440 (`test_the_two_rankings_answer_two_questions.py`): two questions over two keys.
Rejected:  renaming "the top N" in the heading only: churns titles and never says why.
Files:     bga/findings.py; tests/unit/test_the_order_says_why_it_is_not_the_table.py (new); tests/fixtures/with_timeline/analyze.json and tests/fixtures/golden/mixed_task_kinds/expected_output.json, both rewritten by `python3 tools/dev_refresh_analysis.py --write <fixture>`, never by hand.
Guard:     tests/unit/test_the_order_says_why_it_is_not_the_table.py, parametrized over macro_micro/run and golden/mixed_task_kinds through `compute_findings`: the joint elements missing from the `time-concentration` finding's `elements` are exactly the uids named in the joint-saving line containing "re-ranked"; a SimpleNamespace case (as `test_the_order_marks_only_the_steps_measured_to_pay_off_later`) where every joint element is in the table prints no such line; `"codegen.bst"` pinned in the line on macro_micro.
Mutation:  `if False:` or dropping the append reddens both fixture cases; `absent` = the full joint set reddens the exact-set clause; an unconditional line reddens the no-line case.
Class:     product (R1, walk seed 5 finding 3)
Split:     one track.
Question:  none; the default keeps UX-440's two rankings and UX-1135's joint figure.

## Out of Scope

The joint-saving arithmetic (`UX-1135`).

## Acceptance Test

On `macro_micro`, every "top 3" the text names is the same three elements,
or the text says why not.

## Outcome (round 173)

**Gap measured** (`bga analyze tests/fixtures/macro_micro/run`, base `b1323876`):
the order line read `core.bst (31.1 s) -> codegen.bst (24.1 s, pays off after
the step before) -> lib-b.bst (20.1 s)` under a table whose top 3 was
core/lib-b/lib-d; nothing said why codegen.bst was absent from the table.

**Close measured** (same command, after):

```text
    In this order: core.bst (31.1 s) -> codegen.bst (24.1 s, pays off after the step before) -> lib-b.bst (20.1 s)
    Not the table above: the table ranks by time on the critical path, this order by what each step saves once the steps before it are done, so codegen.bst enters here and not there
```

`tests/unit/test_the_order_says_why_it_is_not_the_table.py`: 9 passed.
`with_timeline/analyze.json` and `golden/mixed_task_kinds/expected_output.json`
rewritten by `tools/dev_refresh_analysis.py --write` (one detail line each;
mixed_task_kinds names extra.bst).

| Mutation | Result |
|---|---|
| `if ordered and absent` -> `if False` | 6 failed, 3 passed |
| `absent` = the full joint set | 8 failed, 1 passed |
| `if ordered and absent` -> `if ordered` (no `absent` gate) | 2 failed, 7 passed |
| drop `+ reranked` from the detail | 6 failed, 3 passed |
| drop `shown and` from `absent` | 1 failed, 8 passed (empty-table case) |
| `absent` also names one table element | 7 failed, 2 passed |
| `if ordered and absent` -> `if absent` (drop `ordered`) | 1 failed, 8 passed (one-step horizon) |
| `enters`/`enter` -> always `enters` | 1 failed, 8 passed (two-absent case) |

**Deviation:** the Decision's wording ("re-ranked once the steps before it are
done") was false when the absent element is the order's first step; the line
now says the table ranks by critical-path time and the order by what each step
saves once the steps before it are done. Line is longer; README's 107 lines
unchanged. Guard grew from 4 to 9 cases.
