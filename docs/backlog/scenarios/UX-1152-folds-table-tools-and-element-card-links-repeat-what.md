# UX-1152: folds, table tools and element-card links repeat what is already on screen

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M9, M10, M11, M12 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_repeats_are_not_drawn_twice.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M9, M10, M11, M12).

Long-text folds show a "... 254 chars" preview and repeat it once opened; Why #2's fold opens beside its row where #1 and #3 open below; table tools say "2 rows" three times and a one-row `#resource_blast` stays a 13-column table; the element card's "Also in:" links read section ids ("batch opportunities", "whatif"), and "Dominant binary" repeats "Ran one process at a time".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

An open fold hides its preview and is labelled by what it holds; every Why fold opens below its row; at two rows or fewer the tools strip drops its counts and a single row renders as pairs; element-card links use section titles.

## Decision

- **Folds:** `renderText` (`bga/viewer/structured.js`) labels a long-text fold `more` rather than `N chars`; `style.css` hides the preview (`.long-text-head`) while the fold is open, so the text shows once.
- **Why:** `.decision .action > details.why-ranked[open]` takes `flex-basis: 100%` - every Why opens on a row of its own, below its element.
- **Tools:** `interrogable` drops the badge and the distribution strip at `total <= 2` (`Copy N rows` keeps its count); a one-row array with no element column (`oneRecord`, `structured.js`) renders as `renderPairs` of its row - a section's own (`sections.js`) or a pair's member (`pairs.js`, `#resource_blast`). An element row stays a table, so its Inspect link stays (`test_one_click_from_investigation.py`, `latent_heavies`).
- **Card links:** `renderElementSections` (`element.js`) names each "Also in:" link with `nav.js`'s `sectionLabel` - the section's own heading - not its key.
- **Guard:** `tests/unit/test_repeats_are_not_drawn_twice.py`, one clause per shape on `golden`, `macro_micro` and the two-plane page at 1440.
- **Mutation:** undo each of the four changes; each reds its clause.
- **Not taken:** "Dominant binary" repeating "Ran one process at a time" - the Required Fix does not name it, and dropping the serial block's rows removes `serial_binary.*` from the DOM that `test_the_merge_carries_every_field.py` (`UX-356`) requires; a decision for the session.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: the four shapes each measured absent, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome

Two-plane page (`gen-synthetic --store --seed 1 --layers 8 --width 14`, `capture report`, `--export`), Chromium 1440x900, the guard's own expression (`m1152.js` in the track's scratch dir), every chapter open:

| shape | before (`36cfcc7a`) | after |
|---|---|---|
| long-text folds labelled `N chars` | 4 of 4 | 0 |
| open folds repeating their preview | 4 of 4 | 0 |
| Why folds opening beside their row | 1 of 3 (`Why #2`) | 0 |
| tables of 1-2 rows with a badge or strip | 5 of 5 (`rows`, `phases`, `constraints`, `choke_points`, `consolidation_candidates`) | 0 of 4 |
| one-row non-element tables | 1 (`#resource_blast` `rows`, 13 columns) | 0 |
| "Also in:" links not reading their section's title | 78 of 78 | 0 |

Guard: `PYTEST_XDIST= python3 -m pytest tests/unit/test_repeats_are_not_drawn_twice.py -q` - `21 passed in 3.64s`.

| mutation | reddened | count |
|---|---|---|
| drop the open fold's `display: none` on `.long-text-head` | `test_an_open_fold_shows_its_text_once` | 2 failed, 19 passed |
| `"more"` back to `` `${text.length} chars` `` | `test_a_fold_is_not_labelled_by_its_length` | 2 failed, 19 passed |
| drop `details.why-ranked[open] { flex-basis: 100% }` | `test_every_why_opens_below_its_row` x3 | 3 failed, 18 passed |
| `FEW_ROWS = 2` to `0` | `test_two_rows_carry_no_count_and_no_strip` x3 | 3 failed, 18 passed |
| `oneRecord`'s `rows.length === 1` to `=== -1` | `test_one_row_is_pairs_not_a_table` | 2 failed, 19 passed |
| the `pairs.js` branch off / the `sections.js` branch off | the same clause | 1 failed each |
| the link's text back to `key.replace(/[-_]/g, ' ')` | `test_a_card_link_reads_its_sections_title` x3 | 3 failed, 18 passed |

Re-based guards. `test_pointer_travel_is_a_budget.py`, all four rows, 3 runs, spread 0: macro_micro 1440 J3 15.67 to 16.49 bits, both_scale 390 J3 26.98 to 28.65, the rest within 0.8 bit and 5% of wheel; `UNOFFERED["macro_micro"]` `["change"]` to `[]` - its one-row section is a pair list now, which carries a `?` door. `test_the_page_has_a_volume_budget.py`'s 50-element class, px 38,200 to 38,600 and words 13,200 to 13,600: the card links' titles are 343 words and 396 px of `macro_micro`'s 13,098 to 13,441 and 37,805 to 38,201; styleguide §3e restates both.

Deviation: the fold's label is `more`/`less`, not a name for its content - the `dt` beside every such fold already names it ("Caveat", "Headline"). Not done: "Dominant binary" and "Ran one process at a time" still list the same binary - the Required Fix does not name it, and dropping `serial_binary`'s rows removes fields `test_the_merge_carries_every_field.py` (`UX-356`) requires in the DOM; a decision for the session.

Merge fix (round 154 fixer): a one-row record holding a nested table stays a table (`restructuring`, `serialization_point_risks` keep their folds, rail entries and nested controls - 10 guards); the pairs member keeps only its `dl` (the shim's lowercase `tagName` had left a stray `rows` section beside `blast`); at <= 2 rows the strip states the floor unlabelled and uncounted ("Below the sample floor - too few to have a shape", `UX-226`) so `Copy N rows` is the one count; the guard re-based to both; `UNOFFERED["macro_micro"]` back to `["change"]`. Mutations: nested clause off 6 failed, `dl` lookup reverted 2 failed, `counted: true` 3 failed, `FEW_ROWS = 0` 3 failed.
