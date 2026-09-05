# UX-668: a reader is a shape, not a hue — and the selector lives in the header

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-372 (the reader select), UX-643 (the role demotes), UX-305 | **Serves:** R1..R5, the readers the select names | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
select[data-role="reader"]    at (386, 297) inside section `decision`, "I am" + 6 options
its description               the Reader · question · leads-with table is section `readers`, 759 px below
switching to local-optimizer  promotes 9 sections, folds 58, opens 5 chapters (7,484 → 21,049 px)
computed style of [data-promoted]   border 0, background transparent — promotion has no mark; only the folding shows it
chip                          promoted h2s get "R1" in .reader-tag, 11.2 px muted
```

The user proposed moving the selector and the role descriptions to
the header and giving each role an accent. The header placement is
right (§4a: a whole-page control lives on the sticky header). Five
hues are not: §4.1 forbids a categorical series, §4.2 allows one
accent, and the CVD numbers that reserved the status tones would be
spent on roles. "My content is findable" is a shape question (§4.3),
and the shape is absent today — promotion draws nothing.

## Required Fix

Styleguide **§4 rule 7, "A reader is a shape, not a hue"**. Header
line 3: `I am [select] — <span class="muted" data-role="reader-question">Which element should I shorten first?</span>`
— one control, the panel's copy goes; the question is the role's
description, in place. `section[data-promoted]{border-left: 3px solid
var(--accent)}` plus the chip; with "anyone" every section shows its
reader chips muted, so a reader can see what each role would promote
before choosing. Zero new colors.

## Out of Scope

- Per-role hues — declined by §4.1/§4.2, with the argument above.
- The `readers` section itself — it stays as the table of who asks
  what; the header carries only the current question.

## Acceptance Test

Guard: the header contains the reader select on both fixtures;
`[data-promoted]`'s `border-left-width` ≥ 3 px; every section with a
`readers` entry renders a chip. Mutation: drop the left rule — red.
