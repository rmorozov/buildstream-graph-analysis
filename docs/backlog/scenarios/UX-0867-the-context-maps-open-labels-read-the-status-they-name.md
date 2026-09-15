# UX-867: the context map's open labels read the status they name

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-846 | **Found by:** round 120, review 24 | **Serves:** R4 (the map says which rows are still open, truthfully) | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`docs/contributing/fixing-guide.md` §6 labels
`tools/native_trace/wrappers/_common.sh` as `UX-846 (open)`; `UX-846`
closed in round 118 and its `closed.md` row and Status line both say
so. The map's guard reads the tree's shape, not the labels' tense.

## Required Fix

`docs/contributing/fixing-guide.md` §6: the label drops `(open)`;
`tests/unit/test_the_context_map_is_the_tree.py` (or the guard that
reads §6) gains a case: every `UX-NNN (open)` label in §6 names a row
whose Status line is not Done.

## Decomposition

Input classes: a label naming an open row, one naming a closed row,
no label; the journey it extends is review 24's read of the guides.

## Out of Scope

Labels outside §6.

## Acceptance Test

The case above green on the fixed map; mutation: restore the stale
label - red.
