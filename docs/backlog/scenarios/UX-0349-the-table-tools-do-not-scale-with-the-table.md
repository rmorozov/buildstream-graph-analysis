# UX-349: the table tools do not scale with the table

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-284 (table tools above the table), UX-289 (one element table, many presets) | **Serves:** the reader counting controls on a screen | **Topic:** viewer

## Motivation

The report carries a lot of controls. Measured on a real boot:

```text
                buttons  inputs  selects  links   total
golden              195      81       20    116     412
macro_micro         274     120       32    204     630
```

Most of the inputs are one thing: a per-column threshold filter, given
to every table whatever its length.

```text
                tables   of which <=12 rows and still filtered
golden              25                    17
macro_micro         38                    26
```

Twenty-six of thirty-eight tables are short enough to read at a glance
and carry a filter box per column anyway. On the eleven-row element
table that is five inputs above eleven rows, and one of them sits under
a boolean column with the placeholder `> 10`.

The same table shows the other half of it — columns whose every value
is identical:

```text
element      Element durations  Downstream count  Is leaf  Element kind  Observed critical
core.bst              19.1 s                  8    false         cmake               true
codegen.bst            7.0 s                  8    false         cmake              false
lib-b.bst              4.0 s                  6    false         cmake               true
...  (11 rows; `Is leaf` is false in all eleven)
```

Fourteen columns across the signals tables have exactly one distinct
value over more than three rows. A column that never varies is a fact
about the table, and it is spending a sixth of the width to repeat
itself eleven times.

## Required Fix

**Filters appear when the table is long enough to need them.** The
threshold is the row cap the visual contract's §3 already sets: below
it, the reader scans; at or above it, the tools appear. This is one
condition at the call site that builds the filter row, and it removes
most of the page's inputs.

**A column with one distinct value is stated once, above the table,
and not drawn.** "All eleven are `cmake`, none is a leaf" is a
sentence; eleven repetitions of `cmake` are a column. Where the value
is *not* uniform the column stays, unchanged.

**A filter's placeholder matches its column's quantity.** `> 10` under
a boolean is the tell that the placeholder is a default rather than a
reading of the declaration — `UX-341` left every column declaring one,
so the placeholder can be derived rather than chosen.

## Out of Scope

- The row cap itself, and `UX-289`'s presets, which decide *which*
  rows a table has rather than what sits above them.
- Sorting. It costs one header affordance at any length and helps at
  every one, so there is nothing here for a threshold to scale.

## Acceptance Test

On both committed fixtures: no table under the row cap renders a filter
input; no rendered column has one distinct value over more than three
rows; every filter placeholder is derived from the column's declared
quantity, asserted against the schema rather than against a list. The
control census above is re-run and pasted, before and after.

## Outcome (round 54, 2026-08-28) — 🟢 Done

### The census, before and after

```text
                buttons  inputs  selects  links   total
golden before       257      48        9    123     437
       after        257      18        9    123     407
macro  before       341      81       19    222     663
       after        341      28       19    222     610

tables at or under the row cap, filtered   golden 12 -> 0   macro 21 -> 0
threshold boxes                            golden 17 -> 0   macro 33 -> 0
columns repeating one value over >3 rows   golden  2 -> 0   macro  1 -> 0
```

Thirty inputs off golden and fifty-three off `macro_micro`. The
remainder are the jump box, the focus controls and the marks — not
table apparatus.

### The three rules

**Filters appear when the table is long enough to need them.** The
bound is `TABLE_OPENS_BOUNDED_ABOVE` — the same forty that decides
whether a table opens bounded, because it is the same question: is
this a table somebody reads to the end. Neither fixture has a table
that reaches it, which is the finding restated: every filter row on
either page was apparatus for a table a reader can see whole.

**A column with one distinct value is stated once and not drawn.**
Over more than three rows, `UX-226`'s floor applied to width: two rows
that agree are a coincidence. The sentence reads *"All 48 rows: Kind
cmake."* and the column goes; the **rows** stay, so `Copy 12 rows`,
Ctrl-F and the export see what the payload had.

**A threshold box goes only where the column holds numbers**, read off
the rendered cells rather than off the declaration. `> 10` under a
boolean was the tell, and the guess is not `columnSpecs`' — it is the
*element join*, which ends `?? guessQuantity(name) ?? "count"`, so a
boolean column arrives declared a count.

Sorting is untouched, per the filing.

### The interaction this exposed

A table with **both** a filter and a Top-N preset restored its preset
*after* its filter, so a shared link to a filtered view came back
reading `25 of 48` on a page whose filter matched two. `UX-289` had
already written the reason down for the view select — it rewrites the
rows the filter is about — and the Top-N select was left last.

Unreachable until this round: it needs a table with both, and the
filter row used to appear at every length while the preset appears
only past the cap. Making the filter row rarer is what made the pair
possible to construct.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `fc092ca`.

| # | mutation | reddened |
|---|---|---|
| T1 | filters at every length again — the defect itself | *"golden: 13 table(s) at or under 40 rows carry filters: top_actions (3 rows, 1 search + 0 thresholds), …"*, and 22 on `macro_micro` |
| T2 | uniform columns drawn again | 4 clauses across both fixtures, naming `elements.element_kind = unknown` and `confidence.hard_gates.value = true` |
| T3 | the column goes and says nothing | `test_what_was_removed_is_said`, both fixtures |
| T4 | a threshold box over a non-numeric column | `test_a_boolean_column_gets_no_threshold` |
| T5 | the Top-N restore moved back after the filter | `test_applying_it_restores_the_same_shown_rows` — *"'2 of 48' == '25 of 48'"* |
| T6 | the uniform rule keys on the rendered text again | `test_a_boolean_column_gets_no_threshold`, via the duration column it wrongly removes |

**T4 and T5 both began non-discriminating, and both bought something.**

T4 passed because gating the filter row left *no* threshold box on
either page — the page-level clause is 0 of 0 there, and the rule it
states became invisible to it. The direct clause that replaced it
drives a forty-eight-row table with a boolean column declared `count`,
which is the shape the element join actually produces; the first draft
of that table left the column undeclared, and `guessQuantity("is_leaf")`
is null, so it did not reproduce the defect either.

T5's first form *deleted* the preset restore rather than moving it,
which passes trivially: with no preset restored the filter's badge
stands. Moved back to where it was, it reddens.

**T6 is a defect the synthetic table found in this round's own code.**
The uniform rule first keyed on the rendered text, and forty-eight
durations from 1000 to 1047 µs all format as `1 ms` — so it removed a
column the payload varies in, taking its sort key with it. It keys on
`data-raw` now: a formatter rounding a column flat is a fact about the
formatter, and this rule is about a column that never varies.

### Deviation from the Required Fix

- Two existing guards needed a table with a filter to go on testing
  what they are about, and now **pad** one: the state-key guard pads
  `leaf_analysis.leaves_detail` past the cap it reads out of the
  module, and the view-link guard pads its synthetic rows. Padding
  rather than a longer fixture, because what is under test in both is
  the fragment rather than the rows — and reading the cap rather than
  pinning 40, so a round that moves the rule moves the padding with
  it.
- The filing's census is not the one above. It counted 412 and 630
  controls; the page had grown by `UX-347`, `UX-348` and `UX-350`
  before this ran. The before column here is measured on the tree this
  item was worked against.
