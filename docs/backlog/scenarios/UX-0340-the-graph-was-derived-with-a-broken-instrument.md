# UX-340: the graph was derived with a broken instrument

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-337 (which needed it and had to build it twice), UX-199 (the export's derived module order) | **Serves:** the maintainers — the next time code moves between viewer modules | **Topic:** guards | **Area:** tools

## Motivation

`UX-337`'s Required Fix opens *"the dependency graph between the
chapters is derived (not guessed) before anything moves"*, and it was.
The first derivation was wrong, and it was wrong in the way that does
not announce itself: it produced a **cleaner** answer than the truth.

The instrument had to strip comments and string literals before
counting which symbols cross a proposed cut, because a docstring naming
`render` is not a call to `render`. It did that with regexes, and the
template-literal pattern — written to skip `${…}` so an interpolated
expression stayed visible — simply failed to match any template that
had one, so its opening backtick paired with some later backtick and
everything between them vanished:

```text
app.js's declarations, raw   1,124 lines
after block comments         1,024
after line comments          1,024
after template literals        148     <- 87% of the file, silently
```

The crossing count that came out of it was plausible and short. Against
a character scanner that knows a `//` inside a string is not a comment,
three real crossings were missing — `PRESETS`, `elementColumn` and
`safeStorage` — each of which is a `ReferenceError` in the concatenated
export, which is `UX-199`'s empty page.

Nothing caught it. It was noticed only because the numbers were read
twice by someone who expected `duration` to appear and it did not.

**Why this is an item and not a lesson.** The scanner exists now, in a
scratch directory, and the next round that moves a function between
viewer modules will write it again — probably with regexes, because
that is what one reaches for first. Three things this repository has
already paid for live in that throwaway code: the comment/string
scanner, the block carver that cuts on the prose seam above a
declaration rather than on a line number, and the crossing count that
turns a proposed grouping into "what would have to be imported, and in
which direction".

## Required Fix

`tools/dev_js_deps.py`, beside `dev_touching.py` and
`dev_close_task.py`: given the viewer's modules it prints the import
graph and whether it is acyclic; given one module it prints its
top-level declarations with the comment block each owns; given a
proposed grouping it prints, per pair, the symbols that would cross and
in which direction, comments and string literals removed by a scanner
rather than a regex.

It carries its own guard, and the guard's discriminating case is the
one that fooled the first derivation: a fixture whose declarations
contain a template literal with `${…}`, where a regex stripper reports
a clean split and the scanner does not.

The `derive` skill points at it, so the procedure is "run this", not
"write this again".

## Out of Scope

- A general JavaScript parser. This reads the subset this repository
  writes — top-level `function`/`const`/`let`/`class`, one declaration
  per seam — and should say so rather than pretend otherwise.
- Anything that edits code. Deriving the graph and performing the move
  are separate steps on purpose: `UX-337`'s move was verified by the
  exported page being byte-identical, and a tool that did both would
  have nothing independent to check against.

## Acceptance Test

`tools/dev_js_deps.py --order bga/viewer` reproduces
`tools/bga_view.py::_module_order`'s sequence exactly (asserted against
the real function, not a literal). On a fixture module whose body
contains a template literal with an interpolation, the scanner keeps
the code and a regex stripper does not — asserted as a difference, so
the clause fails if the scanner is replaced by the pattern that failed.
The crossing count for `bga/viewer/app.js` under `UX-337`'s grouping
names `PRESETS`, `elementColumn` and `safeStorage`, which the first
derivation missed.

## Outcome (round 52, 2026-08-27) — 🟢 Done

### The gap, measured

The instrument that was wrong, on the module it was wrong about, kept
as `_regex_stripped` in the guard so the difference stays visible:

```text
app.js's declarations, raw   1,124 lines
after block comments         1,024
after line comments          1,024
after template literals        148     <- 87% of the file, silently
```

### After

