# UX-1279: a sort button's name says what pressing it does, not "sort: By binary"

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-165 walk (2026-10-02) | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_sort_button_names_its_next_press.py`

## Motivation

Every sortable header's button reads `<Column>, sort: <table>` to a
screen reader (`structured.js`, `UX-1197`): on `#by_binary` each one is
"Blocked, sort: By binary", "CPU, sort: By binary". The sentence names the
table, not the action or the order a press gives; `aria-sort` on the `th`
carries the state, but the button's own name never says which way it will
sort. Present at `53d5d364b`, before round 165.

## Decomposition

Input classes: `macro_micro`'s `by_binary` and `element_durations` tables,
each column unsorted, ascending and descending.

## Required Fix

The button's accessible name says the column and what a press does
("Sort by Blocked, descending"), the table's name once, where `UX-1197`
needed it.

## Out of Scope

The visible header text; `aria-sort` on the `th`.

## Acceptance Test

On `macro_micro`, every sort button's `aria-label` names its column and
the order its next press applies, and changes after a press. Mutation:
restore the `${column}, sort: ${table}` template and the guard reds.

## Decision

```text
Route:     tables.js gains one `labelSorts(table)`. It writes each own head's `button.th-sort` aria-label as `Sort by ${column}, ${next}: ${table.sortName}`, where `next` is the order a press applies. That order comes from a new `next(th)`: the reverse of a set `aria-sort`, otherwise "descending" for a `data-quantity` head and "ascending" for the rest. The click handler's inline direction expression becomes `next(th)`, so the label and the press read one rule. `showSort` calls `labelSorts` last, so every press, the opening rank and the viewstate restore all relabel. structured.js:1318-1323's microtask loop shrinks to `table.sortName = named; labelSorts(table)`. The table name stays once, as UX-1197 needs for unique names.
Rejected:  a second label pass in the click handler (misses showSort's opening rank at structured.js:1168/1188 and viewstate's restore); a data-sort-name attribute (adds DOM and bytes for nothing an expando does not carry); dropping the table name (UX-1197's "no two buttons share a name" goes red); a visible glyph or text change (Out of Scope).
Files:     bga/viewer/tables.js (next, labelSorts, showSort, the click handler at 780-783); bga/viewer/structured.js (1318-1323); tests/unit/test_a_sort_button_names_its_next_press.py (new); tests/unit/test_a_pager_continues_the_view.py:301 ("Duration, sort: Tasks" -> "Sort by Duration, descending: Tasks"); tests/quality_reference.json only if dev_sizes moves
Guard:     tests/unit/test_a_sort_button_names_its_next_press.py - on macro_micro's by_binary and element_durations tables, every button.th-sort aria-label starts "Sort by <its head text>, " and ends ": <table name>". The order it names equals the th's aria-sort after one press. A second press flips both the label and aria-sort. The unsorted quantity heads read "descending".
Mutation:  M1 restore `${sort.textContent.trim()}, sort: ${named}` -> red; M2 drop the labelSorts call from showSort (label set once at rest) -> the after-press claim reds; M3 invert next()'s quantity default in labelSorts alone -> first-press claim reds
Reading:   container. On macro_micro #by_binary, the Blocked button reads "Sort by Blocked, descending: By binary" at rest and "Sort by Blocked, ascending: By binary" after one press. The page half stays <= PAGE_BUDGET_B 166,250 B.
```

## Outcome

Gap measured: M1 below is the base template (`${text}, sort: ${table}`) under the new guard.
`macro_micro` has no `element_durations` table, so the guard reads `by_binary` and `elements`.

```text
$ python3 -m pytest tests/unit/test_a_sort_button_names_its_next_press.py -n 2 -q    (M1 applied)
6 failed in 3.71s
```

Close measured:

```text
$ python3 -m pytest tests/unit/test_a_sort_button_names_its_next_press.py tests/unit/test_a_pager_continues_the_view.py -n 2 -q
16 passed
$ page_half of tools.bga_view.export(golden | macro_micro)   (PAGE_BUDGET_B 166,250)
before  166,216 / 166,216      after  166,220 / 166,220      headroom 30 B
$ python3 tools/dev_sizes.py --check      sizes ok: 168 file(s) measured
$ make lint                                clean
```

The click handler's `specs[index].quantity` and `data-quantity` agree (structured.js:608 writes one from
the other). To fit 33 B, `sortable()` lost its `specs` parameter and reads `data-sortable` off the head
(`String(spec.sortable)`, the same value); both callers in structured.js follow. The one-line `next()` is
the reverse of `aria-sort` or of a virtual "ascending" for a quantity head.
`tools/dev_touching.py`: 13 failed, 2711 passed; all 13 need the ignored records (touch map empty,
`ci_reference.json` absent) or the new file's tier row, not this diff.

| Mutation | Reddened | Printed |
|---|---|---|
| M1 restore `${text}, sort: ${table}` in labelSorts | all six | 6 failed |
| M2 drop `labelSorts(table)` from showSort | second-press claim, both tables | 2 failed, 4 passed |
| M3 invert `next()`'s quantity default | named-order claim, both tables | 2 failed, 4 passed |
