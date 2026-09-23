# UX-945: the context map's existence check reads five typed top-level names, so a §6 line under any other directory is never checked against the tree

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-937, UX-239 | **Blocks:** — | **Found by:** round 138 — `UX-937`'s second mutation, which its Acceptance Test expected this guard to catch | **Serves:** every row that declares an area, now that the area vocabulary is whatever top-level directory §6 names | **Topic:** guards | **Area:** tests/unit | **Shape:** mechanical

## Motivation

`UX-937` made the area vocabulary every top-level directory the fixing
guide's §6 tree names. Its Acceptance Test said a §6 line for a
directory that does not exist would join the vocabulary, "and the guard
that reads §6 against the real tree (`test_the_context_map_is_the_tree.py`)
is what catches it". Measured, it does not:

```text
$ sed -i 's/^tests\/unit\/ /nowhere\/deep\/   a directory that does not exist\ntests\/unit\/ /' docs/contributing/fixing-guide.md
$ python3 -c "...; a = d.declared_areas(); print('nowhere' in a, 'nowhere/deep' in a)"
True True
$ python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py -q
48 passed
```

`test_the_map_names_nothing_that_does_not_exist` finds the paths it
checks with its own alternation:

```python
r"(?<![\w./-])((?:bga|tools|tests|docs|\.github)/[\w./-]+)"
```

That is the shape `UX-937` removed from `declared_areas()`: a typed list
of top-level names standing in for the tree, so a path under any other
name is outside the population and passes by not being read.

## Required Fix

The existence check reads every path-shaped entry §6's fenced blocks
open a line with, whatever its top-level name, rather than an
alternation of five.

## Out of Scope

Which top-level directories should be areas (`UX-937`, and §6 itself).
The other direction - a module on no row - which already walks git.

## Acceptance Test

A §6 line `nowhere/deep/` reddens `test_the_context_map_is_the_tree.py`
naming it; removing the line greens it. A mutation that restores the
alternation keeps it green and must redden the new clause.

## Decision

The `architect`, round 140, at `398b4db9`.

```text
Route:     test_the_map_names_nothing_that_does_not_exist reads paths from one helper returning
           both the first word of each path-shaped map line under any top-level name, and
           mid-line paths under top-level names taken from _tracked(), not the typed five
Rejected:  widen the mid-line regex to any name/... - 16 false hits (push/PR, UX-694/697, ...)
           declared_areas() drops a missing directory - hides a §6 typo; touches tools/
Files:     tests/unit/test_the_context_map_is_the_tree.py
Guard:     the existence clause, plus a self-test: the helper fed "nowhere/deep/   x" returns
           nowhere/deep/ (measured: 159 mid-line paths as today, 0 stale)
Mutation:  add a §6 line `nowhere/deep/` -> existence clause red; restore the five-name
           alternation -> self-test red
Class:     bookkeeping (batch with UX-979, UX-977)
```

## Outcome

**Gap measured:** the Motivation's own repro, unchanged before the fix
(48 passed, the injected line never read).

**Close measured (revised per the architect's Decision):** the
existence check now reads `_map_paths()` - `MAP_ENTRY_PATH`'s
line-opening path under any top-level name, unioned with a mid-line
path whose top-level name `_tracked()` actually has (not a typed
alternation of five, and not "any name", which reads `push/PR` and an
id like `UX-694/697` as paths). This restores the 3 mid-line entries
the first draft dropped (`docs/audits/`,
`docs/design/capture-workflow.md`, `tests/fixtures/`):

```text
$ python3 -c "...; print(len(t._map_paths(t._map_text())))"
159   # 151 line-opening + 8 distinct mid-line, 0 stale
$ python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py -q -n 2
36 passed in 1.21s-1.41s
```

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `nowhere/deep/` line inserted before `tests/unit/` | `test_the_map_names_nothing_that_does_not_exist` | 1 failed |
| line removed (saved copy) | same | 36 passed (full file) |
| `MAP_ENTRY_PATH` reverted to a 5-name-alternation, still line-anchored | `test_the_helper_reads_any_top_level_name`; the existence clause stayed green (nothing in today's guide falls outside the five) | 1 failed, 1 passed |
| mid-line half widened to any name (not `_tracked()`'s roots) | `test_the_mid_line_half_is_not_widened_to_any_name` (`{'UX-694/697', 'push/PR'}`) | 1 failed |
| each reverted (saved copy) | all green | 36 passed |
