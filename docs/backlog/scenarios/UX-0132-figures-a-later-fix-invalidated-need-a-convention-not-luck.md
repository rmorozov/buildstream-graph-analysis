# UX-132: figures a later fix invalidated need a convention, not luck

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-123 (whose fix moved the figures)

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
