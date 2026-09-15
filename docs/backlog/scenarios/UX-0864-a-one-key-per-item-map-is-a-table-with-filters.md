# UX-864: a one-key-per-item map is a table with filters

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-419, UX-526 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R2 (find one binary or one task among a thousand) | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

`renderSection` (`bga/viewer/sections.js`) sends every object value
to `renderPairs` without classifying it; `by_binary` and
`wall_clock_share_us` - one key per binary, one per task - render as a
definition list of a thousand rows with a show-all button and no filter
or sort. The styleguide's own row says a one-key-per-element map is a
table, `shapes.js` returns `CONTROLS.MAP_TABLE` for exactly this shape,
and no renderer reads it; `renderStructured` already routes the same
shape to `mapTable` one level down.

## Required Fix

`bga/viewer/sections.js`: the object branch calls `classify()` and
routes `MAP_TABLE` through `mapTable`/`buildTable` with the filter, sort
and top-N tools the blast table has; small keyed objects keep the pairs
pattern per the styleguide's threshold.

## Decomposition

Input classes: a map of 3 keys (pairs), of 40 (table), of 1202 (table,
top-N); the journey it extends is R2 finding one binary in the census.

## Out of Scope

Nested maps; the schema.

## Acceptance Test

`tests/unit/test_the_mapping_is_law.py` gains: `by_binary` and
`wall_clock_share_us` render a table with a filter input and sortable
headers; mutation: route back to `renderPairs` - red.
