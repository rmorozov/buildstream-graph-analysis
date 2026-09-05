# UX-285: the identity blocks are split, and the blast box is last

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-207 | **Serves:** R1 and R7 — reading top-down, and asking a question mid-read | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome

🟢 **Done.** Measured in Chromium on both runs, before and after.

**The identity closes the document.**

```text
                  1,202-element run       golden mixed_task_kinds
              before        after         before        after
summary        10.50        17.86          8.26        10.39
run_instance   10.69        18.06          8.45        10.58
producer       10.83        18.20          8.56        10.69
document       18.51        18.51         11.00        11.00
             (57% of it)  (96% of it)   (75%)        (94%)
```

Adjacent already, on both runs, once the three moved together: gaps of
0.04 and 0.03 screens. `placeIdentityLast` is called from `boot` rather
than from `render`, because `UX-216`'s element sections, the trend and
the inlined questions are all appended after `render` returns — ordering
inside `render` means "last of the payload" and leaves twenty-five
detail blocks below the block that is supposed to close the page.

The rail still reaches them in one action (item 2, unchanged: they are
sections with anchors and `toc` reads the document it is given).

**The blast control sits with the findings.**

```text
                        1,202-element run    golden fixture
blast, before             18.27 of 18.51     10.76 of 11.00
blast, after               4.32              3.35
                          (23% of it)       (30%)
findings                   1.36              1.31
```

After `next_steps` rather than after `findings` itself: `findings`,
`headline` and `next_steps` are one narrative in the payload's own
order, and `next_steps` is where these runs print `bga blast <target>`
as the command to run — the control does that without the terminal, so
it sits under the line that names it.

**The pair the item could not check when it was filed.** Both runs
measured lacked a source inventory, so `resource_blast` was absent and
"the control sits beside the table" was unfalsifiable. Adding a
`sources/v1` file with one monorepo behind three of the four elements
produces the table, and the pair reads together:

```text
findings   index  4/28   1.31 - 2.70
resource_blast    8/28   4.22 - 4.63
blast             9/28   4.66 - 4.73     0.03 screens below the table
```

`_boot_order` gained an `inventory` argument for this, so the guard
exercises it rather than a description of it.

**One deviation from the Acceptance Test, recorded rather than
smoothed.** *"within two screens of `findings`"* holds at 1440×900
(0.92) and 1280×800 (1.03) measured from the end of `findings`, and
**not** at 390×844, where it is 2.16:

```text
             document   findings   headline   next_steps    gap
1440x900       11.32       1.12       0.50        0.31      0.92
1280x800       12.79       1.26       0.56        0.35      1.03
 390x844       20.49       1.55       0.93        1.11      2.16
```

On a phone the diagnosis alone is 2.04 screens, so no placement that
keeps `findings → headline → next_steps` together can meet two screens
there. The width-independent clause is guarded instead: nothing but that
narrative separates the finding from the control, at every viewport.

**Item 4, the order guard.** In `test_the_order_the_page_has.py`,
reusing `UX-235`'s harness — the booted export's own child sequence,
never a literal rebuilt from source order — plus four screen-position
guards in `test_the_page_has_geometry.py`.

**Falsification.** Eight mutations, each asserted to have landed before
the result was read:

```text
M1  boot never calls placeIdentityLast          3 order guards red
M2  the blast block is appended, not placed     3 order guards red
M3  BLAST_ANCHORS prefers next_steps to the     2 order guards red
    resource_blast table
M4  IDENTITY_SECTIONS declared in reverse       2 order guards red
M5  the placement moves back inside render()    14 geometry checks GREEN
M6  no placement at all (the filed defect)      6 geometry guards red
M7  the blast block appended again              8 geometry guards red
M8  two published fields carry one population   the clash guard red
```

**M5 is why there is a fifth geometry guard.** The mutation that
reproduces this item's defect on a long run left every geometry check
green on the fixture, because four element sections and a trend are only
a quarter of an eleven-screen page — the *pre-change* report already put
`summary` at 75%, which satisfies "in the last third". The clause that
discriminates is the pixel one: nothing at all is drawn below the
identity group. The weak clause stays, because it is this item's own
wording, and its docstring says it is weak.

**One guard elsewhere was wrong about what it measured.**
`test_no_two_tables_carry_the_same_elements` named its tables by
*position* (`structural#31 and structural#29`), so moving two sections
reddened it with the identical pair still identical, five tables further
down. It names them by `UX-292`'s `data-table` path now
(`structural.batch_opportunities.serialized_pairs and
structural.sensitivity.top_opportunities`), which is both stable under a
move and legible in the failure message — M8 confirms it still catches
a real duplication.

### Superseded a day later, and unchanged

`UX-286` grouped the report into chapters in the same round. The
identity blocks are one chapter ("Which run is this?") and it is the
last; the blast control is in "What if I change this?", whose declared
order puts it directly after `resource_blast`. Both placement passes
this item shipped — `placeIdentityLast` and `placeBlast` — are deleted,
because two mechanisms deciding one order is how a page ends up with an
order nobody can predict.

Every outcome above still holds, measured after that change: identity at
97–99% of the 1,202-element run and 95–98% of the fixture, blast at 24%
and 31%, 0.99 and 0.94 screens after the end of `findings`. Every guard
this item landed still passes against the new mechanism — the guards
assert what the page *is*, which is why they survived the mechanism
under them being replaced.

### One label corrected

The "after" columns above were measured on the exported **golden
`mixed_task_kinds`** fixture, and were first written as `macro_micro`.
They are the same measurements; the run they name is not the one this
item was filed against, which carries a Plane 2 report and is a
different document. Review 3 caught it, and it is corrected rather than
left to look like a comparison across rounds. The 1,202-element figures
are unaffected.
