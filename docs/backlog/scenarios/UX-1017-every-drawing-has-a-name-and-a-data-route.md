# UX-1017: every drawing has an accessible name and a route to its numbers

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.9 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

**Guard:** test_every_drawing_has_a_name_and_a_data_route.py

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
svg[role=img] with no accessible name   20 of 23 (macro_micro), 8 of 11 (golden)
```

A screen reader hears "image" for every density strip and the sparkline.

## Decomposition

Input classes: every drawing kind (density strip, sparkline, decomposition, interval, chains); both fixtures. The journey extends reading a drawing's sentence into reaching the numbers it draws.

## Required Fix

Every `svg[role=img]` drawn by `bga/viewer/` carries its §6 sentence as its name, and a route to its values, by kind:

| kind | drawn in | route |
|---|---|---|
| density strip | `drawings.js` | its §2f table twin in the same figure |
| decomposition, interval | `drawings.js` | their table twin in the same figure |
| sparkline | `drawings.js`, `element.js` | `aria-details` on the values it sits beside |
| comparison band | `views.js` `renderBand` | none today: this row draws its twin |
| store trend | `views.js` | none today: this row draws its twin |

A kind found during the work with no route gets its twin here too.

## Out of Scope

Sonification.

## Acceptance Test

`tests/unit/test_every_drawing_has_a_name_and_a_data_route.py`, booted on both fixtures: every `svg[role=img]` has a non-empty accessible name and a resolvable data route. Mutation: drop the name from the density strip, and the guard reds.

## Outcome

**Gap measured.** Styleguide §6e.9's own measurement, restated: 20 of 23
`svg[role=img]` on `macro_micro` and 8 of 11 on `golden` carried neither
`aria-label` nor a `<title>`, before this item.

**Close measured.** `python3 -m pytest
tests/unit/test_every_drawing_has_a_name_and_a_data_route.py -q`:

```text
14 passed in 7.5-8.2s
```

Every one of `drawings.js`'s five builders (sparkline, strip,
columnStrip, decomposition, interval), both grades, plus
`element.js`'s inline sparkline and `views.js`'s `renderBand`/
`renderTrend`, now carries `aria-label` equal to its own sentence and
`aria-details` resolving to a node — the table twin where §2a draws one
(exhibit grade), the sentence span itself otherwise; the two composed
figures always carry a twin. Booted on both fixtures: every
`svg[role=img]` in the export has a non-empty name and a resolvable
route.

**Mutation table.**

| guard | mutation | reddened | count |
|---|---|---|---|
| `TestEveryDrawingsBuilderNamesAndRoutesIt` (`strip`, both grades) | drop the `nameDrawing(...)` call from `strip()` | `label` is empty | 2 of 9 parametrised cases |
| `TestEveryDrawingOnTheRealPagesIsNamedAndRouted` (both clauses) | same mutation | every density strip on `macro_micro` (3) has no name, no route | 2 |

4 of 14 clauses reddened by the Acceptance Test's own mutation ("drop
the name from the density strip"); the remaining 10 (sparkline,
decomposition, interval, the two composed figures, the `golden`
fixture) are unaffected by a `strip()`-only mutation, as expected.

Deviation: none from the Required Fix; on the merge `views.js`'s drawings import went back to three lines so the thin-views guard can read its source (`83029c5f`).

**Review (#295):** `sparkline`, `strip` (annotation grade) and
`element.js`'s inline sparkline routed to their sentence, which names
only the edges/extremum/labelled subset — `strip`'s own `stripTicks`
drops labels a nine-decile payload still ticks. Fixed by a new
`drawings.js:valueRoute`: a hidden node whose full mark list lives in
`aria-label`, an attribute, so it adds no words to
`test_the_page_has_a_volume_budget.py`'s `main.textContent` count
(measured: 30 passed, budget unchanged). `columnStrip` is left alone —
its p50/p95 ticks are the "no derived number" boundary its own doc
already states, and naming them would print what it refuses to print.
`TestEveryPlottedValueReachesTheRoute` (new) asserts every drawn
`data-value`/`data-raw` mark appears in its route; mutated back to
`route = sentence` for `sparkline`, `strip`, `renderElementHistory` in
turn, each reddened the new guard, each restored to 20/20 passed.
