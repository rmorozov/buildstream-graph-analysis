# UX-1046: the rail shows the current chapter's sections, or every open chapter's — one rule

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3h, §6e.5 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

**Guard:** test_the_rail_is_a_source_list.py

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900; the rail before and after "Expand all":

```text
                         rail box  scrollHeight  section links  last chapter row bottom
macro_micro   landed       530 px       530 px              6            539 px
macro_micro   Expand all   848 px     2,239 px             76          2,152 px
74 elements   Expand all   848 px     2,601 px             87          2,458 px
1,202         Expand all   848 px     2,885 px             98          2,743 px
```

The rules-at-a-glance line says the rail shows "only the current
chapter's sections"; §3h's own mechanism says a rail row's disclosure
*is* the document's chapter fold, and §6e.5 says several chapters can
be open at once. The page follows the mechanism, so after "Expand all"
the rail is 2.6-3.4 of its own screens, growing with the run, and the
last chapter row sits up to 2.2 rail screens below the rail's bottom — §3h's round-90 measurement (1,902 px,
2.4 rail-screens) back, through the one path its guard does not press.

## Decomposition

Input classes: landed, one chapter opened, "Expand all", a fragment
into a folded chapter; both size classes.

## Required Fix

Decide: (a) the rail discloses only the chapter holding the scrollspy
mark, other open chapters showing their row alone, and the rail's
disclosure stops being the document fold; or (b) the rule reads "every
open chapter's sections" and the rail is bounded some other way.
Default, if no decision: (a), since it is the reading §3h was filed to
buy. Amend §3h and the glance line to one sentence.

## Decision

Route (a), Ruslan's default: the rail's disclosure follows the scrollspy mark, not the document's fold. `nav.js` `toc()` sets `data-current` on one `li[data-chapter]` at build (the first chapter); `scrollspy()`'s `mark()` moves it to the row holding the marked link. The hide rule becomes `.toc .chapters > li:not([data-current]) > .sections{display:none}`. The rail row button is navigation, not a fold: its click calls `chapters.js` `revealAndLand(chapterBox(root,id))` (opens the document chapter, never shuts it, lands on its head) and sets `data-current` on its own row in the same step. §3b holds at two interactions.

