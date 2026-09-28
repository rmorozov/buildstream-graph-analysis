# UX-1085: the residue scan misses non-ASCII identifiers

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1069 | **Found by:** the owner's #298 re-review at 156d7436, finding 2 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`bundle._WORD = re.compile(r"[a-z0-9]+")`, so `_residue_hits()` cannot
match a recorded original such as `café` in a kept string - a
regression from the previous escaped-string alternation. A residue
scan that silently skips non-ASCII originals approves bundles it
should refuse.

## Required Fix

Replace `_WORD`'s matching/indexing with a Unicode-aware strategy in
`bga/bundle.py` (matching on word characters generally, not the ASCII
class) so a non-ASCII original is indexed and matched the same way an
ASCII one is, including at the streamed-chunk boundary UX-1069's
chunked residue read introduced.

## Out of Scope

The map's write ordering (UX-1086); the numeric-credential default
(UX-1084).

## Acceptance Test

`tests/unit/test_the_residue_scan_matches_non_ascii_identifiers.py`:
a recorded original such as `café` kept in a member (1) wholly within
one residue chunk and (2) split across a chunk boundary each trip
`_residue_hits()`. Mutation: revert `_WORD` to `[a-z0-9]+`, and both
cases pass through clean.

## Outcome
