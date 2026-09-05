# UX-302: the mapping made law — no raw JSON that is not on purpose

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-267, UX-277 (the shape dispatch and the fold this codifies) | **Serves:** R1 — every reader of the page | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The style guide (round 41, `docs/design/styleguide.md` §1) turns the
user's rule — raw JSON on the page is a defect unless deliberate —
into a dispatch table: published shape + hint → the one control that
may render it. `UX-267` already killed the wall of `<pre>`; what
remains is to make the mapping *law*: the deliberate escapes named
(the labeled deep-fold, and a per-section "view as JSON" toggle that
does not exist yet), and everything else guarded shut so the next
section cannot reopen it.

## Required Fix

Every render path resolves through the §1 table; the per-section
"view as JSON" toggle is built (served and export, since it is the
issue-pasting affordance); `JSON.stringify` in viewer modules is
allowlisted to `data-raw`, the copy path and the labeled fold; and
the boot guard walks the real page asserting zero raw-JSON text
nodes outside the two deliberate controls. A shape the table does
not cover renders as the labeled fold *and* fails a dev-mode
console check — the gap is a design task, not an improvisation.

## Out of Scope

- New controls beyond the toggle (`UX-303` carries the drawings) —
  this item is the dispatch and its guards.
- Changing any payload — the mapping consumes what is published.

## Acceptance Test

Booting the golden and 1,202-element pages: zero unlabeled raw-JSON
text nodes (guard walks every text node for `{"`-shaped content
outside the two controls); the toggle round-trips (section JSON
shown, hidden, document unchanged — serialized compare); mutation:
rendering one object map as `<pre>` reddens the walk; an unmapped
shape in a probe schema lands in the fold and trips the dev check.

## Outcome

🟢 **Done.** §1 is a function now, both of its escapes are named, and
the guard reads the booted page rather than the source.

**Where the mapping lives.** `bga/viewer/shapes.js` — `classify(value,
{severity, columns, depth, nestLimit, inlineFields, inlineItems})`
returns one of eight control names or `UNMAPPED`. It imports nothing,
takes no DOM, and takes the thresholds as arguments rather than
re-declaring them, so `UX-273`'s guard still reads them out of
`app.js`. `renderStructured` and `renderSection` both dispatch on its
answer; the shape tests that used to live in their `if` chains are
gone.

**The shape that had no row, and the improvisation it was getting.** A
**mixed** array — objects and scalars together. In a cell it produced
one row shape per item; at section level it hit
`Array.prototype.toString` and rendered `[object Object], 2`, which is
`UX-277`'s leaf in a second place. It is now `UNMAPPED`: the value
folds — labelled, counted, one click from the whole thing — and
`noteUnmapped` warns on the console naming the payload path and
pointing at §1. Both halves matter: a silent fold hides the design
gap, and a warning with nothing drawn hides the value.

**The toggle.** `bga/viewer/rawjson.js`. Per section, in the heading
beside the collapse caret; the JSON goes under `data-raw-json`,
pretty-printed, and clicking again removes it. It works in the export,
because the export is who needs it — the person a report was *sent* to
has one HTML file and no payload beside it. The source is held in a
`WeakMap` keyed on the section rather than serialised into the
document, so nothing is paid for until someone asks (and `chapters.js`
re-sorting the sections does not disturb it).

**Coverage, stated rather than implied:**

```text
                sections   with a toggle
golden                28              15
macro_micro           37              17
```

The other 13 and 20 are the sections the page *composes* — `decision`,
`overview`, `evidence`, `horizon`, `whatif`, the drawn critical path,
and one per element. They have no single payload slice, and get no
control rather than one showing the wrong thing.

**The walk.** `tests/unit/test_the_mapping_is_law.py` boots both
exported pages under `file://` and walks every element's own text for
JSON-shaped content, three times: closed, with **every** toggle open,
and closed again.

```text
                    nodes  with text  sections  toggles  raw-JSON text
golden               2082        1174        28       15              0
macro_micro          3497        1972        37       17              0
```

**Two things the first draft of the guard got wrong**, both found by
mutating rather than by reading:

- It walked `body`, and the report root is
  `getElementById("report")`, which the probe hands back **detached**.
  Filling the page with `<pre>{…}</pre>` left it green. `UX-235`'s
  lesson, met again: read the document the page assembles.
- It walked only with the toggles **closed** — so the page held no raw
  JSON at all, and the clause was asserting an empty document rather
  than an allowlist. Removing `data-raw-json` from the toggle's box
  passed all 19 clauses. The open sweep is what tests the allowlist,
  and the regex had to widen from `{"` to `{\s*"` because the toggle
  pretty-prints.

**The falsification round**, against the committed tree:

```text
M1   object map renders as <pre>                  8 clauses red
M2   toggle box loses its data-raw-json label     2 red   (green before the open sweep)
M3   hiding leaves the box behind                 4 red
M4   a mixed array classifies as a table          4 red
M5   the dev check says nothing                   1 red
M6   a new JSON.stringify in a new function       1 red
M7   the guide loses a row                        1 red
M8   the walk reads body instead of the report   10 red
M9   boot never wires the toggles                 8 red
M10  an allowlisted site disappears               2 red + 3 errors
M11  shapes.js dropped from ASSETS               green here, red in
     test_the_page_obeys_its_own_policy.py, which owns that surface
```

**The allowlist**, both directions. Every `JSON.stringify` in
`bga/viewer/*.js` is resolved to its enclosing function and matched
against five entries — `data-raw` (an attribute, never text), the
labelled fold, the toggle, `rowJson` (the clipboard) and
`writeCollapsed` (`localStorage`). A new site in a new function
reddens; so does an allowlisted entry that no longer exists, because a
stale permission is how an allowlist stops meaning anything.

**What the guide gained.** Two rows it was missing — array of arrays
(`UX-290`'s tuple table) and the mixed array as an explicit
*non*-row — a paragraph naming `shapes.js` as where the table lives,
and the correction that there are now **two** deliberate raw-JSON
sites rather than one. The architecture's viewer axis names both new
modules.

**Where the dispatch does not reach, stated plainly.** `classify` is
asked for every *structured* value — every object and every array, in
a cell or as a section. Scalars go through `quantity()` and `data-raw`,
which §1's top four rows describe and which no path here changed; the
hand-built sections in `views.js` draw named published fields with
chosen controls and are not dispatched. What proves nothing escaped is
the walk, not the call graph.

**Cost.** The export grew by 5,315 B on both committed runs — modules
+4,812, styles +567 — and the page bound moved 180,000 → 186,000 B, the
first move since the page/data split was drawn. The page grew by
exactly what the source grew by on both runs, which is that split
working.

**Out of scope, held.** No payload changed, and no control beyond the
toggle was built — `UX-303` carries the drawings.
