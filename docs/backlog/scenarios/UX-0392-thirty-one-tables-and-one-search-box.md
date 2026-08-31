# UX-392: thirty-one tables, one search box

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-349 (the table tools do not scale with the table), UX-366 ("All rows" shows twenty-five of twelve hundred), UX-289 (one element table, many presets), UX-223 (the jump box is a command palette) | **Serves:** anyone looking for one element in a report of a real project | **Topic:** viewer

## Motivation

The user asked whether the search controls help — naming the main one
and "the blast radius search control". Measured on the round 63
export, **the blast-radius search does not exist**. The page has two
search-shaped inputs in total: the global `Jump to…` palette in the
header, and one filter box on `binary_cost`.

```text
tables                        31
  with a filter box            1
  with a preset menu          22
  with a threshold input       1
  >10 rows and no filter       4
```

Twenty-two preset menus is the tell. A preset answers *a question the
page anticipated*; a filter answers *the question the reader arrived
with*, and thirty of thirty-one tables cannot take one. The four
tables already over ten rows on an eleven-element example are the ones
that become unreadable at a real project's scale — which is
`UX-366`'s and `UX-367`'s finding arriving at the table's controls
rather than at its row cap.

`UX-349` measured the same asymmetry one axis over (the tools do not
scale with the table) and fixed the layout. What survives is that the
one tool that scales — a filter over rows — exists once.

The global palette is not a substitute. It jumps to a *section*, not
to a row, so a reader looking for `codegen.bst` in a 1,200-row table
is returned to the top of the table it is in.

## Required Fix

- **A filter is a property of a table, not of one table.** Whatever
  `binary_cost` has, every rendered table gets, from the same code —
  which means it belongs to the table renderer rather than to a
  section.
- **The filter searches what the reader sees**, including the columns
  a preset is not sorting on, and says how many rows of how many it is
  showing — the sentence `UX-366` established for the row cap.
- **The palette reaches rows, not only sections.** Typing an element
  name should be able to land on that element's row in the table the
  reader is in, which is the control the user was describing when they
  said "blast radius search".

## Falsification

A guard over the rendered page asserting that every table with more
than a threshold of rows carries a filter control, and that the
control filters (a fixture, a query, a row count that drops). Today
thirty tables fail the first clause.

The other direction, and it is the one that matters: adding thirty
controls must not spend `UX-360`'s volume budget or re-open `UX-349`'s
finding. One shared control rendered per table is a fixed cost per
table; thirty bespoke ones are not. The guard on the page's own byte
count is the arbiter, and it is already in the suite.

## Out of Scope

- Whether a filter or a preset is the better default. Both stay,
  because they answer different questions — the one the page
  anticipated and the one the reader arrived with.
- Server-side or streamed filtering for very large tables. The page
  parses nothing (`UX-296`); the filter runs over rows already in the
  document.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### Two of the three premises are false, and one defect was real

**The filter is already a property of the table renderer.**
`interrogable` builds it for every table it draws, gated on row count
by `UX-349`:

```javascript
const worthFiltering = total > TABLE_OPENS_BOUNDED_ABOVE;   // 40
```

Thirty tables of thirty-one carried no filter because thirty of them
had fewer than forty rows *on an eleven-element example*. Measured on
the seeded 1,202-element synthetic run:

```text
tables                        22
  over 40 rows                 2   (elements 1,202; leaves_detail 135)
  of those, with a filter      2
  under 40 rows               20
  of those, with a filter      0
```

The rule holds exactly, in both directions. `UX-349` set that gate with
its own measurement — "12 of golden's 13 tables carried a filter row,
and every one of them was short enough to read at a glance" — so the
thirty are below the line on purpose, not unable. This is `UX-367`'s
finding ("the volume budget is enforced at eleven elements") arriving
at a second guard.

**The palette already reaches rows.** `go()` resolves an element with
`root.querySelector('[data-element=…]')`, and the first such node in
the document is a `<tr>`:

```text
[data-element="lib-c.bst"]  ->  TR, A.path-box, TR, TR, TR, TR, SECTION
first is a row: True, inside a table: True
```

**What was real: the two controls did not compose.** Measured on the
1,202-element run before the fix:

```text
opened bounded            25 of 1,202
filter "mod023"           12 of 1,202
then "Top 10 by …"        10 of 1,202   filter box still says mod023
                                        rows drawn from all 1,202
```

A reader looking at ten rows that have nothing to do with what they
typed, while the box they typed it in still shows it.

### After

```text
opened bounded            25 of 1,202
filter "mod023"           12 of 1,202
then "Top 10 by …"        10 of 1,202   every shown row matches
then clearing the filter  10 of 1,202   back to the preset's own view
```

One pass in `applyFilters`, so the text, the thresholds and the Top-N
narrow the same set and the badge has one place to come from. "The ten
biggest **of the ones I asked for**" is what a reader typing in both
means, and `UX-392`'s own Out of Scope insists on keeping both.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| D1 | the preset runs its own pass again (`applyTopN` on change) | 2 of 7, incl. `test_a_preset_narrows_what_the_filter_left` |
| D2 | drop `top` from `applyFilters`, so clearing the filter forgets the preset | 2 of 7, incl. `test_clearing_the_filter_returns_to_the_preset` |
| D3 | lower `TABLE_OPENS_BOUNDED_ABOVE` to 5 (filters on short tables again) | 1 of 8: `test_the_gate_is_where_it_was_measured` |

### A guard of my own that did not discriminate

Both survey clauses read the gate off `structured.js`, which is right
for asking the page about the rule the page actually *has* and useless
as a bound: D3 lowered the constant, the file's own expectation moved
with it, and both clauses stayed green while every short table on the
page grew five inputs. `GATE_AS_MEASURED = 40` is now written down
beside the read, with what `UX-349` measured to set it, and D3
reddens.

### Deviation from the Required Fix

- **Bullets 1 and 3 were already satisfied**, and this is the fifth
  false premise of the round. Both are re-measured as clauses rather
  than dropped: `TestTheFilterIsAPropertyOfEveryTable` asserts the gate
  in both directions at a scale where it bites, and
  `TestThePaletteReachesARow` asserts the palette lands on a `<tr>`. A
  premise that was checked is worth more written down than a bullet
  quietly not done.
- **The guard runs on the synthetic run, not on a committed fixture.**
  No committed fixture has a table over forty rows, which is exactly
  why the filing counted one filter. `--seed 1` makes the 1,202
  elements the same on every machine (`UX-213`), and the file is tiered
  medium at a measured 7.7 s.
- **`applyTopN` is now unused by the viewer** and stays exported: one
  guard drives it directly, and removing it is a separate change from
  making the controls compose.
- **One existing clause was amended.**
  `test_the_report_has_two_panes.py`'s badge clause grepped the
  bounded-open block for `badgeText(`; that block now sets the state
  and calls `refresh`, which is the *one* place the badge is written
  once the two controls compose. The clause follows the call and
  asserts the write itself
  (`badgeText(applyFilters(table, state), total)`), which is the fact
  it was always about — and the badge is measured directly in
  `test_the_badge_never_describes_a_state_the_table_is_not_in`.
- **The export grew 584 B, all source**, and no bound moved: 274,589 →
  275,173 against a `PAGE_BUDGET_B` of 276,000. The data half is
  unchanged, because nothing was added to any payload.
