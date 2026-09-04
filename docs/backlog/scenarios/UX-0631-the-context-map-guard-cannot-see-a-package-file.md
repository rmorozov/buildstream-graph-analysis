# UX-631: the context map's guard cannot see a file inside a package

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-573 (which fixed this walk for two trees), UX-608 (the map guard) | **Found by:** architecture review 15 | **Serves:** a reader looking a module up in the map | **Topic:** docs

## Motivation

`_real_modules()` returns 104 paths and maps a `bga/` package to its
**directory**: `bga/report/*.py` collapses to the single entry
`bga/report/`. So a new file inside a package has a home the moment
the directory does, whatever the map's line actually lists.

```text
$ git ls-files bga/report/
bga/report/__init__.py  _shared.py  ci_comment.py  json.py  rate.py  text.py
map line names:         text.py, json.py, ci_comment.py
```

`UX-596`'s `bga/report/rate.py` landed with no mention anywhere
outside its own source and `docs/backlog/`, and
`test_the_context_map_is_the_tree.py` stayed green. **26 modules** sit
in that blind spot.

This is the same non-recursive walk `UX-573` fixed for `tools/` and
`bga/viewer/`, left undone for `bga/`'s packages.

## Required Fix

The population is files, not directories, for `bga/`'s packages as it
already is for the other two trees — and `fixing-guide.md`'s
`bga/report/` line, which names three of five modules and describes
`rate.py` as a renderer when it converts, is corrected in the same
commit.

## Out of Scope

- `rate.py`'s own design — declined here, because the guard would
  have missed any module in that directory, not this one.

## Acceptance Test

A new module inside a `bga/` package with no map entry, reddening
`test_the_context_map_is_the_tree.py`.
