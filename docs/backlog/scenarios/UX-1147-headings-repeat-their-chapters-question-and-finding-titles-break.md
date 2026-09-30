# UX-1147: headings repeat their chapter's question and finding titles break sentence case

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M2, M3 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_heading_is_its_question_alone.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M2, M3).

"Which run is this?" is both a chapter and a section heading; "Where did the time actually go, per element?" appears twice in `#perfetto-questions`; h3 text includes its chip and button ("Findings (14)View as JSON"). Finding titles read "Highest Criticality Elements:", "Certified Headroom:", "RESOURCE WAIT", and colon titles head empty bodies in the element card and Why #2.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

One question per heading level; chip and JSON button outside the heading element; finding titles are sentence case with no trailing colon.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no two headings share text, no heading's accessible name contains its chip or button text, and no finding title ends in a colon or holds an all-caps word, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

Controls move out of the heading, not the heading's name onto an `aria-label`: `primitives.js` `headRow` wraps a heading in `div.section-head` (`div.chapter-head` for a chapter) and the fold, reader chip, JSON toggle and chapter-open control join that row; the row takes the heading's margins and flex layout in `style.css`. Duplicates: `run_instance` asks "When, and on what machine, was this captured?" and `confidence` "How confident is each part of this report?" (`bga/schemas.py`); the Perfetto worked example is left out of its category fold. Finding titles (`bga/findings.py`) lose Title Case and trailing colons, and the wait category is lower case. The failed-build alarm ("THIS BUILD DID NOT FINISH") and "do NOT" in details are left: neither is a title on these pages. Guard: headings on the two-plane page, `golden`, `macro_micro`. Mutation: put the controls back in the heading; restore a duplicate; restore a title.

## Outcome

**Gap measured.** Two-plane page (`gen-synthetic --seed 1 --store --layers 8 --width 14`), the guard's own measure, before this row:

```text
headings 108  shared ['Where did the time actually go, per element?']  holding controls 82
finding titles: trailing colon 3  shouted 1  Title Case 4
```

"Which run is this?" (chapter and `run_instance`) did not register as shared because both headings' text carried their buttons ("Which run is this?▸ Sections · 4").

**Close measured.** Same page after:

```text
headings 107  shared []  holding controls 0
finding titles: trailing colon 0  shouted 0  Title Case 0
```

Document height at 1440: 7,577 px before and after.

**Mutation table** (`PYTEST_XDIST= python3 -m pytest tests/unit/test_a_heading_is_its_question_alone.py`, 18 tests):

| mutation | reddened | run |
|---|---|---|
| `headRow` returns the heading (controls inside it) | `test_no_heading_holds_its_controls` x3 | 3 failed, 15 passed |
| the fold repeats the worked question | `test_no_two_headings_share_text` x3 | 3 failed, 15 passed |
| `run_instance` asks "Which run is this?" again | `test_no_two_headings_share_text` x3 | 3 failed, 15 passed |
| "Highest Criticality Elements:" and `.upper()` restored | colon, shouts, Title Case (two-plane); shouts (`golden`, `macro_micro`) | 5 failed, 13 passed |

Reverted: 18 passed.

**Deviation.** Re-based guards, each for the structure this row changed: `test_pointer_travel_is_a_budget.py`, `test_a_sections_controls_sit_together.py`, `test_a_chapter_fold_has_one_place_and_one_label.py` (offsets read against the head row); `test_the_rail_says_what_the_heading_says.py`, `test_the_report_has_chapters.py` (the heading's section through the row); `test_one_click_from_investigation.py` (the worked query is drawn once, not twice - `UX-348` drew it twice on purpose); `test_report_key_findings.py`, `test_headline_points_at_the_time.py` (the new title strings). Regenerated: `docs/design/rendered-strings.json` (also carries `UX-1148`'s reordered provenance labels) and both committed analyses. Styleguide §6e.1 and §6e.3 rows amended, and the §6e guard-ledger row names the guard. `bga/schemas.py` is a surface the Decomposition did not name.

Round-154 fixer: test_attribution_hints re-based to the sentence-case "dependency wait" label; the README pasted block re-pasted from a fresh run (untracked tail, Efficiency score).

Round-154 residue: at 390 a head with a toggle or chip is a grid (fold, chip, JSON above; h3 its own row; `style.css`, replacing UX-1145's dead in-heading rule). h3 < 80% of content width 72/73, 44/45, 65/66 -> 0 (two-plane, golden, macro_micro); tallest 395 -> 53 px; 1440 head geometry byte-identical. Guard: two 390 clauses (width >= 80%, height <= its text at full width); pre-fix CSS 6 red, `min-height: 3em` 3 red, `max-width: 70%` 6 red. macro_micro 390 travel re-based down (J3 24.53 -> 22.87, 3 runs, spread 0); both_scale 390 J3 25.23 -> 28.16, J4 wheel 19273 -> 21745 left red, not raised.
