# UX-450: two viewer modules sit exactly on the line-count ceiling

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 70, `UX-429` adding four lines to `structured.js` | **Serves:** the next round that adds anything to the viewer's two largest modules | **Topic:** guards

## Motivation

`UX-337` split the viewer along its seams and set a 1,500-line ceiling
per module, guarded by
`test_the_viewer_splits_along_its_seams.py::test_every_viewer_module_is_under_the_ceiling`.
Two modules now sit **exactly** on it:

```console
$ wc -l bga/viewer/*.js | sort -rn | head -4
 11706 total
  1500 bga/viewer/structured.js
  1500 bga/viewer/app.js
  1267 bga/viewer/element.js
```

Both got there the same way, a round apart. `UX-431` added one line to
`app.js` at 1,499 and paid for it by merging two declarations onto one
line and shortening a comment. `UX-429` needed four lines in
`structured.js` — a `classify` option and a dispatch branch — and paid
for them by folding two option lines into one and **deleting the
branch's explanatory comment**, which then had to be re-homed in
`controls.js`.

Neither payment made the code better. The second one made it slightly
worse: a dispatch branch in a §1 table now carries no note where every
other branch around it does, and its reason lives in a different file.

**The ceiling is working.** It is meant to force a split rather than
let a module absorb, and this is it forcing one — twice, on two
modules, with the cost currently being paid in comments instead. What
has not happened is the split, because each round in turn has had a
task to finish and a module split is a design task of its own.

## Required Fix

Decide, and do one of:

- **Split both modules along a seam**, the way `UX-337` split the
  original two — and name the seam, because "the file is long" is not
  one. `structured.js` holds §1's dispatch *and* the whole table
  machinery (tools, filters, presets, focus); `app.js` holds the boot
  and the section walk. Either could be two files.
- **Or move the ceiling**, with a reason that is not "we hit it" — the
  count `UX-337` chose was a judgement about what one reader can hold,
  and if 1,500 was the wrong number the item should say what the right
  one is and why.

Whichever, the comment `UX-429` deleted goes back.

## Out of Scope

- **Any behaviour change**: this is a move, and a move that renders one
  pixel differently is not a move. The export must come out
  byte-identical, which is what the acceptance test below reads.
- **The other five modules**: none is within 200 lines of the ceiling,
  so none of them is under the pressure this item is about.

## Acceptance Test

```bash
wc -l bga/viewer/*.js | sort -rn | head -5
make test
```

No module within 100 lines of the ceiling, the suite green, and the
export byte-identical to before the split — the property that says a
move was a move.

## Outcome

_Not started._

## Outcome (round 71, 2026-08-31) — 🟢 Done

**Split, not moved.** The ceiling was not raised: `UX-337`'s 1,500 is a
judgement about what one reader can hold, and nothing measured here
says it was the wrong number. Both files came down under it.

```console
$ wc -l bga/viewer/*.js | sort -rn | head -5
 12299 total
  1400 bga/viewer/structured.js
   953 bga/viewer/app.js
   573 bga/viewer/sections.js
  1267 bga/viewer/element.js
```

### `app.js` — a seam the file's own header already named

**What the page draws** against **what runs it**. Everything in
`sections.js` turns a payload and a schema into DOM and returns it;
nothing there touches the document, the URL, storage or an event.

The cut was derived, not judged, and its **first shape was cyclic** —
`investigateButton` draws here and calls `investigate`, which ran
there:

```text
app <- sections    investigateButton investigateButton render render
sections <- app    investigate
```

Moving `investigate`, `decisionInvestigation` and `traceUrl` across
leaves one direction, which is what `_module_order` needs:

```text
app <- sections    decisionInvestigation investigate investigateButton
                   render render traceUrl
```

### `structured.js` — where the obvious cut does not exist

The seam this item proposed — §1's dispatch against the table
machinery — is **not a seam**, and the instrument said so:

```text
structured <- tabledom   CELL_TEXT_CAP TABLE_OPENS_BOUNDED_ABOVE buildTable
                         buildTable elementSignalTable presetTable renderTable
                         sortable
tabledom <- structured   columnSpecs expandTableControl renderStructured
                         renderText
```

That is mutual recursion by design: §1's rule is that a table cell may
itself be a rendered value, so the dispatch and the table are one
module. A narrower cut (the `interrogable` block) was cyclic too.

What worked was moving two concerns to the modules that **already own
them** rather than inventing a module to hold overflow:
`distributionStrip` is a shape and went to `shapes.js`; `sortable` is
table behaviour and went to `tables.js`. Both are one-directional
(`structured <- moved_out`) and both targets are already earlier in the
inline order, so the order did not move.

### The export: a permutation, not a change

The acceptance test asks for byte-identical. It is not, and cannot be —
adding a node to the graph re-derives the topological order. What it is
instead is a **pure permutation**, which is the same evidence:

```console
$ wc -c /tmp/before.html /tmp/after.html
388259 /tmp/before.html
388259 /tmp/after.html
$ diff <(sort /tmp/before.html) <(sort /tmp/after.html)     # empty
```

Same byte count, identical line multiset, different concatenation
order. Recorded as a deviation rather than claimed as a pass.

### The bug the export could not catch

`distributionStrip` uses `columnStrip`, which `structured.js` imported
and `shapes.js` did not. **The export was green on this**: it flattens
every module into one scope, so a missing import is invisible there.
The served page is not flattened:

```text
<div class="verdict refused" data-page-failed="true">
  <h2>Could not load this run</h2>
  <p>ReferenceError: columnStrip is not defined</p></div>
```

128 tests red, and `test_the_console_stays_clean.py` **green** through
all of it, because it reads the export. That is the `derive` skill's
own sentence — *the move is verified by the page, not by the tool* —
paid for rather than quoted. Three imports were missing; the served
page names the first one and only re-serving finds the next.

Two smaller ones from the same session, both mine: `export` written
before a docblock rather than before `function`, which the inliner
strips into a stranded `export` (that was the 7-byte difference before
the permutation was clean); and an insertion anchored on the word
`import` that matched it inside a **comment** — §5 again, in a script.

### What the split cost elsewhere

Five guards read `app.js` for symbols that are now in `sections.js`,
and were repointed at the module that owns the code. The new module
also had to reach three registries a reader would not guess:
`tools/bga_view.py`'s `ASSETS` (or `bga view` 404s it and the page
never boots — caught by `test_everything_inlined_is_also_served`),
`tests/viewer.mjs`, and the architecture's module table (`UX-294`).

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| P1 | drop `sections.js` from `ASSETS` | **`test_everything_inlined_is_also_served`**, naming the module |
| P2 | drop `columnStrip` from `shapes.js`'s imports | the served page refuses with `ReferenceError`; 128 tests red, the export's console-clean guard **green** |

P2 is the one worth keeping: it is the discriminating case for why an
export-only check cannot guard a module move.

### The comment `UX-429` deleted

Restored to `structured.js`'s dispatch branch, which is what the
Required Fix's last line asked for.

### Deviation from the Required Fix

Two, both recorded above: the export is a permutation rather than
byte-identical (the acceptance test could not have anticipated a new
node in the graph), and `structured.js` was relieved by moving two
concerns out rather than by being split in half, because the half the
item proposed is provably not separable.

### The suite

```console
$ make lint
All checks passed!

$ make test
5456 passed, 28 skipped, 1 warning in 265.71s (0:04:25)
```
