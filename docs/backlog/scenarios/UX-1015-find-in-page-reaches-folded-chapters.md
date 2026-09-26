# UX-1015: find-in-page reaches text inside a folded chapter

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.11 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
chapters folded at rest              5 of 6
folded chapter's sections           display: none (`style.css:487`)
Ctrl+F on a folded section's text    no match
```

## Decomposition

Input classes: macro_micro and golden; a folded and an open chapter; find, a fragment link, the rail, the fold control and print. The journey extends finding a word on the page into landing on it inside a folded chapter.

## Required Fix

Drop the `section.chapter[data-open="false"] > section[data-section]` rule in `bga/viewer/style.css`; a folded chapter's sections take `hidden="until-found"`. Exclude `[hidden]` from the `content-visibility: auto` rule, and add a print rule that shows every section. `setOpen` in `bga/viewer/chapters.js` becomes the single setter of `data-open`, `hidden` and `aria-expanded`; a `beforematch` listener calls `revealChapter`. §6c's platform list gains the row.

## Out of Scope

The page's own "Jump to..." box; browsers without `until-found` keep the fold as today.

## Acceptance Test

`tests/unit/test_find_in_page_reaches_folded_chapters.py`, booted: find, a fragment link, the rail and fold controls, and print each reach a folded section's text through `setOpen`, and `aria-expanded` agrees after each. Mutation: restore the `display: none` rule, and the find case reds.

## Outcome

Not started.
