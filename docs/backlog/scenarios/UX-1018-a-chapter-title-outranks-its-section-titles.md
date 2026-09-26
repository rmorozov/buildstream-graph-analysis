# UX-1018: a chapter title outranks its section titles in the heading outline

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.1 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
h1                        the wordmark "bga"
chapter title             h2, 17px, 700
section title             h2, 17px, 700
```

A chapter and its first section look identical, and the outline has one level where it needs three.

## Decomposition

Input classes: chapter, section and block titles; both fixtures. The journey extends scanning the outline into telling a chapter from its section.

## Required Fix

`h1` the run, `h2` a chapter at `--font-h1`, `h3` a section at `--font-h2`, `h4` a block at body weight 600, in `bga/viewer/chapters.js` and `bga/viewer/style.css`. §4f's four sizes hold.

## Out of Scope

Renaming the wordmark.

## Acceptance Test

`tests/unit/test_the_heading_outline_has_three_levels.py`, booted: the outline skips no level, and every chapter title is strictly larger than every section title. Mutation: render section titles as `h2`, and the guard reds.

## Outcome

Gap measured: booted `golden`, every rendered heading: `h1` "bga" 21px,
`h2.chapter-title` 17px/700 and `h2` (section) 17px/700 - one outline
level for two roles, a reader cannot tell a chapter from its own first
section without reading either.

Close measured: `PYTHONPATH=$PWD pytest tests/unit/test_the_heading_outline_has_three_levels.py -q`
— 3 passed. `chapters.js`'s `promoteHeadingLevels` retags every section
it collects (`h2`->`h3`, `h3`->`h4`) once, in the single place every
section passes through regardless of which of a dozen renderer modules
built it - `sectionHead`, `sections.js`, `decision.js`, `element.js`,
`views.js`, `questions.js` all still emit `h2`/`h3` and are none the
wiser. `style.css`: `h2`=`--font-h1` (chapter), `h3`=`--font-h2`
(section), `h4`=body weight 600 (block); five selectors that read a
section's own heading by tag (`nav.js`x2, `rawjson.js`, `views.js`,
three test files' own instruments) widened to `"h2, h3"` so they work
whether they run before or after the promotion pass.

Mutation table:

| guard | mutation | result |
|---|---|---|
| `test_the_heading_outline_has_three_levels.py::test_no_level_is_skipped` + `::test_chapter_titles_are_strictly_larger_than_section_titles` | `chapters.js`'s `h2`->`h3` promotion loop disabled (section titles render as `h2`) | red: level skip `(2, 4)` x3, and no `h3`s left to compare |

Full heading/nav/fold/rail regression sweep (214 + 174 tests across
every file that queries a section heading by tag): all green after the
fix; the fix was red on this same sweep once (`old.attributes is not
iterable` - `tests/dom_shim.mjs` has no `.attributes`, only `.attrs` -
`retag()` now reads either).

`make lint`: clean. `dev_sizes.py --check`: ok, 148 files.

**Surfaces beyond the declared two** (`chapters.js`, `style.css`): the
Required Fix's own file list could not be satisfied without them -
`nav.js`, `rawjson.js`, `views.js` each select a section's own heading
by tag (`"h2"`), and three existing test files carry the same
instrument. `docs/design/styleguide.md`'s §7 guard table also gained
this row's three guard names (shared row - `UX-1027`'s primary-grade
guard lands in it too, later in this same track).
