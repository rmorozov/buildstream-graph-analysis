# UX-672: a blocked pop-up's refusal never renders

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-451 (the refusal leaves the column), UX-198 | **Serves:** anyone whose browser blocks the Perfetto tab | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
Open timeline in Perfetto, pop-up blocked
  rail after 6 s     "opening ui.perfetto.dev — sent tab to tab, not uploaded…"
  the error's "direct link below"   a[href="#"], hidden
  "did not open"     absent from body.innerText
  console            uncaught at app.js:455 → perfetto.js:143
```

The handoff has a refusal sentence and a direct link for exactly this
case, and neither reaches the page; the reader sees "opening" forever
and the console sees an exception — the class `UX-334`'s guard holds
for the served page, on a path the guard's fixtures never take.

## Required Fix

The blocked case renders its sentence and a real `href` to the
trace, the exception is caught where the pop-up is opened, and the
console guard's fixture includes a blocked `window.open`.

## Out of Scope

- The handoff's happy path — verified working.

## Acceptance Test

With `window.open` stubbed to return `null`: the refusal sentence and
a non-`#` link render, zero console errors. Mutation: rethrow — red.
