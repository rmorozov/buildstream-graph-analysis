# UX-1016: every focusable control wears one focus ring, and a keyboard journey reaches every chapter

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.8 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

**Guard:** test_a_keyboard_journey_reaches_every_chapter.py

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
:focus-visible ring designed for     button only
a, input, select, summary            the browser's auto outline
```

## Decomposition

Input classes: links, buttons, inputs, `select`, `summary` and table cells; both fixtures; light and dark. The journey extends reading the page top to bottom into doing it with the keyboard alone.

## Required Fix

One `:focus-visible` rule in `bga/viewer/style.css`, 2px accent, on `a`, `button`, `input`, `select`, `summary` and focusable `[tabindex]`. Tab order follows reading order; Escape leaves table focus and returns focus to the control that opened it.

## Out of Scope

Roving tabindex inside tables; skip links beyond the one the page has.

## Acceptance Test

`tests/unit/test_a_keyboard_journey_reaches_every_chapter.py`, booted: Tab from the top reaches every chapter's fold, opens it with Enter, enters and leaves table focus with Escape, and every stop reads the same computed outline. Mutation: scope the ring back to `button`, and the link stop reds.

## Outcome

**Gap measured.** Before this item: `button:focus-visible` was `style.css`'s
only focus ring rule — `test_the_selector_names_every_focusable_class`
against the un-mutated CSS shows the same:

```text
selector classes before   {button}
```

**Close measured.** `python3 -m pytest
tests/unit/test_a_keyboard_journey_reaches_every_chapter.py -q`:

```text
7 passed in 8.44s
```

Booted on `macro_micro`: `Tab` from a fresh load reaches every non-first
chapter's rail fold in declared order (`change, time, machine, elements,
believe, run`), each showing a 2px solid `--accent` ring; `Enter` on a
reached fold flips `aria-expanded` `false -> true`; a served page's
`Tab`+`Enter`+`Escape` enters table focus and returns focus to the same
control that opened it (`data-expand` unchanged across the round trip).

**Mutation table.**

| guard | mutation | reddened | count |
|---|---|---|---|
| `TestOneFocusVisibleRuleCoversEveryFocusableClass` | scope the `:focus-visible` selector back to `button` alone | selector-class clause | 1 of 2 rule tests |
| `TestEveryFocusableClassShowsTheRingForReal` | same mutation | the `A` stop's ring (`outlineStyle` `auto`, not `solid`) | 1 |

2 of 7 clauses reddened by the mutation the Acceptance Test names; the
other 5 (chapter order, Enter, Escape/table-focus) are unaffected by a
CSS-only mutation, as expected — they guard the DOM/JS mechanism, not
the ring.

Deviation: none from the Required Fix; the new browser guard was tiered medium on the merge (`f71a4831`).
