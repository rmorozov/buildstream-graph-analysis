# UX-836: the page census lists no tables

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-665 (the census) | **Found by:** round 115, the design review | **Serves:** the walk and the design review, which drove 28 tables by hand this round | **Topic:** guards | **Area:** tools | **Shape:** mechanical

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

## Outcome

**Gap measured**, on `golden` (`HEAD` before this fix):

```text
$ python3 tools/dev_page_census.py golden.html | python3 -c "import json,sys; print(sorted(json.load(sys.stdin)))"
['controls', 'counters', 'drawings', 'planes', 'rail', 'sections', 'tables_with_nested']
```

**Close measured**, same export, after:

```text
$ python3 -m pytest tests/unit/test_a_new_control_class_lands_declared.py -v
8 passed in 5.84s
```

`census["tables"]` count (18) against an independent
`(document.querySelector("main")||document.body).querySelectorAll("table").length`
on a fresh boot: equal, both 18. First three entries (post-review fix,
`filters` narrowed to `input.table-filter`):

```json
{"section": "readers", "rows": 4, "visible_rows": 4, "badge": "4 rows", "filters": 0, "sortable": 0, "data_joined": null, "data_levels": null, "show_all": false}
{"section": "headline", "rows": 3, "visible_rows": 3, "badge": "3 rows", "filters": 0, "sortable": 2, "data_joined": null, "data_levels": null, "show_all": false}
{"section": "attribution", "rows": 8, "visible_rows": 8, "badge": null, "filters": 0, "sortable": 0, "data_joined": null, "data_levels": null, "show_all": false}
```

On `scale` (`gen-synthetic --seed 1`, 1,202 elements, 28 `<table>`,
matching the Motivation's hand count): `elements` badge `25 of
1,202`, `filters: 1`.

| mutation | result |
|---|---|
| `show_all` dropped from the returned entry | `test_every_table_entry_carries_the_declared_keys` reds: `Extra items in the right set: 'show_all'` |
| chapter/fold-opening lines removed, discovery filtered by `t.offsetParent !== null` (a naive "only what renders" census) | `test_the_table_count_matches_the_dom_independently` reds: `assert 2 == 18` — 16 of golden's 18 tables sit under a chapter shut by default |
| `filters` selector reverted from `input.table-filter` to `input` | `test_filters_excludes_the_copy_checkbox` reds: golden's `readers` etc. report `filters: 1` from `input.copy-markdown`, not a real filter |

All three reverted (from a saved copy, not `git checkout`) and re-run
green. The bare `input` selector originally counted `.copy-markdown`
(14 of golden's 18 tables) as a filter; caught in verifier review,
fixed to `input.table-filter`, and guarded on both `golden` (every
`filters == 0`, `input.copy-markdown` count ≥ 1) and `scale` (the one
table past the row cap reports `filters >= 1`). The chapter/fold
opening step has no discriminating power alone on the three committed
fixtures (`main.querySelectorAll("table")` already finds all of
golden/macro_micro/shared_resource's 18/35/61 regardless of open
state); it only matters combined with the `offsetParent` mutation.

**Deviation.** The first close counted the copy-markdown checkbox as a filter on 14 of 18 golden tables; the verifier found it and the amended commit counts `input.table-filter` only, with a golden-zero and a scale-one guard. Opening chapters by attribute does not change the count on any fixture — kept as a guard against a visibility-based discovery, and said so in the Outcome.