- aria: the rail button drops `aria-expanded`, `aria-controls` and `data-chapter-open`, keeps `data-toc-chapter` (read by `test_the_chain_folds_and_clicks_are_counted.py:230`); the current row's button carries `aria-current="true"`. `button.chapter-open` is the only control with `aria-expanded`. `labelFold`'s rail branch loses its `aria-expanded` and `data-open` writes and keeps only the label repaint via `box.__railToggle` (`fileInChapter` changes the count).
- Rejected: (b) (Ruslan left (a)); `aria-expanded` on a row whose press never shuts anything (a lie to AT); the row as `<a href>` (leaves §6d's quiet grade for no reader gain).
- Files: `bga/viewer/nav.js`, `chapters.js` (labelFold rail branch), `style.css` (§3h rule and comment), styleguide (§3h to one sentence: "every chapter, and only the sections of the chapter the reader is in; the rail row goes to its chapter, and the fold is the document's"; the line-57 glance row; line 2008; §3b "disclose the chapter's rail row" becomes "press"), `tests/unit/test_the_rail_is_a_source_list.py`, `tests/unit/test_a_keyboard_journey_reaches_every_chapter.py` (stops read `data-toc-chapter`; Enter reads the chapter box's `data-open` false→true).
- Guard: the rail file's landing clause reads `data-current`, not `data-open`. New class on macro_micro at 1440x900: (1) press "Expand all" and settle; `nav.scrollHeight` is unchanged and ≤ `clientHeight`+1, and every laid-out section link sits in the one row holding `aria-current`. (2) Press a non-current rail row: its box has `data-open="true"`, its row `data-current`, and one of its links is laid out. If the largest chapter disclosed alone overflows 848 px, measure it first: the unchanged-by-Expand-all clause stands and the ≤ box clause is a recorded deviation.
- Mutations: `labelFold` writes `data-current` from `isOpen(box)`, or the CSS keyed on `data-open` again: (1) reddens (reading back to 2,239 px). Drop `revealAndLand` from the row click: (2) reddens.
- Class product. One sequential track with UX-1044 on top (opus: architect-shaped judgement).

## Out of Scope

The rail's entries and labels (`UX-1044`).

## Acceptance Test

`test_the_rail_is_a_source_list.py` presses "Expand all" and holds the
rail's scrollHeight to its box (a) or to the bound (b) chosen.
Mutation: restore the coupling, and the clause reds.

## Outcome

**Gap measured.** The Motivation's table (`814a2db8`); reproduced by
mutation 1 below, which puts the fold coupling back: "Expand all grew
the rail from 530 to 2239 px", 67 links laid out outside the current row.

**Close measured.** `probe.py` (scratchpad): each page exported by
`tools.bga_view.export`, booted at 1440x900; "Expand all", then every
rail row pressed in turn. `nav.scrollHeight` / `clientHeight`, px:

```text
                 landed    Expand all   largest row alone (elements)   rows holding data-current after press
macro_micro     530/530      530/530         1,151/848  (24 links)      6 of 6
74 elements     612/612      612/612         1,457/848  (28 links)      7 of 7
1,202           612/612      612/612         1,741/848  (37 links)      7 of 7
```

Every pressed row's box read `data-open="true"` and its button
`aria-current="true"`. `pytest -n 2` on the files reading the changed
modules (38 selected by `grep -lE "nav\.js|chapters\.js|toc-chapter|
data-chapter-open|scrollspy|data-toc"` plus three reading the fold
controls): 568 passed, 2 skipped, 3 failed - the three
`test_the_rail_says_it_is_not_the_way_out.py` non-vacuity floors (`>= 10`
links on screen, which "Expand all" used to supply); the floor is now
read off the page: min(10, links in the row holding scrollspy's mark, or
the `data-current` row while focus hides every section) - served
macro_micro, before / during / after: here 6 >= 6 (decide), 3 >= 3
(change), 3 >= 3 (change): 8 passed.
`test_the_rail_is_a_source_list.py` 5 passed; keyboard journey + chain
folds 26 passed; styleguide guards 36 passed.

**Mutation table** (`tests/unit/test_the_rail_is_a_source_list.py`):

| mutation | reddened | run |
|---|---|---|
| `labelFold` toggles the row's `data-current` from `isOpen(box)` | `test_expand_all_leaves_the_rail_as_it_was` ("530 to 2239 px") | 1 failed, 1 passed |
| row click without `revealAndLand(target)` | `test_a_row_press_opens_and_discloses_its_chapter` ("stayed shut") | 1 failed, 1 passed |
| scrollspy's ended-above-the-line step disabled | same test ("pressed row is not current": the mark fell back to the previous chapter's last section) | 1 failed, 1 passed |
| decision row back to a `p.toc-rail` caption | `test_the_decision_row_brings_its_sections_back_from_anywhere` ("current: False, laid: 0, links: 6") | 1 failed, 5 passed |
| scrollspy marks the *next* row (`?.nextElementSibling`) | `test_the_rail_says_it_is_not_the_way_out.py`: `..._worth_hit_testing`, `..._clickable_again` (here < floor) | 2 failed, 6 passed |
| current look keyed on `li[data-current] > button` (survives lifting `aria-current`) | `test_every_control_has_a_resting_appearance.py::test_the_grades_stay_four` | 1 failed, 9 passed |
| keyboard journey without the body focus in `_START_AT_THE_TOP` | `test_the_stops_are_every_chapters_rail_row_in_order` (`decide` missing) | 1 failed, 6 passed |

Reverted from the scratchpad copy: 6 passed, and 8 passed.

**Deviation.** The largest chapter disclosed alone (`elements`) overflows
the 848 px box on all three pages (1,151-1,741 px), so the guard holds
"unchanged by Expand all" and the "<= box" clause is dropped, per the
Decision. Outside the Decision's file list: `scrollspy`'s `here()`
skips a section that ended above the reading line (without it a row
press landed on the chapter head and the mark returned to the previous
chapter), and `test_the_rail_says_it_is_not_the_way_out.py`'s floor.
The decision row is a press like the rest (was a caption), so its
sections come back from anywhere (§3b). The current row wears the rail's
one "you are here", `aria-current="location"` (weight and `--fg`, one
rule with the section link's); that still counted a sixth appearance, so
the grade guard reads each button with `aria-current` lifted, and §6d
declares "current" a state over a grade beside hover and pressed. The
keyboard journey starts every walk at the document top (landing's
`scrollIntoView` moves Chrome's focus starting point past the decision
row; draft row filed by the session) and requires every chapter id:
`-n 1`, three runs, 7 passed each.
The styleguide's §7 `§3b` row now names `test_the_rail_is_a_source_list.py`.
