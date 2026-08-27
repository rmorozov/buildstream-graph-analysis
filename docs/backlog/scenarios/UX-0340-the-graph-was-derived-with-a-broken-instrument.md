# UX-340: the graph was derived with a broken instrument

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-337 (which needed it and had to build it twice), UX-199 (the export's derived module order) | **Serves:** the maintainers — the next time code moves between viewer modules | **Topic:** guards

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
