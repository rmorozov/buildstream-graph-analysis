# UX-1212: Focus heads its investigation and names what the document holds

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_population_key_is_declared.py::test_the_horizon_row_says_the_section_is_present_and_the_uid_absent`

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P4 (pre-existing): the focus bar with "clear" is drawn 10,165 px above the investigation it heads (pre-round 6,284 px); after Focus the reader never sees "clear". P9: the Focus investigation reads "Optimization horizon: not in this document" while that section is in the document (the uid is not in it).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Decision

Round 160 architect, group B (at ec816233), this row:

```text
Route:     (b) investigationEvidence says which absence it is - the section present and the uid not in it against the section absent ("not in this document"), read as resolvePath(payload, path's table key) !== undefined; (a) the bar fix waits for a reproduction.
Rejected:  sticky focus bar - pins ~40 px at 390 for every focused read before the defect is reproduced; drop the row for "present" - loses the absence UX-228 states on purpose.
Files:     bga/viewer/decision.js investigationEvidence; tests/unit/test_a_population_key_is_declared.py new test on the walk fixture; (a) later: bga/viewer/app.js wireFocusAndMarks refresh/reveal only.
Guard:     Focus layer19/mod040.bst on the 1,202 page: horizon row reads the section present and the uid absent (measured: section present, row "not in this document", 1440 and 390).
Mutation:  restore the single "not in this document" text -> red.
Class:     product.
```

Track: the text taken is "section present, this element not in it" (the architect's "in this document; this element is not in it" read as "Optimization horizon: in this document; ...", ambiguous as a row). (a) was reproduced first, as the brief asks; see the Outcome.

## Required Fix

After Focus, "clear" is on screen with the investigation; a section present without the uid says the element is not in it.

## Out of Scope

Focus across navigation and Back (round 159, H).

## Acceptance Test

After Focus on the 1,202 page, the bar's clear control is within the viewport; the horizon line names the uid's absence; a guard beside the Focus guards in `test_a_population_key_is_declared.py`. Mutation: restore the defect, and the guard reds.

## Outcome

**(a) not reproduced; closed as such.** Page: `gen-synthetic --store --seed 1 --layers 20 --width 60` exported at this commit (24 element cards, 1,202 elements) and `tests.pages.heavy_binary_run`, Chromium 1440x900 and 390x844; each press, `scrollY` before to after, bar top and clear-in-viewport read after 800-1500 ms:

```text
path                                         1440 (bar 86, inv 150)      390 (bar 224, inv 288)
card Focus, cards 0,1,5,6,12,18,22,23 of 24  after=86, clear in view     after=224, clear in view
palette click on the Focus action (from 4,724 / 6,931 px)   after=86, in view   after=224, in view
palette ArrowDown+Enter on Focus (from 3,331 / 5,067 px)    after=86, in view   after=224, in view
focus A then card B while focused            after=86, one bar            after=224, one bar
a reloaded focus link (?link#~...)           scrollY 0, bar 86, in view   scrollY 0, bar 224, in view
heavy-binary page: card B, palette keys      same: after=86 / 224
```

Not driven: F5 on a focused page scrolled deep, where the browser restores the old scrollY and `reveal` is suppressed by design (app.js: "a page restoring focus from its url has not asked to be scrolled"); the 10,165 px is that distance if it happened. No change taken.

**(b) gap measured:** Focus `layer19/mod040.bst` on the 1,202 page: `optimization_horizon[element_uid=...]` row read "not in this document" while `section[data-section=optimization_horizon]` is on the page, at 1440 and 390.
**Close measured:** the row reads "section present, this element not in it"; Plane 2 (section absent) still "not in this document" (`test_focus_is_an_investigation.py` green). decision.js +3/-1 lines, about +130 B on the page half; `test_the_page_has_a_volume_budget.py` green (no unfocused word, node or control added).

| mutation | reddened | count |
|---|---|---|
| decision.js: restore `found === undefined ? "not in this document" : "yes"` | `test_the_horizon_row_says_the_section_is_present_and_the_uid_absent` | 2 failed (1440, 390) |

Deviation: the text differs from the architect's wording (reason in Decision). The ArrowDown path lands on row 1 first (`(active + step + n + 1) % n` from -1), noticed not changed.

