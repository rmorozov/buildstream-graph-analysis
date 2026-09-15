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

## Outcome

**Gap measured.** §6 (lines 173-481) carried exactly one `UX-NNN
(open)` label: `(UX-846 (open))` on the
`tools/native_trace/wrappers/_common.sh` row (line 414,
`grep -n "UX-[0-9]\+ (open)" docs/contributing/fixing-guide.md`
after slicing to §6). `UX-846`'s Status line reads `🟢 Done` and its
`closed.md` row confirms it (round 118). No other `(open)` label
exists in §6, so the sweep found one stale citation, not several.

**Close measured**,
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/unit/test_the_context_map_is_the_tree.py`:

```text
tests/unit/test_the_context_map_is_the_tree.py ......................... [ 73%]
.........                                                                [100%]
34 passed in 0.79s
```

**Mutation table:**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `test_every_open_label_names_a_row_that_is_still_open` | restored `(UX-846 (open))` in §6 (sed on the fixed label) | only this case: `AssertionError: §6 marks id(s) \`(open)\` whose own Status line reads Done: ['UX-846']` | 1 failed, 33 passed |

Reverted from the pre-mutation copy
(`/tmp/.../scratchpad/agent-a1f151ae756c6aa95/fixing-guide.md.orig`);
re-run confirmed 34 passed, 0 failed.

`test_docs_links_and_commands.py`: 59 passed
(`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q
tests/unit/test_docs_links_and_commands.py`). `make test-touching`: 44
files, 1777 passed, 3 skipped. `ruff check`, `dev_sizes.py --check`,
`dev_baseline.py --check` (pre-existing forced findings only),
`pymarkdown scan docs/contributing/fixing-guide.md` all clean.
