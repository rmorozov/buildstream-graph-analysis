# UX-1392: `viewer.md` says staleness is not a version comparison; `UX-1367` made it one

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 40 (2026-11-27) | **Serves:** R1 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`docs/guides/viewer.md:140`: "Staleness is `UX-249`'s contract set ... not a
version comparison." `UX-1367` (`29bb4a0a`) made a stored `analyze.json` from
another bga version stale: `tools/bga_view.py` reads `version_moved =
stored_version != this_build`, and the page says "analysed at capture by bga
0.5.0; this is bga 0.6.2, whose analysis may differ". That commit touched no guide.

## Required Fix

The sentence names both triggers: a moved contract set, and a stored analysis
from another `bga` version.

## Out of Scope

The staleness rule itself.

## Acceptance Test

A guard reads `viewer.md`'s staleness sentence against `bga_view.py`'s two
triggers; dropping either from the sentence reddens it.
