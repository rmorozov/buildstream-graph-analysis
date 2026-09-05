# UX-277: every table cell stringifies its own structure

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-267 | **Serves:** R1, R7, R8 — everyone who reads the report | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Reported from a real report, three ways: *"there still json output like in
leaf analysis - leaves_detail row - has json object value"*, *"there
tables that still have extremely long cells that generally are unbound"*,
and the bottleneck view having *"no way to go to detailed info"*. All
three are one line.

`UX-267` built `renderStructured` — inline / bounded table / fold, chosen
by width — and wired it into `renderPairs`, which draws `<dd>` cells. It
was never wired into `buildTable`, which draws **every `<td>` in the
report**. The leaf of that function is `bga/viewer/app.js:479`:

```js
Array.isArray(raw) ? raw.join(", ")
  : (raw && typeof raw === "object") ? JSON.stringify(raw)
  : numeric ? quantity(raw, kind) : (raw ?? "—")
```

So the rule governs one cell type and stops dead at the other. Measured
on the 1,202-element synthetic run (`bga gen-synthetic /tmp/scale
--seed 1`), 18,415 `<td>` cells:

```text
raw JSON cells                     6
joined-array cells over 60 chars  11
"[object Object]" cells            1
widest cell                   14,300 characters   (signals / leaves_detail)
next widest                    2,687              (signals / leaves)
next                           2,538              (structural / non_deferrable_leaves)
```

Three stringifications, each wrong in its own way:

| value | what the reader sees | what it is |
|---|---|---|
| `{a: {...}}` | `{"all.bst":{"element_kind":"stack",…}}` | 14,300 chars of JSON in one cell |
| `[[name, n], …]` | `layer08/mod073.bst,0.0058,0.583, …` | tuples flattened by nested `toString` |
| `[{…}, {…}]` | `[object Object], [object Object]` | worse than JSON — no information at all |

`CELL_TEXT_CAP` (`UX-269`) never fires either, because it lives on the
path this one bypasses. A 14,300-character cell is not a truncation
failure; it is a cell that was never offered to the renderer that
truncates.

**And it costs affordances, not just legibility.** `choke_points` in the
bottleneck block is a joined string, so it has no rows — and therefore
no sort, no filter, no `Top N` bound, and no Inspect column. Measured:
**zero links out of the entire `structural` section**. The data a reader
wants to click through is all present and rendered as dead text.

## Required Fix

1. `buildTable`'s cell leaf calls `renderStructured` for any non-scalar
   value, so one rule governs `<td>` and `<dd>` alike.
2. A nested table inside a cell stays bounded — `map-table` already has
   the height and scroll; the fold already carries a count.
3. `[object Object]` cannot survive anywhere: an array of objects is a
   table or a fold, never a `toString`.
4. `data-raw` keeps carrying the unrendered value, because sort, filter
   and `Copy shown rows` read it and must not start reading markup.

## Out of Scope

- Re-tuning `OBJECT_INLINE_FIELDS` / `ARRAY_INLINE_ITEMS`. The rule is
  settled (`UX-273`); this is about where it is applied.
- The bottleneck section's *navigation* — that a choke point should be
  one click from its element is `UX-283`, and it becomes possible once
  the cell is a table rather than a string.

## Acceptance Test

On the 1,202-element run: no `<td>` contains `[object Object]`, no cell
exceeds `CELL_TEXT_CAP` of unbroken text, and the three widest cells
above are tables or folds. The guard reddens if the leaf is reverted to
`JSON.stringify`.

## Outcome — 🟢 Fixed & Verified

`buildTable`'s cell leaf calls `renderStructured`. One rule now governs
`<td>` and `<dd>` alike, and the three symptoms it produced are gone.

Measured on the 1,202-element synthetic run in Chrome 141:

```text
                                   before     after
<td> cells                         18,415    19,706
raw-JSON cells                          6         0
"[object Object]" cells                 1         0
widest cell, textContent           14,300     4,409
widest cell, *visible*             14,300       152
cells over 200 visible characters       6         0
widest cell                         829 px    550 px
document                         18.8 scr  18.8 scr
```

**The visible figure is the real one, and it is the one a naive
measurement gets wrong.** `textContent` includes the body of a *closed*
`<details>`, so a correctly folded cell still reads as 4,409 characters
to `querySelectorAll`. What a reader sees is the summary; the widest is
now 152 characters, inside `CELL_TEXT_CAP`'s 160. The first version of
the guard measured `textContent` and would have failed a properly folded
cell while passing an unfolded short one.

Cell count rises (18,415 → 19,706) because nested tables have rows of
their own, and the document height does not move at all — the new rows
are inside folds and bounded boxes.

**Arrays of arrays are a table, not two `toString` calls.**
`high_fanin_elements` is `[["app.bst", 8], …]` and rendered
`app.bst,8, lib-b.bst,4` — nested `Array.prototype.toString`, twice.
Positional members now become columns, which is what the payload means
by them.

**`CELL_NEST_LIMIT = 2`** is new and is the one judgement call. A cell
may hold a table whose cells hold one more; past that the value folds as
labelled text. The document is seven levels deep, and seven nested
tables is seven sets of column headers and seven sets of tools for one
value. The fold still carries its name and count, so bounded is not
hidden.

**`data-raw` still carries the unrendered value** — `JSON.stringify` for
structures, `String` for scalars. Sorting, filtering and `Copy shown
rows` read it, and a cell that started exporting markup would silently
change what they compare and what they copy.

**The guard** — `tests/unit/test_a_table_cell_obeys_the_value_rule.py`,
21 tests, driving `buildTable` directly through the shared DOM shim
(`UX-264`) over five shapes taken from the real report.

Falsified, four mutations:

```text
M1  revert the leaf to JSON.stringify      -> 6 tests (the defect itself)
M2  arrays go back to join(", ") only      -> object_object[objects],
                                              bounded[leaves]
M3  raise CELL_NEST_LIMIT 2 -> 6           -> nest bound + declared bound
M4  data-raw carries the rendered node     -> data_raw_still_carries…
```

**M3 did not discriminate on the first attempt.** The nesting test read
`CELL_NEST_LIMIT` out of `app.js` and asserted the measured depth
against it — so raising the constant raised the bar with it and the
mutation passed. A guard that checks the code against itself checks
nothing. The bound the guard defends is now written *in the guard*
(`NESTING_BOUND = 2`), with a second test asserting the module still
declares the same number, so moving it is a deliberate change that
reddens until both are updated.

The guard also caught a bug in its own first draft: `find` recurses, so
a nested table's own cells were in the sample and a *sum* of tables
double-counted them — it reported 3 nested tables where there are 2.
Measuring maximum nesting **depth** is the honest instrument.

**What this does not fix, measured:** the `structural` section still has
**zero links out of it**. `choke_points` is now a table rather than a
string, which is what makes the route possible; building it is
[`UX-283`](UX-0283-the-bottleneck-view-names-elements-you-cannot-reach.md).

**A pre-existing defect surfaced while checking the cost**, and it is not
this change's: the export ceiling guard measures the **4-element** golden
fixture, so it cannot see growth driven by content.

```text
                        before     after    delta   ceiling 260,000
golden (4 elements)    242,263   243,006     +743   OK   <- what the guard measures
macro_micro (11)       280,093   280,836     +743   OVER
```

This change costs **+743 bytes**. The 11-element export was already
20,093 bytes over the ceiling before it, and nothing reddened. Filed as
[`UX-287`](UX-0287-the-export-ceiling-is-measured-on-a-four-element-run.md).
