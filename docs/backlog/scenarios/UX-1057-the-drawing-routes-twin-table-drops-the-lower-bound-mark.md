# UX-1057: the decomposition bar's aria-details twin table drops the certified lower-bound mark

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 143's walk (`10cde1d2`) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_every_drawing_has_a_name_and_a_data_route.py::TestEveryPlottedValueReachesTheRoute::test_every_drawn_mark_is_in_the_route`

## Motivation

Measured on `10cde1d2`, `drawings.js`'s decomposition bar
(`drawing-route-0`): the SVG plots a certified lower-bound mark
(`data-mark="lb"`) with an `aria-label` stating it. The `aria-details`
twin table styleguide Rule 9 requires (every value the SVG plots also
readable as a row) has no row for that mark - a screen-reader user
reading the table sees every segment's value but not the certified
floor the picture shows.

## Decomposition

Input classes: a route with a lower-bound mark, a route without one,
multiple marks on one route.

## Required Fix

`drawings.js`'s twin-table builder gains a row per `data-mark="lb"`
element, stating the same value and label the SVG's `aria-label`
carries, in `bga/viewer/drawings.js`.

## Out of Scope

Any other twin-table gap this pass did not measure; `columnStrip`
(kept out of the value route, `round-142`'s note).

## Acceptance Test

A route with a lower-bound mark: the twin table has a row whose text
equals the SVG mark's `aria-label`. Mutation: drop the row-emission
call, and the guard reds.

## Decision

```text
Route:     drawings.js decomposition(): the twin-table builder adds a row for `mark` (label and value) whenever a mark is drawn.
Rejected:  a new test file: the parametrized value-coverage test already reads SVG `data-raw` against the route text and only lacks a case with a mark.
Files:     bga/viewer/drawings.js, tests/unit/test_every_drawing_has_a_name_and_a_data_route.py (add a `decomposition(..., {total: 4, mark: {key: "lb", label: "lower bound", value: 2}, grade})` case to test_every_drawn_mark_is_in_the_route)
Guard:     test_every_drawn_mark_is_in_the_route: the mark's data-raw appears in the twin's text (red on main).
Mutation:  drop the mark-row emission; the new case reds.
Class:     product
```

## Outcome

Gap measured (`python3 -m pytest tests/unit/test_every_drawing_has_a_name_and_a_data_route.py -n 2 -q`, base `b8072cd7` plus the new case, exhibit grade):

```text
FAILED ...test_every_drawn_mark_is_in_the_route[decomposition(... mark: { key: "lb", label: "lower bound", value: 2 } ...)-exhibit]
'values': ['3', '1', '2'], 'missing': ['2'], 'routeText': ' As tablePartValuea3b1'
1 failed, 21 passed
```

Close measured (same command, `decomposition()`'s exhibit twin gains a `[mark.label, format(mark.value)]` row):

```text
22 passed in 13.78s
```

Selector `dev_touching.py --base b8072cd7 --list` (45 files, includes the page byte and export size guards): 2137 passed, 3 skipped.

| Mutation | Reddened | Count |
|---|---|---|
| drop the `rows.push([mark.label, ...])` | the exhibit mark case | 1 failed, 21 passed |
| revert | same file | 22 passed |

The annotation-grade case is green on base (its route is the sentence, which already names the mark); it is kept as the pair.
