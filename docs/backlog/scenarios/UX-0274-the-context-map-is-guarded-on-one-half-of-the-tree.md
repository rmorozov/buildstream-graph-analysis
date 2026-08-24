# UX-274: the context map is guarded on one half of the tree

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-239 | **Serves:** the maintainers | **Topic:** guards

## Motivation

Found by review 2 (`UX-241`), and it is `UX-239` recurring in the half
its guard never covered.

`docs/contributing/fixing-guide.md` §6 exists so a low-context session
does not re-derive where things live, and
`tests/unit/test_the_context_map_is_the_tree.py` keeps it honest — both
directions, a module missing from the map fails and a map entry with no
module fails. But its `_real_modules()` globs exactly two roots:

```python
for pattern, root in (("*.py", "bga"), ("*.py", "tools")):
```

So the map's **Tests and docs** block is unguarded prose, and measured
today every figure in it is wrong and more than half its entries are
missing:

```text
map says                                    tree says
tests/unit/  218 files, ~3,100 tests        240 files, 3,327 tests
closed.md    the 233 closed rows            263 closed rows

entries in the map's tests block:  5 of 12 real entries in tests/
absent: browser.py, cdp.mjs, dom_shim.mjs, test_cli.py, test_e2e.py,
        test_golden.py, test_synthetic_multi_subproject.py
```

Three of those absences are the two harnesses this axis just built and
will keep using — `tests/dom_shim.mjs`, the one shared DOM the viewer
guards run on (`UX-264`), and `tests/cdp.mjs` + `tests/browser.py`, the
zero-dependency Chrome instrument every geometric claim is measured
with (`UX-257`). A session that needs to assert something about the
page reads §6, is pointed at no shim and no browser, and writes its
twenty-sixth inline copy — which is precisely the cost `UX-264`
measured and removed.

The figures are the smaller half but they fail the same way `UX-247`
does: a number stated as current, read as current, five rounds old.

## Required Fix

1. The map's tests block names every entry directly under `tests/`,
   with the two harnesses described by what they are for.
2. The guard covers `tests/` the way it covers `bga/` and `tools/` —
   both directions, with a small `NOT_ON_THE_MAP` set for what is
   genuinely not worth pointing at.
3. Counted figures in the map (`N files`, `~N tests`, `N closed rows`)
   are either guarded against the tree or removed. A figure nothing
   checks is the defect, not the count.

## Out of Scope

- Guarding `docs/` entries in the same block against the docs tree.
  Those move rarely and `test_the_docs_links_resolve` already catches a
  path that stops existing.
- Widening the guard to `tests/unit/`'s 240 individual files. The map
  points at the directory on purpose; one line per guard would make it
  a second index.

## Acceptance Test

The guard reddens against the map as it stands — the seven absent
entries, and each stale figure — and is green after the correction.
Adding a new file directly under `tests/` and not naming it reddens it
again; that is the falsification.
