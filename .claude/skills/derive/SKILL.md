---
name: derive
description: Derive the viewer's module graph before moving code between files in bga/viewer/ - the import order the export inlines in, whether it is acyclic, and which symbols would cross a proposed cut. Use before any change that moves a function, constant or chapter from one viewer module to another.
---

# derive

Moving code between `bga/viewer/` modules is not a text edit. The export
concatenates the modules in the order
`tools/bga_view.py::_module_order` derives from their `import` lines,
and `_inline_module`'s whole premise is *what a module imported is now
declared above it*. `UX-199` is on file because that premise broke and
the exported report threw `ReferenceError` in `boot()` and rendered
**empty** for several rounds.

So the graph comes first, and it is derived rather than read off. The
rule lives in
[`docs/design/architecture.md`](../../../docs/design/architecture.md) —
"Which file owns what", and the inlining the Verification Log describes.
`tools/dev_js_deps.py` is the instrument; this is the procedure.

## Before you move anything

```bash
# The order the export will inline in, and a non-zero exit if a cycle
# means that order is a lie.
python3 tools/dev_js_deps.py --order bga/viewer

# Every module and what it imports.
python3 tools/dev_js_deps.py --graph bga/viewer
```

## Deciding where to cut

List the declarations and the comment block each one owns — the seam is
the prose above a function, not a line number:

```bash
python3 tools/dev_js_deps.py --declarations bga/viewer/app.js
```

Then write the proposed grouping down and ask what would have to cross:

```bash
python3 tools/dev_js_deps.py --crossings bga/viewer/app.js --groups '{
  "format":     ["QUANTITY", "duration", "bytes", "el"],
  "structured": ["columnSpecs", "buildTable", "renderTable"],
  "app":        ["render", "boot"]
}'
```

Read the direction. `structured <- format` is fine; `format <- app` and
`structured <- app` in the same answer is a cycle, and the cut has to
move. `UX-337`'s `views.js` split began exactly here and found the
chapters were **not** acyclic — three edges of one symbol each, none of
them chapter content, which is why `primitives.js` exists.

## Why not a regex, and why not an LSP

`UX-337`'s first crossing count stripped comments and strings with
regexes. The template-literal pattern, written to skip `${…}` so an
interpolated expression stayed visible, matched no template that had
one — so its opening backtick paired with a later one and everything
between vanished:

```text
app.js's declarations, raw   1,124 lines
after block comments         1,024
after line comments          1,024
after template literals        148     <- 87% of the file, silently
```

It reported a **cleaner** split than the truth. Three real crossings
were missing, each a `ReferenceError` in the export. That is `UX-340`,
and `tests/fixtures/js/interpolated.js` is the module built out of those
traps — `tests/unit/test_the_graph_is_derived_not_guessed.py` asserts
the scanner and the pattern *differ* on it, so replacing one with the
other reddens rather than passing quietly.

A language server would not have answered either question here: "which
symbols cross this cut" and "what order does `_module_order` inline
these in" are this repository's semantics, not JavaScript's.

## What it does not know

It reads the subset this repository writes — top-level `function`,
`const`, `let`, `var`, `class`, one per seam. It removes comments,
string bodies and the declaration's own parameter list; it is **not** a
scope analysis, so a name shadowed by an inner `const` still counts as a
reference. The answer is a superset of the real edges, not the exact
set — read it, do not paste it.

## After the move

The move is verified by the page, not by the tool:

```bash
python3 tools/dev_js_deps.py --order bga/viewer     # still acyclic
make lint && python3 -m pytest tests/unit/test_the_viewer_splits_along_its_seams.py
```

and the exported page's section list and byte size before and after —
see the `measure` skill for the export-size recipe.
