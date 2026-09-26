# UX-1019: one concept is one word and one control on every bga surface

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.2 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

- each top action shows two "why" affordances side by side: a `why` link and a "▶ Why #1" disclosure;
- run / build / capture, element / task, chain / critical path are used interchangeably across chapters;
- the page, `perfetto.html`, `sql.html` and `describe()` name the same things with no shared list.

## Decomposition

Input classes: the page, `perfetto.html`, `sql.html` and `describe()`; top actions and their why controls. The journey extends reading one chapter into recognising the same thing in the next surface.

## Required Fix

A terminology matrix in `docs/design/styleguide.md` §6e.2: each reader noun, the one word for it, and the surfaces that print it. One "why" control per top action.

## Out of Scope

Renaming schema keys.

## Acceptance Test

The reader-strings guard (§4g) reads the matrix and reds on a listed synonym in rendered text or `describe()` output; booted, one "why" control per top action. Mutation: print "build" for a run in one heading, and the guard reds.

## Outcome

Gap: every top action's row drew both a plain `a.why` link to
`#findings` and `renderWhyRanked`'s "Why #N" disclosure -
two "why" controls. Headings mixed "run"/"build"/"capture" for one
concept ("What this **capture** supports" against "This **run**
names..." elsewhere) and "chain"/"critical path" for another.

Close: `docs/design/styleguide.md` §6e.2 adds the terminology matrix
(concept, word, rejected synonym, where measured). `actionRow`
(`decision.js`) draws the plain `why` link only when `whyBlock` is
null (`UX-194`'s dead-control rule) - one control per action.
`views.js` and `bga/schemas.py`'s reader-facing `question`/heading
strings that said "build"/"capture" for the run now say "run" (7
sites). `tests/unit/test_a_reader_never_sees_the_register.py` gains
`test_no_rejected_synonym_in_a_heading`, parsing the matrix table
itself rather than a second copy of the word list:

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_reader_never_sees_the_register.py tests/unit/test_a_new_control_class_lands_declared.py -q
22 passed
```

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `"What this run supports"` -> `"What this build supports"` | `test_no_rejected_synonym_in_a_heading[golden]`, `[scale]` | 2 failed |
| restore the plain `a.why` link unconditionally | `test_every_measured_class_is_in_the_registry` | 1 failed |

Not fixed: the schema's 651 `description` fields (the `?` door's
"describe()" output) still say "build"/"capture" ~49 times; `chain`
survives in four `decision.js`/`views.js` labels - renaming them adds
6 words, over §3e's `macro_micro` volume cap
(`test_the_page_has_a_volume_budget.py`). Both named in the matrix's
"measured on" column rather than swept.
