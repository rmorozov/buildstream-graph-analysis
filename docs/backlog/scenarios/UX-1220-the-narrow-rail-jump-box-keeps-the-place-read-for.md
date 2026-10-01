# UX-1220: the narrow rail jump box keeps the place read for Back, as its links do

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P3 (pre-existing): at 390 the rail jump box is outside `UX-1208`'s rule. Read at 6000, climb, jump to layer12/mod030 (or its Focus action), Back: y 0, not 6000; Forward after Focus lands at 0, not 749.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

At 390, Back after a jump-box jump or its Focus action lands on the place read before the rail opened; Forward lands on the jumped-to element.

## Out of Scope

Rail links, Expand all and a chapter press (`UX-1208`, closed).

## Acceptance Test

At 390, read at 6000, climb, jump by the box, Back: scrollY 6000; Forward after Focus: the focused element in view; a guard in a new `test_the_narrow_rail_jump_box_keeps_the_place_read.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     The jump box goes through the rail's navigation step: hoist the capture handler's body into `navigate(railed, push)` in app.js, pass it to `wireJumpBox`; `go` and `act` call it with `railed` from the rail's open state, so the place read before the rail opened is kept (UX-1208's `read`) and one entry is pushed.
Rejected:  Dispatching a synthetic click on the rail: the handler reads `event.target`, which a box result does not have.
Rejected:  A second keepPlace inside wireJumpBox: two writers of the history entry.
Files:     bga/viewer/app.js (wireJumpBox go/act, capture handler, the wireJumpBox call), tests/unit/test_the_narrow_rail_jump_box_keeps_the_place_read.py
Guard:     At 390: read at 6000, climb, jump by the box to layer12/mod030, Back gives scrollY 6000±1; then Focus action, Back, Forward: the focused card intersects the viewport.
Mutation:  Have `go` call pushState without `navigate`; Back reaches 0, red.
Class:     product
Split:     Last in track H.
Question:  none. Default: section and binary jumps also push one entry (reversible: keep replaceState for those kinds).
```

## Outcome

Open.
