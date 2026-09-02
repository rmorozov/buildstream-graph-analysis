# UX-527: one control has an option per element

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-368 (the query the control feeds), UX-369 (the substitution) | **Serves:** anyone asking Perfetto about one element of a large project | **Topic:** viewer

## Motivation

```text
section perfetto-questions, "Ask about element" <select>
  @14 elements       14 options
  @1,202          1,202 options      section text 26 KB
  @4,002          4,002 options      section text 86 KB
```

`questions.js:851-859` fills the control from the run's whole
population (`app.js:681`); `test_the_query_asks_about_this_run.py:201`
requires the population be *this run's* and says nothing about the
control's size. It is the only `<select>` on the page that grows
with the project, and a 4,002-entry dropdown is not a control anyone
can use.

## Required Fix

A search box over the same population (`<input list>` with a
`<datalist>` capped at the jump box's 8 results, or the jump box
itself with a "then ask" action) — the substitution and the guard's
population claim unchanged. Options rendered: the 8 that match, not
the 4,002 that exist.

## Out of Scope

- The query library's content — `UX-368`/`UX-369` own the queries.

## Acceptance Test

At 4,002 elements the control's rendered options ≤ 8 for any typed
prefix and the chosen element reaches the query; mutation: fill the
list with the population — red.
