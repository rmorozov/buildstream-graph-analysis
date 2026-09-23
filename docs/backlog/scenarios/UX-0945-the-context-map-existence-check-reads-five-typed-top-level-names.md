# UX-945: the context map's existence check reads five typed top-level names, so a §6 line under any other directory is never checked against the tree

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-937, UX-239 | **Blocks:** — | **Found by:** round 138 — `UX-937`'s second mutation, which its Acceptance Test expected this guard to catch | **Serves:** every row that declares an area, now that the area vocabulary is whatever top-level directory §6 names | **Topic:** guards | **Area:** tests/unit | **Shape:** judgement

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

## Outcome
