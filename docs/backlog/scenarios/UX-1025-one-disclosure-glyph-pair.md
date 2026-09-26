# UX-1025: one disclosure glyph pair, and a fold's label names its content

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.13 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
glyphs in use       ▾ in a boxed button (section fold), ▶ (details), ▸ (rail current mark)
label naming form   "How these were ranked ▶ 1 level, 2 rows"
```

## Decomposition

Input classes: section folds, `details`, rail disclosures, nested-table folds. The journey extends seeing a fold into knowing what opening it shows.

## Required Fix

▸ closed, ▾ open, at the start of every disclosure's label in `bga/viewer/`; a label names the content and its count first; a nested fold keeps §3a.1's depth after it ("inputs: 2 rows, 1 level").

## Out of Scope

The rail's current-chapter mark, which is not a disclosure and takes another sign.

## Acceptance Test

`tests/unit/test_one_disclosure_glyph_pair.py`, booted: every disclosure starts with ▸ or ▾ matching its state, and no label is depth and count alone (`^\d+ levels?, \d+ rows?$`), while §3a.1's depth guard still finds the depth. Mutation: restore ▶ on `details`, and the guard reds.

## Outcome

Gap: `summary` had no marker of its own, so `<details>` drew the
browser's native `▶`/`▼` beside `nav.js`'s own `▸`/`▾` fold button -
two glyph pairs. `renderProvenance` (`decision.js`) drew "1 level, N
rows" alone whenever its caller passed no `label`.

Close: `style.css` hides the UA marker (`list-style: none`,
`::-webkit-details-marker`) and draws `▸`/`▾` on `summary::before`,
matching `[open]`. `renderProvenance`'s default label is now "The
rule" rather than empty, so an unlabeled fold reads "The rule · 1
level, N rows". New `tests/unit/test_one_disclosure_glyph_pair.py`
boots both fixtures, toggles every `<details>` once and reads its
`::before` content each way:

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_one_disclosure_glyph_pair.py -q
4 passed in 1.63s
```

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `▸` → UA's `▶` on `summary::before` | `test_every_disclosure_starts_with_the_matching_glyph[golden]`, `[macro_micro]` | 2 failed |
| restore the bare `"1 level, N rows"` default | `test_no_label_is_depth_and_count_alone[golden]`, `[macro_micro]` | 2 failed |

`tests/unit/test_why_bga_believes_what_it_believes.py`'s text
allowlist gained the new "The rule · " prefix (its own contract,
not this guard's).
