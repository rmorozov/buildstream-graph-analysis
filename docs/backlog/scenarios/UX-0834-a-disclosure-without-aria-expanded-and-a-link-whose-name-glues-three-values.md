# UX-834: a disclosure without aria-expanded, and a link whose name glues three values

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-716 (every control has a resting appearance), UX-532 (the twin) | **Found by:** round 115, the design review | **Serves:** a keyboard or screen-reader user | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

Two controls differ from every other of their class:

```text
button.twin-toggle "as table"   drawings.js:274   aria-expanded absent (collapse, json-toggle, chapter-open all carry it)
a.path-box                      views.js:1033     three display:block spans, no separator → accessible name "toolchain.bst0.0 simport"
```

## Required Fix

In `bga/viewer/drawings.js` `twin-toggle` carries `aria-expanded`, flipped on the same click
path; in `bga/viewer/views.js` `a.path-box` gets `aria-label` "<element>, <duration>, <kind>".

## Decomposition

Input classes: a drawing with a twin, a critical path with one and
with fifteen boxes; the journey is the timeline handoff's keyboard path.

## Out of Scope

- The twin's default state — closed is right (§2a).

## Acceptance Test

`test_every_control_has_a_resting_appearance.py` extended: every
`button` that toggles a sibling's `hidden` carries `aria-expanded`;
`a.path-box` accessible name contains a separator; mutation: drop
either — red.
