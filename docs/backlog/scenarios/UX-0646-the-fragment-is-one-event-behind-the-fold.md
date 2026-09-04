# UX-646: the fragment is one event behind the fold

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-211 (URL state), UX-642 (which measured it and declined it) | **Found by:** round 87, track D, while guarding the fold round trip | **Serves:** anyone who opens a fold and copies the link | **Topic:** viewer

## Motivation

`wireViewState` writes the fragment on the bubbling `click`. A
`<summary>` flips its parent's `open` **after** that dispatch, and the
`toggle` listener beside it never fires because `toggle` does not
bubble. So every fragment describes the fold state as it was one
interaction ago.

Measured on the exported `macro_micro` page, hitting both fold
conventions equally so it is the event and not the attribute:

```text
click structured summary, then declared summary   o=restructuring.0.edges
click declared summary, then structured summary   o=evidence
```

Each fragment names the fold opened *before* the one just clicked. A
reader who opens a fold and copies the link immediately hands over a
link without it — which is the failure `UX-211` exists to prevent, and
`UX-642` only appeared to fix. `UX-642`'s guard reaches its assertion
by clicking a second summary, and says so at the site.

`document.body.click()` does not rescue it: `wireViewState`'s root is
the report container, not `body`.

## Required Fix

The fragment is written after the state it describes has changed —
either by listening where `toggle` actually fires (per `details`, not
delegated) or by deferring the write past the dispatch that flips it.
Whichever, the guard is the one `UX-642` could not write: open one
fold, read the fragment, and find that fold in it, with no second
click.

## Out of Scope

- The attribute the two producers disagree about — `UX-642`, done.
- Any other control's timing. Every other control this writes on
  mutates before the click dispatches; `details` is the exception, and
  the row that widens this to a survey is not this one.

## Acceptance Test

On both fixtures: open exactly one fold, capture the fragment, and it
names that fold. A mutation restoring the delegated-`click`-only write
reddens it.

## Outcome (round 88, 2026-09-04) — 🟢 Done

**Premise:** held, and the mechanism is the one the Motivation names.

### The gap, measured

Served, `macro_micro`, Chromium, at `a5bca33`: open one fold whose key
no other fold shares, and read the fragment. Nothing else touched.

```text
before               #~c=decision&v.elements=All+elements&n.binary_cost=…
after one summary    #~c=decision&v.elements=All+elements&n.binary_cost=…
after a second       #~c=decision&…&o=evidence
```

`o=evidence` is the *first* fold, arriving on the second click: the
`<summary>` flips `open` after the dispatch the writer ran on, and the
`toggle` listener beside it never fired - `toggle` does not bubble.

### After

```text
after one summary    #~c=decision&…&n.binary_cost=25%3Acalls&o=evidence
```

Both halves of the Required Fix, each covering what the other cannot.
The delegated write happens **one turn after** the dispatch that flips
`open`, not on it — one write per burst, so a filter box's keystrokes
do not each walk every table — and `toggle` is heard **in the capture
phase**, the only place a root hears an event that does not bubble. The
deferral covers a fold the reader clicked, the capture listener one the
reader did not.

Deferred rather than written twice, and that is a measurement: with a
write on the event *and* a turn later, `test_the_rail_takes_a_step.py`
went red after its own 97-press walk. Chrome throttles same-document
history ops and the second write spent that budget; 12s of idle
restored it, which is what named the cause.

`tests/unit/test_the_fragment_keeps_up_with_the_fold.py`, **8 passed**
in 4.50s (MEDIUM, tiered on landing): two served fixtures, four node
clauses holding the timing where there is no Chrome.

`UX-642`'s guard loses the workaround it declared — a second summary
clicked to reach its assertion. One click and a settle now:
`test_a_fold_stays_open_in_the_link.py`, **12 passed** in 1.75s, red
under M2 below, which says the removal was earned.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M2 | the delegated-`click`-only write restored (four names, bubble phase, `write` not `settle`) | 5 failed / 3 passed here (`[] == ['evidence']` served), 2 in `UX-642`'s file, 1 in `UX-647`'s |
| M3 | the capture-phase `toggle` registration dropped | the unclicked-fold clause served (`['evidence'] == ['evidence', 'utilisation.buckets']`) and its node twin — 2 failed / 26 passed |
| M4 | the per-burst coalescing dropped (`if (queued) return`) | `…defers_one_write` alone, `3 == 1` |

M3's first draft did not discriminate: `UX-647`'s
`…document_is_what_hears_the_events` asserted the exact four-name list,
so dropping the `toggle` registration reddened a clause about *where*
the writer listens. It reads the three delegated names as a subset now.

The node clause for `toggle` cannot see the *phase* — the DOM shim
ignores `addEventListener`'s third argument — so the capture claim is
held by the served clause, where nothing but it can write.

### Deviation from the Required Fix

None. The Fix offered either mechanism; both landed - `UX-647`'s rail
measurement needs the deferral, a fold nothing clicked needs the
capture listener. The `viewstate.js` change is in `UX-647`'s commit,
the item whose acceptance could not go green without it.

```text
make test-touching   20 file(s) selected · 583 passed, 3 skipped in 39.99s
make lint            ruff + PyMarkdown, All checks passed!
make test            26 failed, 6931 passed, 125 skipped in 263.56s - 19
                     `bst` ("Cache too full", pre-existing), 5 the two index
                     rows a track does not move, 2 `fixing-guide.md`'s
                     derived test-file count. Both are the orchestrator's.
```
