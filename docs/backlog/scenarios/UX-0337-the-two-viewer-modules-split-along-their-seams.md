# UX-337: the two viewer modules split along their seams

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-336 (which measured the cost and deferred this), UX-199 (the export's derived module order), UX-294 (the module map) | **Serves:** the maintainers — edit cost, not page cost | **Topic:** guards

## Motivation

`UX-336`'s fifth lever, split out of it rather than rushed inside it.
The two largest viewer modules are long enough that every edit pays a
long read:

```text
bga/viewer/app.js     2,614 lines
bga/viewer/views.js   2,484 lines
                      -----
                      5,098 of the viewer's 9,603
```

`views.js` already carries its chapter seams as comment rules — band,
trend, blast box, overview, the two graphs, the decision, the element
object — so *where* to cut is not the open question.

**What is.** The export inlines modules by concatenating them in
dependency order (`tools/bga_view.py::_module_order` walks `import`
lines; `_inline_module` strips `export ` and blanks the imports). Two
consequences the split has to respect and `UX-336` did not have room to
establish:

- the order must be **acyclic**. A chapter that both calls into and is
  called from what stays in `views.js` would produce a cycle, and the
  inliner's whole premise is "what it imported is now declared above
  it";
- `export * from` and bare `export { a, b };` re-export forms are
  invisible to `_module_order` and survive `_inline_module` verbatim —
  so the tidy "keep `views.js` as an index" shape does not work, and
  the two importers (`app.js`, `nav.js`) have to name the new modules.

`UX-199` is on file because exactly this inlining shipped an export
that threw `ReferenceError` in `boot()` and rendered **empty** for
several rounds. That is the risk this item is about.

## Required Fix

The dependency graph between the chapters is derived (not guessed)
before anything moves; the two files split along seams the graph shows
are acyclic; `app.js` and `nav.js` import the new modules directly.
Page cost stays neutral — the export inlines either way — and the
export's byte size is asserted before and after. `UX-294`'s module map
gains the new files in the same commit.

## Out of Scope

- Changing any rendering behaviour. This is a move, and the diff should
  read as one.
- Splitting anything else in `bga/viewer/`. The other five modules are
  486 lines and under.

## Acceptance Test

No file in `bga/viewer/` over 1,500 lines; the exported page boots
under the DOM shim and renders the same section list as before (asserted
against a before/after capture, not a literal); the export's byte size
moves by less than 1%; `_module_order` returns an acyclic order
containing every new module (asserted); the module map names them.
