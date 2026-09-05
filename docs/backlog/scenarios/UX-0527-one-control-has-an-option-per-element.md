# UX-527: one control has an option per element

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-368 (the query the control feeds), UX-369 (the substitution) | **Serves:** anyone asking Perfetto about one element of a large project | **Topic:** viewer | **Area:** bga/viewer

## Motivation

```text
section perfetto-questions, "Ask about element" <select>
  @14 elements       14 options
  @1,202          1,202 options      section text 26 KB
  @4,002          4,002 options      section text 86 KB
```

`questions.js:851-859` fills the control from the run's whole
population (`app.js:681`); `test_the_query_asks_about_this_run.py:201`
requires the population be *this run's* and says nothing about the
control's size. It is the only `<select>` on the page that grows
with the project, and a 4,002-entry dropdown is not a control anyone
can use.

## Required Fix

A search box over the same population (`<input list>` with a
`<datalist>` capped at the jump box's 8 results, or the jump box
itself with a "then ask" action) — the substitution and the guard's
population claim unchanged. Options rendered: the 8 that match, not
the 4,002 that exist.

## Out of Scope

- The query library's content — `UX-368`/`UX-369` own the queries.

## Acceptance Test

At 4,002 elements the control's rendered options ≤ 8 for any typed
prefix and the chosen element reaches the query; mutation: fill the
list with the population — red.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

Per section on the seeded 4,002-element run
(`gen-synthetic --layers 20 --width 200 --seed 1`), booted at 1440x900
with the chapters open, after `UX-526`:

```text
section                 words   ctrl   nodes    <option>
perfetto-questions       2044     20    4119        4002
wall_clock_share_us       977     43     248           0
findings                  440     28     118           0
```

**4,119 of that page's 8,953 DOM elements were one control.** It was the
biggest section on the page once `UX-526` had bounded the rest.

### After

An `<input list>` over a `<datalist>` the same population fills, capped
at `PICKER_SHOWN = 8` — the jump box's own limit, because this is the
same act. `includes`, not a prefix: an element is `layer07/mod123.bst`
and the part a reader remembers is rarely the layer.

```text
                     nodes   perfetto-questions nodes   <option>
xl     4,002 before   8,953                    4,119       4,002
             after    4,960                      126           8
scale  1,202 before   5,925                    1,319       1,202
             after    4,732                      126           8
```

Words move by **+12** — the sentence beside the control says what the
box searches and how many it offers — and controls not at all: a
`<select>` and an `<input>` are one control each, an `<option>` never
was. `test_the_budgets_are_not_slack` went red on the large class's
nodes bound, which is that clause's job; restated 10,000 -> 5,500 here
rather than in `UX-526`. `UX-369`'s population claim is unchanged and
now read off `data-population` rather than counted in the DOM: the
control searches all 4,002, and the last uid the run has — which no
published array names — reaches the SQL and the clipboard once typed.

### One defect this found in the page

`el()` assigns any unhyphenated attribute name as a **property**, and
`HTMLInputElement.prototype.list` is read-only, so `{ list: id }` threw
inside the module and took the whole questions section with it. Same
shape as `UX-317`'s `for` / `htmlFor`; `setAttribute("list", …)` now.

### Mutations verified red and reverted (3)

| # | mutation | red |
|---|---|---|
| M1 | `fill` draws the whole population, not `slice(0, 8)` | 1 |
| M2 | `data-population` publishes 8 | 1 |
| M3 | the control is a `<select>` again | 2 |

**M1 did not redden the first draft of its clause**, which read only the
post-typing datalist: the needle was a whole uid, so one row matched
whatever the cap was. It reads the list before the probe types and
after. M3's first attempt was non-discriminating — `select.type` is
read-only, so it reddened by crashing the section, not by being a menu.

### Acceptance Test

```text
$ python3 -m pytest tests/unit/test_the_query_asks_about_this_run.py \
      tests/unit/test_one_page_behind_the_button.py -q
31 passed in 129.96s (0:02:09)
$ python3 -m pytest tests/unit/test_the_page_has_a_volume_budget.py -q
25 passed, 2 skipped in 162.60s (0:02:42)
```

`make lint` clean. `test_the_query_asks_about_this_run.py` was **14.7s**
in MEDIUM — 0.3s under the large floor, which its own note predicted
would move — because the scale probe is now at 4,002 rather than 1,202,
where the Acceptance Test is. **109s** here under this round's parallel
load; **54.1s** alone on a quiet machine, which is the figure the merge
tiered it LARGE on.
