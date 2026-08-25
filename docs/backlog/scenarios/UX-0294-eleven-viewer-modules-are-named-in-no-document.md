# UX-294: eleven viewer modules are named in no document

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the maintainers, and the next reader of `bga/viewer/` | **Topic:** docs

## Motivation

Found by review 3, checklist item 4 — *what shipped since the last
review that no document names.* The viewer is twelve ES modules; the
architecture names two of them:

```text
module              times named in docs/design/architecture.md
app.js                     1
chapters.js                1
focus.js                   0
nav.js                     0
perfetto.js                0
perfetto_page.js           0
questions.js               0
sql.js                     0
tables.js                  0
trace_context.js           0
views.js                   0
viewstate.js               0
```

`views.js` is 2,411 lines and draws every section the page has;
`nav.js` is the rail, the anchors, the collapse and the jump box;
`viewstate.js` is the fragment contract `UX-211` and `UX-225` publish
links against. None of them appears in any document — the reader who
opens `bga/viewer/` is told what the *page* does and has to derive
which file does it.

The Python side is not in this position: `bga/`'s modules are listed,
and the Verification Log records the listing being updated as modules
arrive (`findings.py`, `correlate.py`, `tools_dispatch.py`).

This is the axis `UX-241` named — documentation drifting behind a
subsystem — caught this time by the cadence rather than by a review of
the whole document.

## Required Fix

1. The architecture's viewer section names the modules and what each
   one owns — a listing, not a description of each: the principles are
   already written, and what is missing is the map from principle to
   file.
2. A guard, if it is cheap: every `bga/viewer/*.js` is named somewhere
   in `docs/`, the same shape as the contract-home guard
   (`test_the_documents_keep_up_with_the_contracts.py`).

## Out of Scope

- Describing each module's internals. The file is the description; the
  document's job is to say which file to open.
- `tools/`'s modules. Declined because they are already listed with a
  sentence each in `bga --help` and in the alias table `UX-67` added to
  the architecture, so the gap this item names does not exist there.

## Acceptance Test

Every module under `bga/viewer/` is named in at least one document
under `docs/`, and a guard says so.
