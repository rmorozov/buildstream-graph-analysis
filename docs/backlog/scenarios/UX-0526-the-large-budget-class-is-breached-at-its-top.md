# UX-526: the large budget class is measured at its bottom and breached at its top

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-367 (the budget), UX-366 and UX-419 (the 40-row bound) | **Serves:** anyone who opens a report of a project larger than the seeded run | **Topic:** guards

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
