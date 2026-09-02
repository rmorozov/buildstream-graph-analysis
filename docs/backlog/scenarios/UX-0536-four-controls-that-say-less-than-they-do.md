# UX-536: four controls that say less than they do

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-280 (the Markdown preference), UX-223 (the accelerators), UX-334 | **Serves:** the keyboard and screen-reader reader | **Topic:** viewer

## Motivation

From the 782-control census, the four that are reachable and usable
but say less than they do:

```text
input.copy-markdown "as Markdown"     29 boxes for one localStorage preference; 1 of 29 changes on a click
button.collapse ▾/▸                   65, no accessible name, default type=submit     nav.js:187-191
[ ] / Escape accelerators             announced nowhere                                nav.js:587-594, app.js:998
element_join_coverage                 zeros under a two-plane heading on a one-plane run   sections.js:370-420
```

## Required Fix

One preference, one control (the Markdown box moves to the rail or
mirrors across all 29); `aria-label` and `type="button"` on the
collapse buttons; the accelerators listed beside the Prev/Next
controls; `element_join_coverage` says "Plane 2 not captured" where
the evidence line already does.

## Out of Scope

- A full accessibility pass — `UX-334`'s a11y rider carries the
  ~200-issue census; these four are the ones a control walk hit.

## Acceptance Test

One click on any Markdown box changes all 29; the console/a11y
guard reports zero unnamed buttons; the one-plane page's join
section carries the not-captured sentence.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

Both committed fixtures, exported and booted at 1440x900, chapters
opened. The Markdown box driven from a **known** start — every box
unchecked first, since `Browser(chrome)` reuses one Chromium and the
previous drive's `localStorage` preference would otherwise be inherited:

```text
fixture       collapse   unnamed   type!=button   boxes   one click changes
golden              46        46             46      14            1 of 14
macro_micro         66        66             66      29            1 of 29

accelerators  no hint anywhere; the labels read "Previous section" /
              "Next section" and the [ ] keys are announced nowhere
```

The fourth through the section renderer, the only instrument reaching
the state (see the deviation): `{joined_elements: 0, plane1_elements:
11, plane2_elements: 0}` drew `section, h2, dl, dt, dd, span` — six
zeros under a heading naming two planes.

### After

```text
fixture      unnamed  type!=button  one click changes  promising Markdown
golden             0             0           14 of 14            14 of 14
macro_micro        0             0           29 of 29            29 of 29

step controls  "[ ] step" beside them; labels "Previous section, or the
               [ key" / "Next section, or the ] key"
zero coverage  -> section, h2, p  "Plane 2 not captured for this run, so
   the two planes have nothing to agree on — these are not zeros that
   were measured."  ·  data-empty="true", so the rail agrees
```

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| Q1 | the collapse button's `aria-label` removed | `…is_unnamed`, 2 — `66 == 0` |
| Q2 | its `type="button"` removed | `…is_a_submit`, 2 |
| Q3 | one box stops telling the other 28 | `…one_preference_is_one_state`, 2 — `1 == 29` |
| Q4 | the `[ ] step` hint removed | `…accelerators_are_announced…`, 2 |
| Q5 | the zero join renders its zeros again | `…carries_the_sentence` + `…draws_no_zeros…`, 2 |

Each reddens its own clause and no other.

**One guard of mine did not discriminate, and it was the whole page.**
The mirror's first version wrote `addEventListener(MIRROR, label)` —
`label` as a value **above** its own `const label = …`, a
temporal-dead-zone `ReferenceError` at render time. The page booted to 0
sections and 0 inputs, the drive read `0 collapse buttons, 0 unnamed`,
and that *passes* a clause reading "no button is unnamed". Every clause
now carries a population floor (`collapse > 20`, `boxes > 10`).

### Deviation from the Required Fix

The Markdown box **mirrors** rather than moving to the rail; the Fix
allowed either. `element_join_coverage` is guarded through the renderer
rather than a fixture: neither committed run reaches `plane2_elements ==
0` — `golden` publishes no coverage block, `macro_micro` joins 9 of 11 —
and emptying `plane2.json`'s `by_element`, `element_attribution` and
`declared_vs_used` leaves it at 9 of 11, the join being computed from
the trace rather than from that report.

**The export size bound is 142 B over and left alone** (another track
owns it): round 80's four items add **2,305 B of page and 0 of data** to
`golden` — page 294,848 → 297,153 B, data 114,424 → 114,399 (run-path
noise) — of which this item is 1,185 B, all JS. Bound 411,000; the suite
measures 411,142.

```text
the two guard files  →  54 passed, 6 skipped in 50.70s
conformance, palette, emphasis, resting appearance, labels  →  109 in 82s
make test-touching   →  903 passed, 19 skipped (1 failed: the size bound)
make lint            →  All checks passed!
```
