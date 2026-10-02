# UX-1294: the CHANGELOG's task links resolve from the repository root

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** none | **Found by:** the docs audit (2026-10-02, finding 5): ~1,595 relative links in `CHANGELOG.md` do not resolve | **Serves:** R1, R8 | **Topic:** docs | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`tools/bga_release_notes.py` copies each row's link from `closed.md`,
where it is relative to `docs/backlog/scenarios/`. Pasted into
`CHANGELOG.md` at the root, every `](UX-NNNN-....md)` points at a file
that does not exist there, so a reader clicking a release's "What
landed" gets a 404 on every item.

## Required Fix

The generator writes links relative to the file the body lands in
(`docs/backlog/scenarios/UX-....md` for `CHANGELOG.md`). Shipped rows
get the same prefix only if UX-550's digest does not cover the body;
otherwise they stay and the guard's scope is stated in the Outcome.
A guard resolves every relative link in `CHANGELOG.md`.

## Out of Scope

Rewording any shipped row.

## Acceptance Test

The link resolver over `CHANGELOG.md` reports 0 unresolved (or only
the frozen rows, counted); a fresh `bga release-notes` body's links
all resolve from the root.

## Outcome