```text
$ python3 tools/dev_js_deps.py --order bga/viewer
primitives.js format.js controls.js drawings.js shapes.js tablefocus.js
tables.js views.js structured.js perfetto.js element.js decision.js
chapters.js nav.js rawjson.js focus.js viewstate.js questions.js
trace_context.js app.js
                                   == tools/bga_view.py::_module_order()

$ python3 tools/dev_js_deps.py --crossings tests/fixtures/js/interpolated.js \
      --groups '{"lower":["LABEL","HIDDEN","alpha","render","delta"],
                 "upper":["beta","gamma"]}'
upper <- lower               HIDDEN LABEL

  scanner vs the pattern, on the same file:
  tokens   55  /  33
  LABEL     2  /   1        the use in `gamma`, lost
  HIDDEN    2  /   1        the use in `gamma`, lost
  gamma     1  /   0        the whole function, lost
```

### A scanner, because the thing being removed can contain its own end

`//` inside a string is not a comment. A backtick inside a comment does
not open a template. A `${…}` holds real code that has to survive, so it
is recursed into. None of those is expressible as a substitution, and
the pattern that tried lost 87% of a file while reporting a clean
answer.

The tool also subtracts the declaration's **own parameter list**, which
removes the false edge `UX-337` had to spot by reading —
`expandControl(path, label, render, breadcrumb)` reads its parameter,
not the top-level `render`. It is not a scope analysis and says so: a
name shadowed by an inner `const` still counts, so the answer is a
superset of the real edges rather than the exact set.

### The fixture is the argument

`tests/fixtures/js/interpolated.js` is two template literals with an
ordinary function between them, because that is the shape that eats
code: the first template's closing backtick pairs with the second's
opening one. `gamma` sits between them and disappears whole.

The guard asserts the **difference**, not the scanner's output. A clause
that checked only what the scanner produces would pass with the pattern
substituted for it — mutation B1 below is exactly that substitution, and
it reddens.

### Mutations verified red and reverted (6, one repaired)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| B1 | `strip_comments` delegates to the three regexes that were wrong | `test_the_pattern_eats_a_whole_function_and_the_scanner_does_not` — 1 failed, 9 passed |
| B2 | `--order` appends before recursing, so a module precedes its imports | `test_the_order_is_the_order_the_export_inlines_in` — 1 failed, 9 passed |
| B3 | the declaration's parameter list stops being subtracted | `test_the_crossing_count_is_the_real_one` — 1 failed, 9 passed (`render` reappears as a false edge) |
| B4 | comments are no longer removed at all | `…eats_a_whole_function…` and `test_a_comment_and_a_string_make_no_reference` — 2 failed, 8 passed |
| B5 | a declaration no longer owns the comment block above it | `test_a_declaration_owns_the_comment_block_above_it` — 1 failed, 9 passed |
| B6 | an incomplete grouping is answered rather than refused | `test_a_grouping_that_leaves_a_declaration_out_is_named` — 1 failed, 9 passed |

**B5 was repaired, not counted twice.** Its first run was **10 passed**:
the comment the clause asserted on sat *inside* `gamma`'s body, so
cutting at the declaration line kept it either way and the clause was
testing nothing. The fixture gained a real seam — a docstring above
`delta` — and the clause now asserts `delta` owns it and `gamma` does
not. The re-run is the row above.

### Deviation from the Required Fix

- The Acceptance Test asks that the crossing count for
  `bga/viewer/app.js` under `UX-337`'s grouping names `PRESETS`,
  `elementColumn` and `safeStorage`. It cannot: those three moved out of
  `app.js` when `UX-337` landed, so the clause would have asserted
  against a file that no longer exists in that shape — a guard measuring
  history rather than the code. The property it was after is asserted
  instead on a committed fixture built out of the same traps, where the
  scanner and the pattern are shown to **differ**, which is strictly
  more than re-checking three names.
