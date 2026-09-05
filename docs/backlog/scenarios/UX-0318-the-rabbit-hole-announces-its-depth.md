# UX-318: the rabbit hole announces its depth

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-277 (the nesting cap), UX-205 (the tables), styleguide §3a | **Serves:** R1, R2 | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Three field reports, one mechanism. Tables nest several levels deep
and "it is unknown for user how deep rabbit hole is" — a fold says
nothing about what is behind it beyond a label. The resource blast
table "became scrollable, but nested doesn't work if I try to look
through all rows" — a nested table's scroll inside a scrolling
parent, the exact interaction §3a abolishes rather than repairs.
And the user asks for "a separate button to enlarge table to occupy
more space" — the same mechanism from the other end. §3a's three
rules: depth announced (levels and row counts on every fold), one
nested level inline, and **table focus** — the nested or capped
table takes the content column's full width as a plain in-flow
section with a breadcrumb back, the enlarge affordance entering the
same state. Deliberately not an overlay (round 24's
export-survivability argument stands); focus is served-mode state
like UX-222's, and the export keeps folds with counts.

## Required Fix

Fold labels gain depth and row counts (computed from the published
value being folded — counting is not analysis); the second nesting
level stops rendering inline and routes to focus; every capped or
nested table gets the expand control entering focus; nested
scrollboxes are removed (a table scrolls only when it is the widest
thing on screen); focus state travels in the URL fragment like the
rest of the view state (`UX-211`/`UX-225`).

## Out of Scope

- Overlays, drawers, modals — declined again with the round-24
  argument.
- Changing the nesting cap itself (`UX-277`'s number stands; this
  changes what happens at it).

## Acceptance Test

On the 1,202-element page: every fold's label states levels and
rows equal to the folded value's actual shape (walk); no table's
scroll container sits inside another (asserted from the booted
DOM); the blast table's second level opens in focus, full column
width, breadcrumb resolving back, and every row is reachable by
plain page scroll (the field defect's repro, inverted into the
guard); focus round-trips through the fragment; export shows folds
with counts and no focus machinery.

## Log

**Ground truth.** Three field reports, one mechanism, and the code that
made all three true:

```text
fold summary        "Blast radius · 44 entries"    width, never depth
main .map-table     max-height: 20rem; overflow-y: auto
main table          display: block; overflow-x: auto
```

The last two are the nested-scroll defect exactly: a `.map-table`
inside a `<td>` of a table that is itself inside a `.map-table` is a
scroll container inside a scroll container. The inner one takes the
wheel and the outer one never moves, which is what "nested doesn't work
if I try to look through all rows" describes.

**§3a.1 — depth is announced.** `shapeOf` walks the published value and
reports `{levels, rows}`; the summary carries the sentence and the
element carries the numbers, so a walk checks them against the *value*
rather than against the prose beside them. Counting is not analysis:
nothing here reads a schema or derives a figure.

```text
"Blast radius · 44 entries"     ->  "Blast radius · 1 level, 44 rows"
"Odd shape · 3 entries"         ->  "Odd shape · 2 levels, 3 rows"
```

Measured on the two committed exports: 18 folds on the golden page, 28
on macro_micro, every one carrying both numbers, and eleven of them
resolved back to their payload key and re-counted in Python.

**§3a.2/§3a.3 — table focus, and it is a section.** One control, three
entrances: the fold that is too deep to render inline, the nested
table, and the capped one. `tablefocus.js` **moves** the node rather
than re-rendering it — the table a reader expands is *the* table, with
its filter, its sort and its Top-N as they were left — and remembers
where it came from with a marker so it goes back exactly there.

Deliberately not an overlay; round 24's export-survivability argument
stands, and the guard makes it checkable: after going back, the
document is **byte-identical** to before, measured by serialising the
whole report tree on both sides.

```text
                          export      served
folds                       18/28       18/28
expand controls              0/0         5/11
```

Nested is counted in *tables*, not in calls: `renderStructured` hands
`mapTable` `depth + 1`, so a section's own fold arrives at depth 1 and
only depth 2 is a table inside another table's cell. The first draft
used `depth > 0` and put an Expand on all 18.

**Nested scrollboxes are gone**, not tuned: `main .map-table` has no
scroll of its own, and `main table table` turns off the inner table's
sideways scroll. The chain walk on both booted pages finds no scroll
container inside another.

**The instrument was wrong, and this found it.** `tests/dom_shim.mjs`
had `remove()` and **not** `removeChild()`, so every
`parent.removeChild?.(child)` in the viewer was a silent no-op in every
guard — the optional call swallowed the missing method. Focus leaves a
marker and takes it away again, so "byte-identical after going back"
failed against the instrument rather than against the page. Added, and
measured in the same Chromium the shim's other rows were measured in:
it returns the child, empties the parent, clears `parentNode`, and
throws `NotFoundError` for a node that is not a child.

**Deviation from the Required Fix, recorded.** It says focus state
"travels in the URL fragment like the rest of the view state", and it
does — `tf=<path>`, captured and applied through `captureView` /
`applyView`. What is *not* in the export is the machinery: the
acceptance asks for "folds with counts and no focus machinery" there,
so the expand control is served-only and the deep fold keeps its label,
its counts and the whole value one click away on paper. A `tf` in a
fragment opened against an export therefore applies nothing, in
silence, exactly as a `tf` naming a table this run does not have.

**One more served-only defect this surfaced**: `tablefocus.js` was not
in `bga_view.py`'s `ASSETS`, so a served page would have 404'd on the
import and died at boot — caught by `UX-233`'s guard, which follows
every import from each entry module rather than naming a list.

**Mutations — eight, all discriminating.** Run against the committed
tree, one at a time, reverted between:

```text
N1  shapeOf stops descending                4 red  known answers + the walk
N2  the .map-table scrollbox comes back     3 red  including the booted chain
N3  the home marker is left behind          1 red  byte-identity, after back
N4  every section hides, focus included     1 red  the empty-page case
N5  the expand control ships in the export  1 red
N6  the fragment stops carrying `tf`        2 red  both directions
N7  the inner table keeps its scroll        1 red
N8  the summary reverts to "N entries"      1 red  sentence vs attributes
```

N2 is the one worth naming: it puts the field defect back exactly as it
was, and the guard that catches it is the walk over the **booted** page,
not the scan of the stylesheet — so a second route to a nested
scrollbox would redden too.

> **Correction (round 48, `UX-332`).** The last clause of that sentence
> was false, and round 45's verification proved it: a *second*
> `main .map-table { overflow-y: auto }` rule appended later in
> `style.css` restored the scrollbox with **all twenty-one clauses in
> this file green** — verified live. Both scroll clauses stopped at the
> first matching rule, and the booted walk was no protection because
> the flag it is handed (`_map_table_scrolls`) read the stylesheet the
> same first-match way: the browser saw a scrollbox while the walk was
> told there was none. `UX-332` merges every rule per selector and
> judges the cascade's winner, and both routes now redden the same
> three clauses.
