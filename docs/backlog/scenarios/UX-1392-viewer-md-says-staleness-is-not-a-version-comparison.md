# UX-1392: `viewer.md` says staleness is not a version comparison; `UX-1367` made it one

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 40 (2026-11-27) | **Serves:** R1 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_viewer_guide_names_both_staleness_triggers.py`

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

## Outcome

**Gap measured** (`sed -n 140,141p docs/guides/viewer.md`, base `7e7b5db3`):
"Staleness is `UX-249`'s contract set ... not a version comparison", while
`bga_view.analysis_source` stales on `moved or version_moved`. No existing
guard read the sentence (`grep -rn viewer.md tests/unit/`: ceilings, counted
figures, comparison advice only).

**Close measured**: the sentence now reads "Stale means one of two triggers:
the contract set `UX-249` moved ..., or the stored analysis came from another
bga version (`UX-1367`)". `pytest tests/unit/test_the_viewer_guide_names_both_staleness_triggers.py`:
2 passed.

| Mutation | Result |
|---|---|
| sentence: `contract set` -> `set` | 1 failed, 1 passed |
| sentence: `another version of bga` -> `another release` | 1 failed, 1 passed |
| `bga_view.py` stale: `moved or version_moved` -> `moved` | 1 failed, 1 passed |

Review rework (2026-11-27): the code-side guard was a source regex that could not see `or True` on the `stale` expression. It now calls `analysis_source` with stored docs differing only in contract set, only in version, and in neither (stale True/True/False); renamed to the claim; the sentence regex is bounded to one sentence. Mutations: `or True` -> 1 failed, 3 passed; `moved or version_moved` -> `moved` -> 1 failed, 3 passed; drop `moved` -> 1 failed, 3 passed.
