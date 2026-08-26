# UX-315: every canned question's `why` renders with doubled spaces

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R1 | **Topic:** viewer

## Motivation

`bga/viewer/questions.js` builds each `why` by concatenating string
literals across lines, and every continuation begins with a space
while the previous line already ends with one:

```js
why:
  "Plane 1's element spans, aggregated - scoped to the element " +
  " plane, so Plane 2 command names cannot crowd the answer.",
```

The reader sees `the element  plane`. Measured: **13 of 13**
questions are affected, so it is the file's convention rather than
one slip, and every one of them is prose the page renders.

Found while `UX-312` was raising the page budget, and deliberately
not fixed there: the six pre-existing questions are text that item
had no other reason to touch, and "trivial and adjacent" is how a
pull request widens.

## Required Fix

The continuations lose their leading space, and a guard asserts no
`why` contains a double space — cheap, and the kind of defect that
comes back the next time someone adds a question by copying the one
above it.

## Out of Scope

- Rewording any `why`. This is whitespace; the sentences are right.
- The same pattern anywhere else. If it exists elsewhere the guard
  should widen, but that is a search, not an assumption.

## Acceptance Test

No `why` in `QUESTIONS` matches `/  /`; the guard reddens when a
continuation's leading space is restored.
