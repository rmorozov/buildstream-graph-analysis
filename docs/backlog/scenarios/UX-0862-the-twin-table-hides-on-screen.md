# UX-862: the twin table hides on screen

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-195 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R1 (a closed twin is closed) | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

`exhibitTwin` sets `table.hidden = true` and its guard passes, but
`bga/viewer/style.css` carries `main table { display: block; ... }`, an
author-origin rule that beats the browser's `[hidden] { display: none }`
on every table whatever the selector's specificity. The twin renders
open with `hidden` true. The guard reads the property, not the rendered
display - the proxy shape of fixing guide §5.

## Required Fix

`bga/viewer/style.css`: the block rule excludes `table.twin-table`
(or the twin gets an explicit `display: none` under `[hidden]`); a real
Chrome case asserts the twin's computed display is `none` while hidden
and `table` after the toggle.

## Decomposition

Input classes: hidden, toggled open, print; reader: real Chrome, not
the DOM shim (`UX-359`); the journey it extends is R1's twin toggle.

## Out of Scope

The print block, which already forces the twin open.

## Acceptance Test

`tests/unit/test_a_drawing_is_graded.py` gains the computed-style
case in Chrome; mutation: restore the unconditional rule - red.

## Outcome

**Gap measured.** With the unconditional rule restored (the round's own
mutation), the new Chrome case:

```text
AssertionError: {'before': 'block', 'after': 'block'}
assert 'block' == 'none'
```

- confirming the twin renders open while `hidden` is true, exactly as
the motivation states.

**Close measured**, `bga/viewer/style.css:574` reading
`main table:not(.twin-table) { display: block; ... }`:

```text
tests/unit/test_a_drawing_is_graded.py::TestTheTwinReallyHidesOnScreen
::test_the_twin_is_hidden_until_toggled_open PASSED
28 passed in 8.45s   (whole file, real Chrome)
```

Wider: `test_the_fold_says_how_deep_it_goes.py`,
`test_the_report_has_two_panes.py`, `test_a_rail_click_lands_on_its_
section.py` (the other three files naming `main table`) - 51 passed,
71.84s - unaffected, since only the excluded selector changed.

### Mutation table

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `test_the_twin_is_hidden_until_toggled_open` | restore `main table { display: block; ... }` (drop `:not(.twin-table)`) | yes | 1 failed, 27 passed -> 28 passed after revert |

Deviation (merge): none - the verifier passed it as filed; the Chrome
case reads the computed display.
