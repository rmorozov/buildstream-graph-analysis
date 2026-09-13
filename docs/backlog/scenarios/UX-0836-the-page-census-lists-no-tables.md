# UX-836: the page census lists no tables

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-665 (the census) | **Found by:** round 115, the design review | **Serves:** the walk and the design review, which drove 28 tables by hand this round | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tools/dev_page_census.py` prints sections, rail, controls, drawings
and `tables_with_nested`; on the scale export the page has 28 `<table>`
elements and the census names none of them as tables:

```text
$ python3 tools/dev_page_census.py scale.html | python3 -c "import json,sys; c=json.load(sys.stdin); print(sorted(c))"
['controls', 'counters', 'drawings', 'planes', 'rail', 'sections', 'tables_with_nested']
```

This round's review re-measured every table by hand — id, rows, badge,
filters, sort — the numbers `UX-835`'s guard and the next walk need.

## Required Fix

`tools/dev_page_census.py` gains `tables`: one entry per `<table>` — section, rows, visible rows, badge
text, filter count, sortable count, `data-joined`, `data-levels`, and
whether a "Show all" control is present. The census's own guard covers
the new key.

## Out of Scope

- Driving the tables — the census reads, it does not click (`UX-665`).

## Acceptance Test

On the golden export the census's `tables` count equals the DOM's
`table` count; mutation: drop the key — `tests/unit/test_a_new_control_class_lands_declared.py` reds.
