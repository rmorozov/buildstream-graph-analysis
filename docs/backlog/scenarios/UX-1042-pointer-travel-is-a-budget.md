# UX-1042: pointer travel is a budget, measured per journey

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3l | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900 and 390x844. Every hop from one control's centre to the next; Fitts' index `log2(D/W + 1)` with `W` the target's smaller side; wheel is the scroll a hop needed.

```text
journey, 1440x900                          11 elements       74               1,202
verdict -> first next step's Copy          466 px   4.4 b    534 px   4.5 b   522 px   4.5 b
rail row -> section -> ? -> JSON -> fold   1,041-2,712 px    1,117-3,002      1,117-3,284
                                           13.5-19.8 b       13.9-17.5 b      13.3-17.7 b
open every chapter from the document       684 px  12.8 b    829 px  16.1 b   829 px  16.1 b
  wheel, 1440x900                          8,067 px          8,538 px         9,521 px
  wheel, 390x844                           49,946 px         50,467 px        61,039 px
element table: filter, top-N, column,
  sort, copy (macro_micro)                 1,057 px 12.8 b
```

Every hop is `element.click()`, after `scrollIntoView({block:
"center"})` only when the target is off screen.

§3b counts clicks and §3c screens; nothing counts how far the pointer
moves between controls used together, so a control can wander across
the column (`UX-1043`-`UX-1045`) with every guard green. At 390x844
the rail is behind "Sections", so the rail journey did not run there.

## Decomposition

Input classes: both fixtures, both size classes, the four journeys
above plus the compact rail (open "Sections" first). The journey is the
rail-to-section walk §3b already takes, extended to the controls a
reader then uses.

## Required Fix

A booted guard that drives the four journeys, records per hop the
distance, the target size and the wheel pixels, and holds (a) the
x-centre spread of each control class (`button.collapse`,
`button.describe`, `button.json-toggle`, `button.chapter-open`,
`button.copy-rows`, `select.top-n`) to at most 24 px, and (b) each
journey's Fitts bits to a bound set from the measurement after
`UX-1043`-`UX-1045` land. §3l moves from proposed to binding.

## Out of Scope

Moving any control (`UX-1043`-`UX-1045`); keyboard travel (§6e.8).

## Acceptance Test

The guard, green on both fixtures at both sizes. Mutation: give
`button.json-toggle` `margin-left: auto` back after `UX-1043`,
and the spread clause reds; add a hop's worth of margin to the Copy
control and the journey clause reds.

## Outcome

Not started.
