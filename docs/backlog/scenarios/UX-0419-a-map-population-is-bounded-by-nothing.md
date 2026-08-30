# UX-419: a map population is bounded by nothing, and the sweep cannot see it

**Priority:** High | **Status:** 🟢 Done | **Found by:** UX-411's measurement | **Serves:** anyone whose run has many binaries or many tasks | **Topic:** viewer

## Motivation

`UX-413` made a long table open bounded whether or not it has a column
worth ranking by. It bounds **tables**. A section whose payload is a
*map* — one measure per key — is drawn by `renderPairs`, which has no
bound at all:

```js
for (const [name, value] of Object.entries(object)) {
```

Measured by rendering each of `UX-396`'s two ranked maps at 120 keys
in the shim, exactly as `UX-400`'s sweep does for record populations:

```text
by_binary            entries 120   drawn 120   shown 120   tables 0
wall_clock_share_us  entries 120   drawn 120   shown 120   tables 0
```

Every pair drawn, nothing hidden, no table and therefore no badge, no
filter, no preset and no `N of M`. `UX-360`'s volume budget is measured
on three fixtures, and the largest of them has eleven of these keys.

The sizes are not hypothetical. `wall_clock_share_us` is one duration
**per task uid**, so it is the element population by another name —
1,202 keys on the `gen-synthetic` scale run. `by_binary` is one count
per binary name across the whole build; the round-60 capture published
`cmake 248, sh 150, make 99, c++ 88, cc1plus 51, …`.

**And no instrument would have found it.** `UX-400`'s sweep discovers
its populations as *arrays of objects*:

```js
.filter(([, v]) => Array.isArray(v) && v.length
                   && v.every((r) => r && typeof r === "object" ...))
```

A map of numbers is not one, so the whole zero/one/many sweep — the
file written precisely to stop the next population shipping the same
three bugs — steps over every section of this shape.

## Required Fix

- Bound a long pair list the way `UX-413` bounds a long table: past
  `TABLE_OPENS_BOUNDED_ABOVE` entries, show the first
  `TABLE_OPENS_BOUNDED_ABOVE` in the payload's order, say `40 of 120`,
  and give one control that shows the rest. `boundCards` is the same
  shape for a different element and is the obvious thing to generalise.
- **Extend `UX-400`'s sweep to map populations**, at zero, one and
  many. The bound is worth less than the instrument: this defect
  existed because the sweep's discovery rule has a shape-shaped hole,
  and the next map section will fall in it too.

## Out of Scope

- Turning a ranked map into a table. That is a bigger change with its
  own reader-facing consequences, and `UX-411` decided the *drawing*
  question separately; this is about volume.
- Choosing an order for the entries. As in `UX-413`, publication order
  is the emitter's decision.

## Acceptance Test

- A map section rendered at 120 keys shows `TABLE_OPENS_BOUNDED_ABOVE`
  entries and a badge naming the total.
- `UX-400`'s sweep discovers `by_binary` and `wall_clock_share_us` and
  asserts all three legs over them, with the ledger for each leg
  empty or filed.

## Outcome (round 66, 2026-08-30) — 🟢 Done

### The gap, measured

Each of `UX-396`'s two ranked maps rendered at 120 keys, in the shim,
exactly as `UX-400`'s sweep renders a record population:

```text
by_binary            entries 120   drawn 120   shown 120   tables 0
wall_clock_share_us  entries 120   drawn 120   shown 120   tables 0
```

Every pair drawn, nothing hidden, no table and therefore no badge, no
filter, no preset and no `N of M`.

### After

```text
by_binary            entries 120   drawn 120   shown 40
                     badge "40 of 120"   control "Show all 120 rows"
wall_clock_share_us  entries 120   drawn 120   shown 40
                     badge "40 of 120"   control "Show all 120 rows"
```

`drawn` stays 120 because the pairs are **hidden, not removed** — the
rule `foldTheMiddle` and `boundCards` already follow, so Ctrl-F, the
export and every anchor keep working.

### One bound, three shapes

`boundCards` was already the right shape for a different element, so it
was generalised rather than copied. `boundGroups(groups, bound, noun)`
takes *groups of nodes* — one card, or a `<dt>` and its `<dd>` — hides
past the bound and returns the badge-plus-control. `boundCards` is now
three lines on top of it and `boundPairs` collects the pairs.

A `<dt>` and its `<dd>` are one thing to a reader, so they are one
group. Hiding the value and leaving the term is its own bug, and
mutation A3 below is that mutation.

### The half worth more than the bound

`UX-400`'s sweep discovered its populations as **arrays of objects**:

```js
.filter(([, v]) => Array.isArray(v) && v.length && v.every(...))
```

A map of numbers is not one, so the file written to stop the next
population shipping the same three bugs stepped over an entire shape —
which is why this defect survived. The discovery rule now finds both,
and the sweep renders each at zero, one and many *in the shape the
payload publishes it in*:

```text
records: 11   maps: 11   swept: 20
maps swept: attribution, by_binary, configure_phase, cpu_time,
            document_shape, graph_metrics, graph_summary, peak_memory,
            ready_queue, wall_clock_share_us
```

