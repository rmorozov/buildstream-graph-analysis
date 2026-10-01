# UX-1183: a traced element's binaries reach the page whole or counted

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1182 | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_traced_elements_binaries_reach_the_page.py`

## Motivation

Finding: 1 of the review.

Screenshots `03-binary-cost-one-element.png`, `04-card-81-binaries-shows-1.png`. `finish(top_n=5)` in `tools/bst_native_build_tracer.py` keeps the top 5 by CPU and the top 5 by count. On the heavy page `layer12/mod058` exec'd 81 distinct binaries: `binary_cost` shows 9 rows (4 of them with CPU "none", from the by-count list) and the card shows 1 ("Dominant binary tar, 2.9%"). `gperf`: 3 elements ran it, 0 rows show it. `python3`: 8 elements ran it, 1 row shows it. The section's sentence says "45 binaries ran" against `by_binary`'s 81. The schema describes the section as "One row per element and binary Plane 2 saw it run". `wall_us` is published and not drawn. Breaks §1b and §1c. Task walk: "Which binaries did X run, and how long did each take?" - 9 of 81, dead end; "Which elements share binary Y?" - 0 elements shown where the log has 3.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a membership the capture saw is published whole or counted": drop `top_n` from `finish` for membership, keeping the ranked five for the card, and publish `binaries[]` per element: every (element, binary) pair Plane 2 saw, with calls, CPU and wall time. The card draws the rest as a bounded table. `binary_cost` gains the `wall_us` column. The section's sentence counts the capture (`by_binary`'s keys), not the rows kept. A permitted key under `plane2/v2`, no bump.

## Decision

Owner (Ruslan, 2026-09-30 19:04 ("your defaults looks good to try")), D3: publish every (element, binary) pair Plane 2 saw, with calls, CPU and wall time. Keep the top-5 lists for the card, and draw the rest bounded. Class: product.

Architect (round 158, group A):

```text
Route:     `_BinaryCost.finish` publishes `binaries[]` per element (every binary: calls, cpu_us, wall_s), and top_n still bounds by_cpu/by_count for the card (D3). `_binary_rows` builds one row per `binaries[]` entry when present and otherwise falls back to by_cpu ∪ by_count (the committed macro_micro plane2.json has no raw log to regenerate). `binary_cost` COLUMNS gains wall_us. SECTION_ANSWERS.binary_cost counts `payload.by_binary` keys. The card draws the element's other binary_cost rows inside the existing closed "What Plane 2 saw" fold, through the `bounded` hook.
Rejected:  a new per-element `binaries` block in the report: the report's binary_cost rows already are the (element, binary) pairs, so a second copy breaks "one population, once" (json.py's own docstring).
Rejected:  a card link to the filtered table instead of a table: D3 says draw it bounded, and the focus link is 1186's.
Files:     tools/bst_native_build_tracer.py (`_BinaryCost.finish`); bga/report/json.py (`_binary_rows`); bga/schemas.py (`binary_cost` COLUMNS and GROWS to (element, binary) pairs; plane2's `binary_cost.*.binaries[]` if declared there); bga/disclosure.py (`binary_cost.{_PER_ELEMENT}.binaries[].*`); bga/plane2.py (only if it enumerates nested keys); bga/viewer/sections.js (`SECTION_ANSWERS.binary_cost(rows, payload)`); bga/viewer/element.js (`joinDetail`/`elementFactsFor` collect the rest, `elementSection` draws it in the join-evidence fold); tests/unit/test_a_traced_elements_binaries_reach_the_page.py; tests/tiers.py (large: heavy page plus browser)
Guard:     test_a_traced_elements_binaries_reach_the_page.py on `heavy_binary_run`: filtering binary_cost to the element with the most distinct binaries shows all of them (the count equals Plane 2's distinct set); filtering to a binary that 3 elements ran returns 3; the sentence's count equals len(by_binary); the card's fold holds that element's count minus the ranked rows.
Mutation:  build `binaries` from by_cpu[:top_n] -> reds; make the sentence count `by.size` over rows while by_binary is larger -> reds.
Class:     product (D3).
Split:     one track, after 1182 lands in the track's base or is cherry-picked into it.
Question:  none
```

Budgets:

- Page bytes: sections.js +3 lines and element.js +~20 lines, about +250 B gzipped (estimate). 144,196 -> ~144,450 of 160,000.
- xl_both controls: 0. Each xl_both element runs one `cc`, so the rest is empty and nothing is drawn. It replaces no control.
- xl_both height: 0 px. No rows are added, and the fold is closed.
- macro_micro words: 0 opened-page words. The rows sit in a closed `details`, which the budget leaves closed; the fold's summary count moves by digits only. The wall_us column adds about 1 word per visible binary_cost row, about +25 at the table bound. Nodes budget: about +250 on macro_micro (9 cards x ~7 rows). The track reads nodes first.
- Data half: xl_both is unchanged (1 row per element). The heavy page grows by about 3,100 rows x ~110 B before gzip, and its reading goes in the Outcome.

Overlaps:

- `elementSection` and `elementFactsFor`: UX-1187 (card lists dependents) writes the same two functions. Put them in one track, 1183 then 1187, or merge 1187 second.
- The `binary_cost` schema entry: UX-1186 declares its key (`bga:keyed_by`) and adds the binary jump kind. 1186 follows 1183.
- binary_cost's table: 1185 and 1191 (group B) read the heavy page's binary_cost and follow 1182. With 1183 merged first, their guards read the whole population. Otherwise they read 9 rows per element.
- UX-1176 and UX-1178 name binary_cost. The group C architect checks whether they touch `SECTION_ANSWERS.binary_cost`.

Taken, with three changes:

- The card draws its five costliest binaries in a fold of its own (`details[data-fold=binaries]`),
  not inside "What Plane 2 saw", and counts the rest ("+494 more"). It does not page them. That
  fold's guard (`test_the_merge_carries_every_field.py`) holds it at 1 level with `data-rows`
  equal to its `dd` count, and a table inside it breaks both. The rest went through `bounded` at
  first, and that measured +49 controls and +872 words on the heavy page (13,347 words, over the
  13,200 budget). The whole population is `binary_cost`'s table, which is bounded and filterable.
- `binaries[]` is published where `available` is true, beside the rankings. An element with no CPU measured keeps its `note` and draws no rows, as before; that membership is out of this row.
- The guard reads "filtering to X" off the exported page's `binary_cost` rows, not by typing into
  the table's filter: that code is UX-1185/1191's this round. The card fold, the sentence and the
  column are read in Chromium.

## Out of Scope

The Plane 2 capture itself; the top-5 card lists, which stay (D3); the jump box's binary kind (`UX-1186`).

## Acceptance Test

`tests/unit/test_a_traced_elements_binaries_reach_the_page.py`, on `UX-1182`'s page (the heavy page until it lands): filtering `binary_cost` to the element with the most distinct binaries shows every one of them; filtering to a binary three elements ran returns 3 elements; the sentence's count equals the number of `by_binary` keys. Mutation: restore `top_n=5` on membership; the guard reds.

## Outcome

### The gap, measured

```text
base 78d7be67, pages.heavy_binary_run (112 elements), the rankings plane2.json still publishes:
  layer02/mod006.bst: 499 distinct binaries in the log, 10 binary_cost rows (by_cpu ∪ by_count)
  binary_cost: 708 rows; 400 distinct binaries in rows against by_binary's 601
  7 binaries three elements ran: rows name 1, 0, 0, 0, 0, 0, 1 of their 3 elements
  wall_us published, no column; macro_micro sentence "9 binaries ran" against by_binary's 11
```

### The close, measured

```text
plane2.json binary_cost.<element>.binaries[]: every binary, {binary, count, cpu_us, wall_s}
  heavy plane2.json 453,384 -> 989,917 B; binary_cost 708 -> 4,057 rows (every log pair)
  heavy: widest 499 of 499; the 7 three-element binaries name 3 each; sentence "601 binaries ran"
  macro_micro (committed plane2.json, rankings only): "11 binaries ran"
  card: top 5 by CPU in `details[data-fold=binaries]`, "+494 more"
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_traced_elements_binaries_reach_the_page.py -q
6 passed in 4.14s
volume, opened, 1440x900 (after UX-1193 -> after this):
  page_bytes   144,202 -> 144,622 (+420)
  xl_both      controls 885 -> 886 (the Wall column's sort), words 12,318 -> 12,349, height 42,037 same
  macro_micro  controls 661 -> 662, words 12,399 -> 12,559, height 36,919 -> 37,207, nodes 5,606 -> 5,986
  heavy        controls 780 -> 781, words 12,475 -> 12,780, height 40,851 -> 41,488
```

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| M1 | tracer: `binaries` from `by_cpu[:top_n]` | 4 failed (widest, every pair, three elements, card) |
| M2 | sections.js: the sentence counts `by.size` over rows | `..._where_the_rows_are_ranked`, 1 failed |
| M3 | element.js: no "+N more" line | `test_the_page_counts_the_capture_and_the_card_the_element`, 1 failed |
| M4 | schemas.py: `wall_us` dropped from `binary_cost` COLUMNS | `..._and_the_table_draws_it`, 1 failed |
| M5 | json.py: `binaries` ignored, rows from the rankings | 5 failed |
| M6 | element.js: the card shows the five cheapest | `..._card_the_element`, 1 failed |
| M7 | (round-158 residue) element.js as at `43397b70`: `href="#binary_cost"`, no filter | `test_the_more_link_lands_on_binary_cost_filtered_to_the_element`, 1 failed, 6 passed |
| M8 | (residue) the link's click handler dropped | the same, 1 failed, 6 passed |
| M9 | (residue) the href without its `f.binary_cost` | the same (opened fresh), 1 failed, 6 passed |

Reverted from the saved copies: 6 passed. A first M6, "rank the card by calls", passed. It is
equivalent on this page, because the five costliest all ran 3 calls, the most any binary ran.

**Residue (round 158, walk N1).** The card's "+494 more" was `href="#binary_cost"`: on the heavy 1,202 page `layer16/mod006`'s link landed on `25 of 11,683`, filter empty, first row `layer00/mod000.bst`. The link now carries `f.binary_cost=element:<uid>` in its fragment and a press types the same filter into the table: `25 of 499 matched, of 11,683`, every mounted row `layer16/mod006.bst`, section top 60. The new clause presses the link on the widest element's card and opens its href fresh, reading the filter, the matched count against the report's rows for that element, the mounted rows' elements and the landed top: `7 passed in 6.05s`.
