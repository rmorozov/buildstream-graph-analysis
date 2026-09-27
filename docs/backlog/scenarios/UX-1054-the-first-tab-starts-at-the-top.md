# UX-1054: the first Tab from a fresh load starts at the top of the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** UX-1046's verifier (round 143) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on the branch at `18afdebb` (the same at `5f967f09`): `macro_micro` exported by
`pages.export_uri`, driven by `tests/cdp.mjs --journey` at 1440x900 (scratch
`tabs3.py`). At load `scrollY` 0, `location.hash` "", `activeElement` BODY,
`nav.toc.scrollTop` 0. The first laid-out focusables in document order, then
what the first `Tab` actually lands on:

```text
document order   SELECT.top-n, "← Prev", "Next →", INPUT, rail "▾ What should I do?",
                 "What to fix first", "What this run supports", ...
first Tab        "What this run supports"   (6 focusables skipped)
```

Cause, isolated in the same journey after first focusing BODY (which resets the
starting point):

```text
then nothing                                          first Tab: SELECT.top-n
then aria-current="location" + data-current set by hand  first Tab: SELECT.top-n
then first a[data-toc].scrollIntoView({block:"nearest"}) first Tab: "What this run supports"
```

`nav.js` `scrollspy()`'s `mark()` calls `link.scrollIntoView({block: "nearest"})`
on the marked rail link (`UX-667`) at landing; Chromium moves the sequential
focus navigation starting point to the scrolled element, so a keyboard reader's
first `Tab` begins after "What to fix first" and never meets the page header's
controls, the rail's steps, the jump box or the decision row. A forward walk
reaches them only by wrapping the whole page.

## Decomposition

Input classes: fresh load with no fragment, fresh load with a fragment, a mark
that moves while nothing is focused, a mark that moves while a control has focus.

## Required Fix

The rail follows the mark without moving the focus starting point: scroll the
rail itself (`nav.scrollTop` from the link's offset, clamped the way
`block: "nearest"` would) instead of `Element.scrollIntoView`, in
`bga/viewer/nav.js` `scrollspy()`. `test_the_rail_is_a_source_list.py`'s
"mark stays in view" clause holds unchanged.

## Acceptance Test

A keyboard journey with **no** explicit start (unlike
`test_a_keyboard_journey_reaches_every_chapter.py`'s `_START_AT_THE_TOP`): the
first `Tab` from a fresh load lands on the first focusable in document order,
and a forward walk's rail stops include every chapter id, `decide` first.
Mutation: restore `link.scrollIntoView({block: "nearest"})`, and the first-stop
clause reds.

## Outcome

Not started.
