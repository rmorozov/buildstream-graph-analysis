# UX-177: five corners round 18 verified its way into

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-164, UX-166, UX-168 (the landings these trail) | **Topic:** store

## Motivation

Small, each demonstrated or traced by the round-18 review; none
reopens its parent:

1. **`@stamp` resolution has no exact-match short-circuit.** The
   store's own same-second disambiguation (`stamp`, `stamp-01`) makes
   one full stamp a strict prefix of its sibling, and
   `resolve_snapshot` then refuses the *exact* name as ambiguous —
   reproduced: the walk-back hint printed `@20260820T153932Z` and
   pasting it raised `StoreError: matches 2 snapshots`. An exact match
   should win before prefix matching.
2. **The casd config precedence has a narrower residual corner**
   (UX-166's own class): bst selects the config *file* by existence
   and stops; bga's loop falls through on missing *key*. A
   `buildstream2.conf` without `cachedir` beside a `buildstream.conf`
   with one makes bga answer a directory bst is not using. Match the
   file-selection rule, and test the corner.
3. **`build_outcome`'s new three-way counts have no consumer**
   (`bst_extract_run.py:447-450`): the violation derives from
   `build_queue` instead. Wire the violation to the recorded counts or
   drop the duplication — two sources for one number is how drift
   findings start.
4. **The `.size` memo goes stale on re-extraction**: `bga extract`
   into an existing `<snapshot>/run` overwrites files in place, which
   moves no directory mtime, so the memoised size survives wrong.
   Extraction into a snapshot should drop the memo.
5. **CRLF nit in both streaming readers**: `rstrip("\n")` leaves `\r`
   on header lines where `splitlines()` would not — irrelevant to
   hook-written logs, one token to fix while someone is in the file.

## Required Fix

As numbered. Item 1 is the user-visible one and belongs first (it
breaks the paste-and-go hint UX-164 just built).

## Out of Scope

- Anything requiring new features; these are corrections inside landed
  behavior.

## Acceptance Test

`resolve_snapshot("@<full-stamp>")` on a store with `stamp` and
`stamp-01` returns the exact one (mutation: removing the
short-circuit reddens it); the config corner test asserts bga and
bst agree on both file layouts; one source of truth for the failed-run
counts (grep proves the other gone); re-extraction drops `.size` and
`--list` shows the new size; both readers `splitlines()`.

## What was built

1. **An exact stamp wins before prefix matching.** The store's
   same-second disambiguation makes `<stamp>` a strict prefix of
   `<stamp>-01`, so `resolve_snapshot` refused the exact name as
   ambiguous - and the walk-back hint prints exactly that name. A
   genuinely ambiguous prefix is still refused; only the exact match
   short-circuits.
2. **The casd config file is selected by existence, then read.** bst
   picks the *file* and stops; bga's loop fell through on a missing
   *key*, so a `buildstream2.conf` without `cachedir` beside a
   `buildstream.conf` with one made the check answer a directory bst is
   not using.
3. **One number, one source.** `build_outcome`'s three-way counts had
   no consumer - the `build_failed` violation derives them from
   `queue_summary` - so the copy is gone rather than wired up.
4. **The size memo does not survive a re-extraction.** An extraction
   into an existing snapshot overwrites files in place, which moves no
   directory mtime, so `UX-168`'s memo - keyed on exactly that - would
   have survived a re-extraction that changed the size. The producer
   drops it, because the producer is what knows.
5. **CRLF in both streaming readers.** `rstrip("\r\n")`, so a CRLF
   trace parses identically to an LF one, which `splitlines()` (used by
   the string-taking wrappers) already did.

Twelve guards in `tests/unit/test_round18_tail.py`. Four mutations,
each red; item 3's guard is a source check and is labelled as one -
there is nothing left to call.
