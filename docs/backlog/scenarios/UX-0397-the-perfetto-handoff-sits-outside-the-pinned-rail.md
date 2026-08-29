# UX-397: the Perfetto handoff sits outside the pinned rail

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-373 (two satellite pages for one handoff), UX-282 (the fallback below the button that fails), UX-209 (the rail), UX-348 (the handoff) | **Serves:** anyone who decides to open the trace after reading a finding | **Topic:** viewer

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
