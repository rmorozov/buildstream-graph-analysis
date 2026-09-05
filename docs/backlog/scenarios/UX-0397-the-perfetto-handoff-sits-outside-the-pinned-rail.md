# UX-397: the Perfetto handoff sits outside the pinned rail

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-373 (two satellite pages for one handoff), UX-282 (the fallback below the button that fails), UX-209 (the rail), UX-348 (the handoff) | **Serves:** anyone who decides to open the trace after reading a finding | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The user proposed pinning the Perfetto handoff into the left pane,
beside the main search control. Measured on the round 63 export, that
costs nothing structurally:

```text
handoff button              y = 137 px   (header, scrolls away)
rail                        already position: sticky
page height                 9,316 px
```

The handoff is a header ornament. The decision to open the trace is
almost never made on the first screen — it is made at a finding, four
or five screens down, by which time the button is 9,000 px behind the
reader. `UX-368` put a query on each finding for exactly this reason;
the button that opens the trace to run it did not follow.

The rail beside it is already sticky and already carries the reader's
map of the report. Moving the handoff into it puts the trace one click
from wherever the reader is, and removes a header row that scrolls
away unused.

## Required Fix

- **The handoff lives in the sticky rail**, near the jump box, so it
  is reachable from every screen of the report.
- **The fallback travels with it** — `UX-282`'s rule that the
  fallback is not below the button that fails.
- The header keeps the run's identity and loses the ornament, which is
  `UX-285`'s grouping applied to the one block that escaped it.

## The other half: whether to adopt a table library

The round also asked whether the page has reached the point of needing
a JavaScript library rather than continuing to hand-roll, naming
[Tabulator](https://github.com/tabulator-tables/tabulator). **This
item files the question, not the answer** — it is a product decision
and belongs to the maintainer.

What is measured, so the decision is made against numbers:

```text
tables in one report               31
preset menus                       22
filter boxes                        1
threshold inputs                    1
viewer modules                     21
export, total                  477 KB
```

For adoption: `UX-349` already found the table tools not scaling with
the table, `UX-392` and `UX-396` are both table-shaped, and a library
answers sorting, filtering, and virtual scrolling at 1,200 rows in one
dependency rather than in twenty-one modules.

Against: the export is 477 KB and Tabulator is roughly 400 KB, which
nearly doubles it against `UX-360`'s and `UX-367`'s volume budget;
`UX-296` made the page parse nothing and `UX-307` keeps source
commentary out of the export, both of which exist because the page is
deliberately dependency-free and self-contained; and the CSP admits
only four CDNs, so the library ships *inside* the file rather than
being fetched.

The arbiter is the volume budget. If a library lands, it lands with a
measured before-and-after of the export's page half and data half, the
same split `UX-382`'s verification log used.

## Falsification

For the handoff: the driven browser scrolls to the bottom of the
export and asserts the handoff control is still in the viewport and
still opens the trace. Today it is 9,000 px above.

For the library question: **the decision is no library, taken in
round 65 as `UX-398`.** Recorded here, with the halves beside it:

```text
bga view tests/fixtures/macro_micro/run --export
  export total   417,859 B
    page half    269,531 B
    data half    148,328 B
```

A ~400 KB dependency is 1.5x the entire page half. And the argument
this filing gave *for* adoption - "one dependency rather than
twenty-one modules" - is false:

```text
$ grep -rn 'el("table"' bga/viewer/*.js
bga/viewer/structured.js:435

viewer modules                21
modules that construct a table 1
```

One factory builds all 31 tables, so a behaviour wanted on all of them
is one change to one function. The standing question is replaced by a
priced rule in styleguide §6b, and `test_one_factory_builds_every_table.py`
holds the premise the price is computed from.

## Out of Scope

- The satellite pages. `UX-373` already collapsed two into one.
- Choosing the library. Tabulator is the one the user named; if the
  answer is yes, the comparison against alternatives is part of that
  work.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The handoff, measured before and after

Driven in Chrome on the exported `macro_micro` page, scrolled to the
end of a 9,316 px document:

```text
before   #actions-group in <header>, y = 137 px at rest, off-screen
         from the second screen onward
after    #actions-group in nav.toc, y = 140 px with the document
         scrolled to its end; the rail is position: sticky
```

**The whole group moves, not the button.** `UX-282`'s rule is that the
fallback is not below the button that fails and `UX-317`'s is that a
control's explanation lives with the control, so `#actions-group` —
button, fallback and download, one node — is what is relocated. Both
rules hold by construction rather than by a second clause, and the
guard asserts all three ids are still inside it.

**At the head of the rail, beside the jump box.** The rail scrolls on
its own axis (`max-height: 100vh; overflow-y: auto`), so the first
version appended the group after 66 entries and measured it 1,697 px
below the viewport with the document scrolled to its end — the
header's defect moved one column left. Found by driving it, before any
clause was written.

### The library question was already answered

The filing's second half — whether to adopt Tabulator — was decided in
round 65 as `UX-398` and landed in this round's Phase A: no library,
with the price in styleguide §6b and
`test_one_factory_builds_every_table.py` holding the premise it is
computed from. Nothing here reopens it.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| G1 | leave the group in the header (drop the move) | 4 of 5, incl. `test_the_handoff_is_in_the_rail` |
| G2 | append it to the rail's foot instead of its head | 2 of 5, incl. `test_it_is_still_on_screen_at_the_bottom_of_the_report` |
| G3 | move only `#perfetto`, leaving the fallback behind | 5 of 5, incl. `test_the_fallback_travelled_with_it` |

### Two neighbours the move broke, both fixed here

- **`test_apparatus_in_its_place.py` at 390x844.** A narrow viewport
  folds the rail, and a folded rail hid the handoff with it — the move
  would have been a loss for the reader with the least screen. The
  fold rule now keeps `.actions-group` visible; the map folds, the
  control does not. `UX-317`'s clause that the group is not *sticky*
  still holds: it is `position: static` inside a sticky rail, so its
  height is paid once.
- **`test_the_shape_channel_is_built.py`'s axis overlap**, from
  `UX-396`'s new decomposition in the same round. `attribution`
  publishes eight buckets and six are `0 ms` on a clean run, so eight
  labels stacked at three positions; after dropping the zeroes the two
  that were left sat 71 px apart carrying 150 px of text each. An axis
  tick now needs a share of the total (`AXIS_TICK_MIN_SHARE = 2%`,
  measured against parts of 93.6%, 5.9% and 0.5%), and a part below it
  keeps its place in the sentence and in the twin table, which is
  where §2a says the rows a reader wants live.

### Deviation from the Required Fix

- **"and still opens the trace" is asked of the served page, not the
  export.** An export has no server behind the trace, so `UX-194`'s
  rule keeps the button undrawn there — measured, `#actions` is hidden
  in the `macro_micro` export. The served class boots `UX-358`'s
  two-plane snapshot, which is the one committed capture whose trace
  carries both planes, and asserts the button is offered *and* in the
  rail.
- **One clause of mine was wrong about the placement before the
  placement was.** It asserted the group's next sibling is a chapter;
  the jump box sits between them, so it read a correct placement as
  wrong. It now measures the group's position among the rail's
  children, which is the fact it was always about.
