# UX-132: figures a later fix invalidated need a convention, not luck

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-123 (whose fix moved the figures) | **Topic:** docs

## Motivation

UX-123's exec-chain collapse changed `examples/06` from 822 to 813
processes and the fdsdk trace head from 1833 to 1812 — correctly. But
UX-107's headline ("merges 1644 records into **822** processes", "the
fdsdk capture re-renders byte-identically") and UX-108's fdsdk counts
("+734 observed exits") now describe a parser that no longer exists,
unannotated — and UX-112, committed *after* UX-123, quotes 822 fresh.
When UX-118 invalidated UX-106's explanation, it went back and
annotated the old text ("kept folded beneath it: a wrong explanation
that was believed for a while is worth being able to recognise again");
UX-123 did not, so the convention exists only where one author
remembered it.

The style guide already splits this cleanly for *documents* (rule 2:
docs are current, findings are history). Task files sit in between:
they are history, but history that later work can falsify, and a reader
has no way to tell a stood-the-test-of-time figure from a superseded
one.

## Required Fix

1. Annotate the three invalidated figure sites (UX-107, UX-108,
   UX-112's 822s) the way UX-118 annotated UX-106: the old figure
   stays, with one line naming what changed it.
2. Write the convention into the fixing guide: *a fix that changes a
   number a previous task file quotes annotates that file in the same
   commit* — grep-able (`git grep <old figure> docs/backlog/scenarios`)
   as part of the fixer's checklist, since this one is judgment-shaped
   and cannot be a hard test.

## Out of Scope

- Rewriting historical figures (the annotation preserves them; that is
  the point).

## Acceptance Test

The three sites carry the annotation naming UX-123; the fixing guide
names the convention with UX-106/UX-118 as the worked example; and a
spot-grep for `822` across the three files finds no un-annotated
instance presented as current.

## Fix Implemented

The three sites carry the annotation, in the shape `UX-118` used on
`UX-106` — the old figure stays, with one line naming what changed it:

1. **`UX-107`**, two places: the merge table's 822s (now 813 after
   `UX-123`'s exec-chain collapse), and the "re-parses byte-identically"
   acceptance clause, which was a property of that parser and is
   deliberately no longer true.
2. **`UX-108`**, two places: the overhead table's 822, and the +734
   observed exits / 127,632 processes, both pre-collapse counts. Noted
   there that the *finding* is sharpened rather than weakened —
   exec'd processes are exactly what the hook cannot see.
3. **`UX-112`**, whose 822 was stale *when written*: `UX-123` landed one
   commit earlier. That is the clearest possible statement of why the
   convention needed writing down.

The convention is now item 5 of the fixing guide's Definition of Done,
with `git grep <old figure> docs/backlog/scenarios` as the mechanic and
`UX-106`/`UX-118` as the worked example. It is a checklist item rather
than a test because it is judgment-shaped — which figure is presented as
current, and which is a record of what was measured, cannot be decided
by a regex.

## Verification Log

Done 2026-08-19.

```text
$ git grep -n "822" docs/backlog/scenarios/UX-0107*.md \
      docs/backlog/scenarios/UX-0108*.md docs/backlog/scenarios/UX-0112*.md
```

Every hit in those three files now sits under an annotation naming
`UX-123` and the corrected figure. Hits elsewhere in the backlog
(`UX-32`, `UX-37`, `UX-38`, `UX-45`, `UX-46`, `UX-56`) are deliberately
untouched: they are verification logs recording what a real capture
measured on the day, which is history the style guide's rule 2 protects
and this task's Out of Scope names explicitly.
