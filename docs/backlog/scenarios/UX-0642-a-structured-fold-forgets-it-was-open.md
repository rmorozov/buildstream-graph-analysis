# UX-642: a structured fold forgets it was open

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-211 (URL state), UX-318 (the rabbit hole announces its depth) | **Found by:** round 87, while measuring the parallelism block | **Serves:** anyone who shares a link to a report they were reading | **Topic:** viewer

## Motivation

View state travels in the fragment, and folds are part of it —
`viewstate.js:97` collects the open ones and writes them as `o=`. It
collects them with:

```js
root.querySelectorAll("details[data-fold]")
```

Every fold that `structured.js` builds — the nested-value folds, one
per rabbit hole — is written with a different attribute:

```js
el("details", { class: "map", "data-fold-path": path, ... })   // structured.js:182
```

`data-fold-path`, not `data-fold`. So the selector never matches them:
they are neither captured on write nor restored on read. A reader who
opens a nested fold, filters a table and hands over the link sends a
URL that restores the filter and closes the fold.

The folds that *do* persist set `data-fold` explicitly — `element.js:652`,
`sections.js:101`, `views.js:162,441`, `questions.js:812`. Two
conventions for one thing, and the larger population is the one that
does not work.

## Required Fix

One attribute names a fold's identity. Either `structured.js` sets
`data-fold` alongside its path, or `viewstate.js` reads both — decided
by which is the identity: `data-fold-path` is a payload path and is
already the stabler name.

A guard covers a fold from each producer, so the next fold added under
either convention is captured.

## Out of Scope

- Whether every fold on a 65-section page *should* be in the URL. The
  `c=` collapse set already answers that for sections; this row only
  makes the two conventions agree.

## Acceptance Test

Open a `structured.js` fold, capture the view, restore it into a fresh
render: the fold is open. A mutation to the attribute name reddens it.
