# UX-277: every table cell stringifies its own structure

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-267 | **Serves:** R1, R7, R8 — everyone who reads the report | **Topic:** viewer

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
