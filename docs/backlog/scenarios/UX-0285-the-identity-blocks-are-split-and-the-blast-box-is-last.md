# UX-285: the identity blocks are split, and the blast box is last

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-207 | **Serves:** R1 and R7 — reading top-down, and asking a question mid-read | **Topic:** viewer

## Motivation

Reported: *"run info and run instance info could be placed somewhere at
the bottom of the page grouped with producer info, and blast radius
search control must be placed close to resource_blast block somewhere
near findings."*

Both halves measured, on two runs.

**The three identity blocks are one subject split across the page.**
They answer the same question — *which run is this, on what host, written
by what* — and they are nowhere near each other:

```text
                      1,202-element run     macro_micro fixture
summary   ("Run")          1.4 screens           1.3 screens
run_instance               1.6                   1.5
producer                  10.9                  14.0

document height           18.8                  20.1
```

Nine to thirteen screens between the first two and the third. A reader
checking provenance reads two blocks near the top, forms an answer, and
meets the rest of it two-thirds of the way down — by which point the
question has been answered wrongly or forgotten.

`UX-207` earned the first screen for the **decision**, and the identity
blocks are the clearest thing on the page that is not one. They are
reference, consulted once, and they currently occupy screens 1.3–1.6 —
prime space, directly under the verdict.

**The blast box is the last thing on the page.** It is not a report
block at all but an interactive query — *"What rebuilds if I touch
this?"*, with an input and an `Ask` button:

```text
blast section, 1,202-element run:  screen 18.5 of 18.8
blast section, macro_micro:        screen 19.9 of 20.1
findings:                          screen  1.7
```

It sits after twenty-five element detail blocks, at the very bottom,
below everything. A control a reader would reach for while looking at a
finding is eighteen screens away from every finding.

`resource_blast` — the published table the control's answers belong
beside — is absent from both runs measured (neither has a source
inventory), so where the pair should sit together is checked on a run
that has one before this lands.

## Required Fix

1. `summary`, `run_instance` and `producer` are adjacent, and low.
   They are one subject and they are reference; the first screen belongs
   to the decision (`UX-207`).
2. The identity is still reachable in one action from the top — the rail
   already carries it, and a reader checking provenance should not have
   to scroll eighteen screens to do it.
3. The blast control sits with `resource_blast` and near `findings`,
   where the question "what else does this touch?" is actually asked.
4. Section order is asserted, not incidental. `UX-235` guards the order
   the page *claims*; this is the order it should have, and moving a
   block should redden a guard that names the intended sequence.

## Out of Scope

- Removing anything. Every block here earns its place; this is about
  where each one sits.
- The rail's contents, settled in `UX-271`.
- What `blast` computes (`UX-172`) or what `producer` records
  (`UX-249`).

## Acceptance Test

On both the 1,202-element run and the fixture: the three identity blocks
are consecutive and in the last third; the blast control is above the
midpoint and within two screens of `findings`. The order guard reddens
when a block is moved out of sequence.
