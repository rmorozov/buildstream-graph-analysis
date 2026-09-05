# UX-642: a structured fold forgets it was open

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-211 (URL state), UX-318 (the rabbit hole announces its depth) | **Found by:** round 87, while measuring the parallelism block | **Serves:** anyone who shares a link to a report they were reading | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome (round 87, 2026-09-04) — 🟢 Done

**The premise held, and one sentence of it did not.** The populations,
counted in Chromium on the two committed fixtures before the fix:

```text
                     details  data-fold  data-fold-path  both
golden                    25          5               5     0
macro_micro               52         16              12     0
```

Disjoint — no fold anywhere carries both — so reading one attribute
drops the other half whichever is read. But the Motivation's "the
larger population is the one that does not work" is **wrong on these
fixtures**: `data-fold-path` is 12 against `data-fold`'s 16 on
`macro_micro` and 5 against 5 on `golden`. The defect is that the two
halves are disjoint, not that the broken half is bigger. Fifteen and
twenty-four `details` on the two pages carry *neither* attribute —
`folded()` called with `path = null` — and stay uncapturable, which is
right: a fold with no identity has nothing to put in a link.

### After

`viewstate.js` reads both, `data-fold` first, at both sites — `FOLDS`
and `foldKey`, one definition each for the capture and the restore.
`structured.js` is untouched: `data-fold-path` is the payload path the
fold holds and is the stabler identity.

The acceptance test, on the exported `macro_micro` page in a real
Chromium — open a structured fold, take the fragment the page wrote,
open it as a **second document** (a second exported copy; a
fragment-only navigation keeps the DOM and proves nothing):

```text
opened   restructuring.0.edges
hash     #~v.elements=All+elements&n.binary_cost=25%3Acalls&o=restructuring.0.edges&c=
reload   open: ["restructuring.0.edges"]      fresh: true
```

`tests/unit/test_a_fold_stays_open_in_the_link.py`, **12 passed** in
2.2s (MEDIUM, tiered on landing).

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| N1 | capture selector back to `details[data-fold]` | 6 failed / 6 passed, both browser clauses among them |
| N2 | restore selector back to `details[data-fold]` | 4 failed / 8 passed — **every capture clause stayed green**, which is what says the two sites are covered apart |
| N3 | `foldKey` reads `data-fold-path` only | 5 failed / 7 passed, the declared-fold clauses among them |
| N4 | capture stops filtering on `node.open` | `…nobody_opened_is_not_in_the_link` alone |
| N5 | restore opens every identified fold (`open.has(key)` dropped) | `…leaves_the_rest_shut` alone |
| N6 | `structured.js` sets `data-fold` beside its path | `…producers_still_disagree`, `…shares_none` (both: 12) |
| N7 | both loads at one URL | `…in_a_fresh_document`, on `fresh` |

N6 is recorded because the guard it targets **did not discriminate at
first**: it read "which attribute names this fold" as an either/or, so
a fold carrying both still answered `data-fold-path` and the clause
stayed green under the mutation. It now reports the list of attributes
present and asserts both singletons.

### A second defect, measured and not fixed

The fragment is one event behind the fold. `wireViewState` writes on
the bubbling `click`, and a summary's activation flips `open` *after*
that dispatch; the `toggle` listener beside it never fires, because
`toggle` does not bubble. So opening a fold and pasting the link
immediately hands over a link without it — measured on `macro_micro`,
both conventions alike:

```text
click structured summary, then declared summary   o=restructuring.0.edges
click declared summary, then structured summary   o=evidence
```

Out of this row's Required Fix, which is the attribute. Worth a row of
its own: the guard here clicks a second summary to get past it, and
says so.
