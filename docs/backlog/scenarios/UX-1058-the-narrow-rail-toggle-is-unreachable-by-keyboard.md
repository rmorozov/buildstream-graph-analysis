# UX-1058: the narrow-rail fold toggle is a click-only `<p>`, unreachable by keyboard

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 143's walk (`10cde1d2`) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Out of Scope

The rail's own disclosure mechanics (`UX-1046`); any other narrow-width
control.

## Acceptance Test

At 390x844, a keyboard journey reaches `p.toc-title` by `Tab` and
toggles the fold with `Enter`. Mutation: remove the `keydown` handler,
and the guard reds.
