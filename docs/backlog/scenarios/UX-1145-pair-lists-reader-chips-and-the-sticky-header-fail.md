# UX-1145: pair lists, reader chips and the sticky header fail the compact class

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H6 | **Serves:** R1, R6 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_compact_class_stacks_pairs.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H6).

At 390x844: `#capacity_recommendation`'s `dl.pairs` columns are 177.5px/148.5px (term wider than value); its constraints table is 148x1073 px; 11 reader chips inside `h3` exceed 30 px tall ("capacity operator" 41x123 px); header plus rail take 168 of 844 px.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

In the compact class a term stacks above its value, a chip does not wrap, and the rail bar stops sticking once the page scrolls.

## Decision

- **Choice:** under `@media (max-width: 60rem)` in `bga/viewer/style.css`: `.pairs` is one column (`dt` above its `dd`; `UX-1137`'s `button.describe` keeps `grid-column: 1 / -1`); a *folded* rail is `position: static` (an opened one still sticks, so J2's rail-to-section hop stays on screen); a head holding a JSON toggle is a grid whose `.reader-tag` takes a row of its own. `applyRole` (`bga/viewer/chapters.js`) writes one `span.reader-chip` per reader, `white-space: nowrap`, so a tag breaks between readers and never inside one; its `textContent` is unchanged. In the regular class the tag shrinks to its longest chip, no further.
- **Revised in the track:** the first cut, a whole-tag `nowrap` beside the title, overflowed three `json-toggle`s past a 390 head (the tag reads "recipe author, CI gatekeeper, capacity operator"); a static rail at every fold state left J2's section link 11,589 px of wheel away.
- **Guard:** `tests/unit/test_the_compact_class_stacks_pairs.py`, `golden`, `macro_micro` and the two-plane page at 390x844: no rendered `dd` narrower than its `dt`, every `.reader-chip` at most 30 px tall, pinned `body > *` chrome after `scrollTo(0, 3000)` under 12% of 844.
- **Mutation:** drop each rule, and the spans; each reds its own clause.
- **Styleguide:** §6e.10 (index row and rule 10) gains the compact rule.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: at 390x844 no `dd` is narrower than its `dt`, no chip is taller than one line, and sticky chrome is under 12% of the viewport, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome

Two-plane page (`gen-synthetic --store --seed 1 --layers 8 --width 14`, `capture report`, `--export`), Chromium 390x844, `m1145.mjs` in the track's scratch dir:

| | before (`36cfcc7a`) | after |
|---|---|---|
| rendered `dd` narrower than its `dt` | 257 | 0 |
| reader tag or chip over 30 px tall | 11 (`local optimizer` 40x102) | 0 |
| `#capacity_recommendation` constraints table | 148 px wide | 342 px wide |
| pinned chrome after `scrollTo(0, 3000)` | header 69 + rail 98 = 167 px (19.8%) | header 69 px (8.2%) |

Guard: `PYTEST_XDIST= python3 -m pytest tests/unit/test_the_compact_class_stacks_pairs.py -q` - `15 passed in 3.92s`.

| mutation | reddened | count |
|---|---|---|
| drop compact `.pairs { grid-template-columns: minmax(0, 1fr) }` | `test_no_value_is_narrower_than_its_term` x3 | 3 failed, 12 passed |
| drop `.reader-chip { white-space: nowrap; }` | `test_a_reader_chip_is_one_line` x3 | 3 failed, 12 passed |
| `chipsInto(tag, words)` to `tag.textContent = words.join(', ')` | `test_each_reader_is_its_own_chip` x3 | 3 failed, 12 passed |
| drop the folded rail's `position: static` | `test_sticky_chrome_is_under_its_share` x3 | 3 failed, 12 passed |

Re-based guards. `test_pointer_travel_is_a_budget.py`, both 390 rows, 3 runs, spread 0: macro_micro J1 wheel 424 to 478 px (the decision's pairs stack, so its Copy sits lower), J3 23.76 to 21.12 bits, J4 17,717 to 18,656 px; both_scale J1 771 to 825 px, J3 30.32 to 26.98 bits, J4 22,257 to 22,346 px. The head grid is held there: without it three `json-toggle`s overflow a 390 head (dx spread 213.5 px). `test_a_reader_role_demotes.py` counts nodes outside `[data-reader-tag]`: a chosen role leaves one chip where "anyone" wore three (2760 to 2757 on `golden`). `test_the_page_has_a_volume_budget.py`'s compact landed bound, 8,500 to 8,800 (`golden` 8,688) and 11,400 to 11,800 (`macro_micro` 11,604), and `test_the_chain_folds_and_clicks_are_counted.py`'s compact reach, 13.0 to 13.5 screens (`macro_micro` `run` 13.4): a stacked pair spends a line on its term; styleguide §3c and §3e restate both.

Deviation: `.reader-tag`'s `min-width: 0` became `min-content` - a nowrap chip in a tag shrunk past it overlapped the JSON toggle at 1440 with a 40 px root (`test_a_sections_controls_sit_together.py`, zoom40, 3 and 4 sections); restoring `min-width: 0` reds it again.
