# UX-526: the large budget class is measured at its bottom and breached at its top

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-367 (the budget), UX-366 and UX-419 (the 40-row bound) | **Serves:** anyone who opens a report of a project larger than the seeded run | **Topic:** guards

## Motivation

`test_the_page_has_a_volume_budget.py` asserts the class "to 4,000
elements" on one run of 1,202. Round 79 built the top of the class:

```text
bga gen-synthetic /tmp/r77/xl --layers 20 --width 200 --seed 1     4,002 elements
                       @1,202      @4,002     budget "to 4,000"
nodes                  24,345      73,075     27,500      2.7×
words                  37,312     107,352     41,000      2.6×
controls                1,949       4,774      2,300      2.1×
<tr> in DOM / rendered  1,572/295  4,826/319
export                  1.0 MB     2.4 MB     (48 s to write)
```

The growth is four surfaces: `elements`, `wall_clock_share_us` and
`leaf_analysis` keep every row in the DOM hidden past the 40-row
bound (`structured.js:646-656`, by design), and the Perfetto
"Ask about element" `<select>` carries one `<option>` per element
(`UX-527`). The budget holds where it is measured and nowhere above.

## Required Fix

- The seeded 4,002-element run joins the guard as the class's top
  point (the class is asserted at both ends, the way the tier
  floors are).
- Hidden rows past the bound leave the DOM: the table keeps the
  rendered rows and the count, and materialises the rest on the
  §3a focus/expand path from the payload — which is where those
  rows are already held once.
- Before/after at 4,002 pasted for the four counters.

## Out of Scope

- The embedded data half — `UX-529`.
- The `<select>` — `UX-527`, its own control.

## Acceptance Test

The volume-budget guard runs the 4,002 run and is green; mutation:
restore hidden rows to the DOM — red at 4,002, green at 1,202 (so the
new point is the one that discriminates).

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

`bga gen-synthetic /tmp/r80/b/xl --layers 20 --width 200 --seed 1` is
4,002 elements; exported and booted at 1440x900, chapters opened, the
same `_LOOK` the budget uses:

```text
                       opened    words   controls    nodes   <tr> in DOM
scale  1,202  before   26,576   37,312      1,949   24,345         1,545
              after    26,576    8,247        787    5,925           273
xl     4,002  before   27,222  107,352      4,774   73,075         4,800
              after    27,222    8,263        812    8,953           306
```

`budget_for(4002)` raised `past every size class` before this, so the
class boundary moves 4,000 -> 4,100 and its four opened bounds are
restated from the top: **32,000 / 9,000 / 900 / 10,000**. Height does
not move, for `UX-419`'s reason — a bounded row costs no pixels.

### The Motivation's mechanism was wrong for the biggest surface

`wall_clock_share_us` is not a table and does not go through
`structured.js:646-656`. It is a `<dl>` bounded by
`boundPairs`/`boundGroups` (`UX-419`), and at 4,002 elements it held
**96,065 of the page's 107,352 words, 4,005 of its 4,774 controls and
24,020 of its 73,075 DOM elements** — per section, measured:

```text
section                 words   ctrl   nodes
wall_clock_share_us     96065   4005   24020
perfetto-questions       2044     20    4119
findings                  440     28     118
```

The task names it as one of the three growth surfaces, and its bound
calls its groups "rows", so it is fixed with them: `boundPairs` detaches,
`boundCards` does not (a finding carries an `#anchor` that has to land).
Tables alone would have left the page at 103,351 words and 32,725 nodes.

### Deviation: the Acceptance Test's predicted discrimination

The mutation is red at **both** points, not green at 1,202:

```text
mutation                          scale nodes    xl nodes    budget
M1 rows stay in the DOM              17,373      49,303      10,000
M2 bounded pairs stay in the DOM     12,897      32,725      10,000
```

"Green at 1,202" was only reachable with bounds set near the *unfixed*
4,002 page (35,000 nodes), and `test_the_budgets_are_not_slack` forbids
those once the page is 8,953: 2 x 8,953 < 35,000. So the new point
discriminates by magnitude — 4.9x its budget against 1.7x — rather than
by sign. Written down rather than engineered around.

### Mutations verified red and reverted (3)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `showOnly` keeps the row in the DOM | volume budget at both scale and xl; `inDom == shown` at 4,000 rows | 2 failed / 1 failed |
| M2 | `boundGroups` never detaches | volume budget at both scale and xl | 2 failed |
| M3 | `data-rows` publishes the shown count, not the population | `test_a_value_shows_what_it_is::test_a_map_is_a_table_a_reader_can_search` | 1 failed |

### Acceptance Test

```text
$ python3 -m pytest tests/unit/test_the_page_has_a_volume_budget.py -q
25 passed, 2 skipped in 126.99s (0:02:06)
```

`make lint` clean; `make test-touching` 416 tests green. The file was
22.3s in `tests/tiers.py` LARGE and is **127s** measured alone at
`-n auto` (200.9s cold) — the 4,002-element **export** is 69.7s of it,
against 3.8s for the browser (`UX-529` owns the export).
