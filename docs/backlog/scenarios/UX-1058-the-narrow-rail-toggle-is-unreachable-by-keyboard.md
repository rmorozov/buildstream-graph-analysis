# UX-1058: the narrow-rail fold toggle is a click-only `<p>`, unreachable by keyboard

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 143's walk (`10cde1d2`) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_keyboard_journey_reaches_every_chapter.py` (`TestTheNarrowRailToggleIsReachableByKeyboard`)

## Motivation

Measured on `10cde1d2`, `app.js`'s `foldOnNarrow` (`UX-254`), at
<=60rem / 390x844: the rail collapse toggle `p.toc-title "Sections
▸"` carries a click listener only. It has no `tabindex`, `role`, or
`aria-expanded`, so a keyboard-only reader at 390 cannot reach or
operate it - a forward Tab walk skips over it entirely.

## Decomposition

Input classes: <=60rem/narrow width with the fold closed, with it open,
Tab arriving at the toggle from either side, Enter and Space activation.

## Required Fix

`p.toc-title` becomes a real control: `role="button"`, `tabindex="0"`,
`aria-expanded` tracking the fold state, and a `keydown` handler for
`Enter`/`Space` alongside the existing click listener, in
`bga/viewer/app.js`.

## Decision

```text
Route:     build the rail title as a native `<button type="button" class="toc-title">` in nav.js; it gets Tab, Enter and Space for free. foldOnNarrow (app.js) sets `aria-expanded` and makes the button `disabled` at wide width, so wide width gains no dead tab stop.
Rejected:  role, tabindex and a keydown handler on the `<p>` (reimplements the button; mechanism before guard).
Files:     bga/viewer/nav.js, bga/viewer/app.js (foldOnNarrow only), bga/viewer/style.css (button reset; §6d resting look), tests/unit/test_a_keyboard_journey_reaches_every_chapter.py (a 390x844 class)
Guard:     at 390x844 a forward Tab walk (browser.py steps) reaches .toc-title, then Enter flips data-folded and aria-expanded.
Mutation:  change the element back to `p`: Tab skips it and the guard reds.
Class:     product
```

## Out of Scope

The rail's own disclosure mechanics (`UX-1046`); any other narrow-width
control.

## Acceptance Test

At 390x844, a keyboard journey reaches `p.toc-title` by `Tab` and
toggles the fold with `Enter`. Mutation: remove the `keydown` handler,
and the guard reds.

## Outcome

**Gap measured.** `.toc-title` was `<p>` with a click listener: no tab
stop, no `aria-expanded`. The new guard, run on the base `nav.js` with
the element set back to `p` (below), reds: Tab never reaches it in 40
stops at 390x844.

**Close measured.** `nav.js` builds `<button type="button"
class="toc-title">`; `foldOnNarrow` sets `aria-expanded` and `disabled`
at wide width; `style.css` puts `button.toc-title` in the quiet grade
(§6d, no declared weight, so the title is 400 not 600) and drops the
`p` look. Registry row `button.toc-title` (§3c) and
`docs/design/rendered-strings.json` (+1 label "Sections", role button)
follow. Selector (`dev_touching.py --base 45859a39`, 100 files, `-n 2`):
10693 passed, 25 failed; the 3 mine (control-class registry, 3x
sentence-case labels) fixed and re-run with resting-appearance,
keyboard, pointer-travel, two-panes: 112 passed. The other 20 failures
are outside the viewer (context map, tiers, process documents,
junction-cost, ...) and were not compared against the base.

| mutation | reddened | count |
|---|---|---|
| `createElement("button")` -> `("p")` in `toc()` | `TestTheNarrowRailToggleIsReachableByKeyboard` | 1 failed |

Reverted from a copy; the file then passed (10 passed).
