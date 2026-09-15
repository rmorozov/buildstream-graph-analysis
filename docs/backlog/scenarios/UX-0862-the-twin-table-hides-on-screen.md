# UX-862: the twin table hides on screen

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-195 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R1 (a closed twin is closed) | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

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