**Ten new populations, and every leg is clean** — no ledger. The zero
leg marks `data-empty` and says "found none" on all ten, which is
`UX-388`'s fix reaching a shape nobody had checked it against; the one
leg draws one pair; the many leg draws 40 of 120.

Every clause that reads a count now reads it through `_seen`, which
returns `(visible, total)` from whichever of rows, cards or pairs the
section drew. A clause that reads one shape is a clause the next shape
walks past, and that is the whole finding.

### The export moved, and the way it moved is the point

```text
page          283,964 -> 284,584   (+620, source)
golden        384,218 -> 384,838
macro_micro   439,581 -> 440,201
```

Both fixtures move by exactly the same 620 B as the page, which is the
signature of source: **no control is rendered on either of them**,
because neither publishes a map over 40 keys. That is the same absence
that let the defect live — the bound is measured by `UX-400`'s sweep at
120 keys, not by a fixture. Both bounds restated with the measurement.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| A1 | the pair list unbounded again — the filed defect | `test_a_map_of_many_is_bounded_like_a_table`, `test_a_long_population_opens_bounded`, `test_the_bound_holds_at_the_threshold_the_viewer_declares`; 3 failed, 16 passed |
| A2 | the sweep's map discovery matches nothing — the shape-shaped hole restored | `test_it_sweeps_both_shapes`, `test_a_map_of_many_is_bounded_like_a_table`; 2 failed, 17 passed |
| A3 | `boundPairs` groups on `<dd>`, hiding each value and leaving its term | the same three as A1; 3 failed, 16 passed |

A2 is the one that matters most: it proves the *instrument* is what
changed, not only the page. A3 is the direction that would have looked
right — 40 values shown — while leaving 120 terms on screen.

`test_a_map_of_many_is_bounded_like_a_table` exists because the other
clauses read whichever shape a section drew: if every map stopped
drawing pairs, `_seen` would return `None` and they would all pass.
That clause names the shape.

### Deviation from the Required Fix

- **None.** The bound folds to the first `TABLE_OPENS_BOUNDED_ABOVE`
  entries in the payload's order, says `40 of 120`, and gives one
  control that shows the rest; the sweep reaches map populations at all
  three sizes. The Out of Scope holds: no map became a table, and no
  order was chosen — publication order is still the emitter's.

### Addendum — what the volume budget said afterwards

This item was committed on a tier run, and the **full suite** that
followed it went red:

```text
FAILED tests/unit/test_the_page_has_a_volume_budget.py::
    TestBothBudgetsAreBound::test_the_budgets_are_not_slack[scale]
the opened height budget for runs up to 4000 elements is 66000 and
scale measures 26312; a bound with that much slack is a number nobody
will ever meet
```

Committing before `make test` is the deviation, and it is recorded
rather than hidden: the tier run this item's Acceptance Test names is a
selector, and the verify skill's step 3 says in as many words that it is
not evidence about the suite.

What it caught is the size of the fix. Measured on both trees with one
instrument, at 1440x900, all three runs — `UX-418`'s worktree at
`ae981dc` for *before*:

```text
                      landed   opened    words   controls    nodes
golden      before     3,800   15,618    5,565        427    2,498
            after      3,800   15,618    5,565        427    2,498
macro_micro before     5,965   31,804   11,127        750    5,686
            after      5,965   31,804   11,127        750    5,686
scale       before     4,763   55,998   36,536      1,940   24,291
            after      4,763   26,242   36,542      1,941   24,294
```

**The opened page at 1,202 elements halved**, 55,998 → 26,242 px, and
nothing else moved: the two small fixtures are untouched (no map of
theirs holds forty pairs), and on `scale` the +6 words, +1 control and
+3 nodes are the single bound's badge and its "Show all N pairs"
button. A bounded pair is `hidden`, so it stops occupying pixels while
its text and its nodes stay in the document — the same asymmetry
`UX-366` recorded from the other side, where only `nodes` could see a
table double.

So the large class's opened-height bound came down 66,000 → **32,000**
in `tests/unit/test_the_page_has_a_volume_budget.py` and in
`docs/design/styleguide.md` §3e, which is `test_the_budgets_are_not_slack`
doing exactly what its docstring said it would do rather than breaking.
The scale row's other three bounds are still met from below and are
left where they are. §3e's whole table was refreshed with this reading
while it was being edited — `golden` and `macro_micro` had drifted from
their round-59 figures and were being presented as current.

One consequence is worth stating because it reads as a bug and is not:
the large class's opened height is now **below** the small class's
(26,242 against 31,804). Every population on the scale page is bounded
now; the small fixtures' populations are mostly under their bounds and
draw in full. The 11-element page is the denser of the two once the
1,202-element one stops drawing 1,202 of anything. §3e says so in
place, since the split's original justification — "55,000 px at 1,202
elements may be acceptable while 55,000 px at eleven is not" — is no
longer the page's shape. `words` and `nodes` still grow 3.3x and 4.3x
with the run, which is what keeps the two classes apart.
