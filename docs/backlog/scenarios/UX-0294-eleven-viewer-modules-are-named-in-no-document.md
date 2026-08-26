# UX-294: eleven viewer modules are named in no document

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Serves:** the maintainers, and the next reader of `bga/viewer/` | **Topic:** docs

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

## Outcome

🟢 **Done.** The architecture carries a `### Which file owns what`
table — sixteen rows, one line each, from `app.js` to `style.css`.

**The count had moved, and the gap had not.** Re-measured before
writing anything: every module is now named *somewhere* under `docs/`
(the backlog files and the Verification Log mention them in passing),
so the acceptance as filed — *named in at least one document under
`docs/`* — was **already true of all fifteen**. But
`docs/design/architecture.md`, the document a reader of `bga/viewer/`
actually opens, named only eight; `views.js` at 2,400 lines, `nav.js`,
`viewstate.js`, `tables.js`, `focus.js`, `sql.js` and
`perfetto_page.js` appeared **zero** times.

So the guard is on the *map*, which is what the Required Fix asks for,
rather than on the acceptance sentence. A guard on the latter would
have been green the day it was written and green forever — the
non-discriminating shape this repository keeps finding in its own work
(`UX-297`'s M2, `UX-312`'s dead queries). The weaker clause is kept
beside it so a module that leaves the map *and* every other document
at once reddens twice rather than once.

**Falsification.** Four mutations against the committed tree:

```text
V1  the largest module leaves the map        1 guard red
V2  an entry that only repeats the filename  1 red
V3  the map names a file that does not exist 2 red
V4  a new module ships with no entry         2 red
```

V4 is the one the item exists to prevent, and it reddens in both
directions at once.

**Recorded:** the first attempt at V2 and V3 measured nothing, because
`git checkout -- docs/` reverted the *uncommitted* map between
mutations and left the guard asserting against a document with no
table at all. Mutation testing runs against a committed tree; this is
the second time that rule has earned its place this round.

