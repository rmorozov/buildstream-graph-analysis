# UX-257: nothing reads the page's geometry, so "it does not overlap" is an opinion

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-254 (the layout worth checking) | **Serves:** the maintainers; R1 through the defects it would catch | **Topic:** guards

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
