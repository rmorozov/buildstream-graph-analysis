# UX-1056: navigating back after an in-page reveal does not re-fold the chapter

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** round 143's walk (`10cde1d2`) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_back_after_a_reveal_re_folds.py

## Motivation

Measured on `10cde1d2`, `macro_micro`, 1440x900, through `tests/browser.py`:
clicking `a[href="#graph_summary"]` opens its chapter and scrolls to it; a
following `history.back()` neither closes the chapter nor restores the
scroll position:

```text
                 scrollY   open chapters
initial              0            6
after click       8,022          30
after back()      8,230          30
```

`nav.js` reveals a chapter fold on a fragment click (`UX-667`, `UX-1015`)
but installs no `popstate` handler; the browser's own back navigation
changes `location.hash` without notifying the fold state, so the page
looks as if the user were still mid-reveal.

## Decomposition

Input classes: back after a fragment click into a folded chapter, back
after "Expand all", back with no prior reveal (a no-op), back after two
successive fragment clicks (which chapter re-folds).

## Required Fix

A judgement call on what "back" should mean here is needed before a fix
is scoped: re-fold to the state before the reveal (requiring a stack or
a snapshot of `data-open` at click time), or re-fold to the fold's
resting default regardless of prior state. `nav.js` gets a `popstate`
listener that reads `location.hash` and applies whichever rule is
chosen; scroll position follows the same rule.

## Decision

```text
Route:     save the fold state in the history entry. In app.js's delegated `a[href^="#"]` click listener, before the reveal, `history.replaceState({folds: open chapter ids, scrollY}, "")`. A `popstate` listener restores those folds (chapters.js setOpen) then scrollTo(scrollY), and sets a flag so the hashchange handler skips its re-reveal. Two back() calls unwind two clicks with no stack of our own.
Rejected:  re-fold to the resting default (drops folds the reader opened; after "Expand all" it would re-fold everything) · our own stack (duplicates what history holds).
Files:     bga/viewer/app.js, bga/viewer/chapters.js (snapshot/apply pair), bga/viewer/viewstate.js and app.js's `replaceState(null, …)` calls (must pass `history.state` or they wipe the snapshot), tests/unit/test_back_after_a_reveal_re_folds.py. Not nav.js.
Guard:     through tests/browser.py on macro_micro at 1440x900: click #graph_summary then back(): open chapters equal the initial count (6) and scrollY 0; click twice then back() once: the state after the first click returns.
Mutation:  remove the popstate listener (open stays 30, reds); restore viewstate.js's `replaceState(null…)` (the two-click case reds).
Class:     product
```

## Out of Scope

Forward/replace navigation; multi-level chapter nesting beyond what
`nav.js` already models.

## Acceptance Test

The journey above (`click #graph_summary`, `history.back()`): the
chosen rule states an expected `open chapters` count and `scrollY`
after `back()`, and a guard checks it. Mutation: remove the `popstate`
listener, and the guard reds.

## Outcome

**Gap measured.** The guard's own journey on `b8072cd7`'s `app.js` and
`viewstate.js` (`measure.py base`, scratchpad; `macro_micro`, 1440x900,
`Browser.journey`); "sections" is the Motivation's "open chapters" (the
`[data-section]` outside a fold), "chapters" the `data-open="true"` boxes:

```text
step              scrollY  chapters  sections
initial                 0         1         6
first (#graph_summary)  7,952     2        30
second (#confidence)   22,882     3        38
back_once               7,952     3        38
back_twice              8,160     3        38
rail_back               8,115     3        38
shut_back               7,907     3        38
```

**Close measured.** The same journey on this commit:

```text
step              scrollY  chapters  sections
initial                 0         1         6
first                   7,952     2        30
second                 22,882     3        38
back_once               7,952     2        30
back_twice                  0     1         6
after_a_rewrite             0     1         6
rail_back                   0     1         6
shut_back               6,633     1         6
expanded / _back   36,582 / 37,165  7 / 7   67 / 67
```

`test_back_after_a_reveal_re_folds.py`: 7 passed in 5.35s (4.95s setup).
Selector (`dev_touching.py --base b8072cd7 --list`, 92 files, `-n 2`):
2857 passed, 12 skipped, 1 failed - `test_the_tiers_are_a_partition.py`
asks for the new browser file's `tests/tiers.py` row (the orchestrator's).
The 15 browser files of the selection, `-n 2`, after the journey rework:
201 passed.

**Mutation table** (`mutate.py`, scratchpad; restored from copies):

| mutation | reddened | run |
|---|---|---|
| M1 `popstate` listener renamed away | one-click, two-click, rewrite, rail, re-reveal | 5 failed, 2 passed |
| M2 `viewstate.js` back to `replaceState(null, …)` | rewrite, rail | 2 failed, 5 passed |
| M3 re-fold to the resting default `["decide"]` | two-click, Expand all | 2 failed, 5 passed |
| M4 `scrollRestoration` left `auto` | one-click, two-click, rewrite, rail | 4 failed, 3 passed |
| M5 snapshot listener in the bubble phase | rail | 1 failed, 6 passed |
| M6 `hashchange` skip removed | re-reveal | 1 failed, 6 passed |

**Not in the Decision** (for the deviation line): three things, each held by a
row above: `history.scrollRestoration = "manual"` once a snapshot is
written (Chrome's own restore lands after `popstate` and overrode it:
7,952 read at `popstate`, 22,340 two frames later); the snapshot is a
capture-phase listener (a rail view link reveals in `nav.js`'s own
listener, before the document's); the flag is `history.state.folds`
itself rather than a variable. `tests/cdp.mjs`'s journey reads now
`awaitPromise`, and links follow a real `Enter`: in the shared tab at
Chrome's 50-entry cap an entry added without user activation is pruned
first, and a scripted `click()` lost `e0` (measured: `-n 2`, 5 errors).
After "Expand all" the restored `scrollY` drifts 583 px
(`content-visibility` estimates); not asserted.
