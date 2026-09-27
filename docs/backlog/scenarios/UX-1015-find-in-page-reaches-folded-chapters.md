# UX-1015: find-in-page reaches text inside a folded chapter

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.11 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

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

**Gap measured.** Before this item, `style.css` folded a chapter with
`section.chapter[data-open="false"] > section[data-section] { display:
none; }` — a `display` rule, which hides text from `Ctrl+F` regardless
of any `aria-*` state. On the un-mutated tree this repository's own
audit found 5 of 6 chapters folded at rest on `macro_micro`.

**Close measured.** `python3 -m pytest
tests/unit/test_find_in_page_reaches_folded_chapters.py -q`:

```text
9 passed in 1.35-1.68s
```

`setOpen` is now the one writer of `data-open`, `hidden="until-found"`
and `aria-expanded`; a dispatched `beforematch` opens the whole chapter;
a section that arrives after its chapter is shut joins it shut; booted
in a real browser, a folded section computes `contentVisibility:
"hidden"` and `display` other than `"none"`.

**Mutation table.**

| guard | mutation | reddened | count |
|---|---|---|---|
| `TestTheMechanismIsThreePlaces::test_the_display_none_fold_rule_is_gone` | restore `section.chapter[data-open="false"] > section[data-section] { display: none; }` | the static source check | 1 |
| `TestAFoldedSectionIsHiddenUntilFoundOnScreen::test_a_folded_section_computes_hidden_but_not_display_none` | same mutation | `display` reads `"none"` again | 1 |

2 of 9 clauses reddened by the Acceptance Test's own mutation; the
remaining 7 (the shim-level `setOpen`/`beforematch`/late-arrival logic,
and the print/content-visibility static checks) are unaffected by
restoring the old `display` rule alone, as expected.

Deviation: `hidden="until-found"` meant five existing guards that force a chapter open had to clear `hidden` too, and `test_the_header_keeps_its_budget.py` reads `textContent` past the fold (`0de51abb`).

**Review (#295):** the print rule set `display: block !important` on
`[hidden="until-found"]` but never touched `content-visibility`, which
the platform itself sets to `hidden` on that state (HTML Standard
#hidden-elements) - so a folded section printed at zero rendered size
regardless of `display`. `style.css`'s print rule now also sets
`content-visibility: visible !important`.
`TestAFoldedChapterPrintsItsText` (new, in the same guard file) drives
`Emulation.setEmulatedMedia({media: "print"})` for real over CDP
(`tests/cdp.mjs --media=print`, `Browser.measure(..., media="print")`)
and asserts the folded section's `getBoundingClientRect().height` and
`scrollHeight` are non-zero. Mutation: drop the added
`content-visibility` line - `python3 -m pytest
tests/unit/test_find_in_page_reaches_folded_chapters.py -q -n 1 -k
print`: 1 passed, 1 failed (`contentVisibility` reads `"hidden"`,
`height`/`scrollHeight` read `0`); restored, both pass again.
