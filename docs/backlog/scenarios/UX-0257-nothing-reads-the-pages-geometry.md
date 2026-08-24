# UX-257: nothing reads the page's geometry, so "it does not overlap" is an opinion

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-254 (the layout worth checking) | **Serves:** the maintainers; R1 through the defects it would catch | **Topic:** guards

## Motivation

The user asked to *"recheck that information on page won't overlap"*.
That recheck was done by hand for `UX-254`, in a real browser, and
found no overlaps at three viewports — but **it cannot be a guard
today**, and the reason is worth writing down.

The viewer's test harness is a hand-rolled DOM shim in node. It has no
layout engine: no `getBoundingClientRect`, no box model, no cascade. It
is why `UX-235` found `prepend` implemented as `append` and every order
guard reading a reversed document — *"the page was never wrong; the
instrument was."*

So every geometric claim this repository makes about the viewer —
"the contents take 573px", "nothing overlaps", "the first content is
above the fold" — is measured by hand and then **not held by anything**.
`UX-254` will add a layout that has real geometric preconditions, and
those preconditions will be exactly as unguarded as the ones it
replaces.

`UX-213` is the precedent that makes this urgent rather than tidy: a
guard that only runs on one machine is the failure that item was filed
against, and a measurement that runs on no machine is one step worse.

## Required Fix

The decision first, because it is a real trade and not obvious:

1. **Decide the instrument.** A real browser (Chromium is already
   assumed by nothing in CI; Playwright would add an install step and a
   browser download) versus keeping geometry unguarded and holding the
   *CSS contract* instead — the grid areas, the sticky offsets, the
   `overflow` on the rail, the breakpoint — which is checkable
   everywhere and weaker.
2. Whichever is chosen, **say which claims it does not cover**. A
   CSS-contract guard cannot see two boxes overlapping; a browser guard
   in one job cannot see the other Python versions' pages.
3. If a browser is chosen: an overlap scan across a stated set of
   viewports, and the set is part of the contract.

## Out of Scope

- Pixel screenshots as a regression baseline. They fail on font
  rendering and would be muted within two rounds, which is worse than
  no guard.
- Waiting for `UX-254`. The instrument decision is what unblocks
  guarding it, so this item is the one that has to be argued.

## Acceptance Test

The decision is argued and recorded; whichever instrument is chosen
reddens on a deliberate overlap or a deliberately broken CSS contract,
and the claims it cannot see are named in the same place.

## Outcome

**Decided: a real browser, and it costs nothing to add.**

The trade the item posed assumed a browser meant Playwright — a package
and a browser download, in a repository whose test dependencies are
`pytest` and `jsonschema`. Measured rather than assumed, that premise
is false: **node 22 has a built-in `WebSocket` and `fetch`, and the
DevTools protocol needs nothing else.** `tests/cdp.mjs` is the entire
client, forty lines, and `node` is already required by every viewer
guard. The CSS-contract alternative stays where it is
(`test_the_report_has_two_panes.py`) and is now the weaker of two
instruments rather than the only one.

The cost is a Chrome binary. `tests/browser.py` finds one by the usual
names or `BGA_CHROME`; where there is none these guards skip, and the
reason is **declared in `tests/conftest.py`'s census** so that "no
browser here" is a fact the suite reports rather than a silence
(`UX-235`).

**It found something on its first run.** At 390x844 the scan reported
32 overlapping sibling pairs. Two were real measurement errors of my
own and worth recording, because both are the same class of defect this
item exists to prevent:

- `getBoundingClientRect()` on a **wrapped inline** element returns the
  union of its per-line boxes — a rectangle covering text that is not
  there. Two wrapped links reported a 141x18 overlap while touching
  nothing. Fixed by comparing `getClientRects()` per line.
- Out-of-flow boxes (`position: absolute`) are *placed* over other
  boxes deliberately — a copy button over a command. Reporting those is
  how an overlap scan gets muted.

After both fixes: **zero overlaps at all three viewports**, with 20+
boxes scanned at each, so "no overlaps" is not "nothing rendered".

**What it holds**, at 1440x900, 1280x800 and 390x844 — the viewport set
is part of the contract, and dropping the narrow one makes the suite
blind to the sideways-scroll defect it was added for:

```text
no two siblings share pixels          (with named, reasoned exemptions)
the heading is above the reading column, which starts in the first half-screen
the rail is left of the text
the document never scrolls sideways
an anchor lands clear of the sticky heading
```

**Four mutations, four reds:** a `-30px` margin pulling sections over
each other; `display: block` collapsing the two-pane grid; a
`min-width: 1600px` table forcing sideways scroll; and
`scroll-margin-top: 0` dropping the anchor under the heading.

**What it cannot see**, named in the file itself: any machine with no
Chrome; font differences, which is why every assertion is a threshold
with slack and why screenshot baselines stay declined; and the served
page's dynamic halves, since this loads the exported single file.
