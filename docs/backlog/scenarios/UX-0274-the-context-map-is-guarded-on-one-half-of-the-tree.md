# UX-274: the context map is guarded on one half of the tree

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-239 | **Serves:** the maintainers | **Topic:** guards

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

## Outcome — 🟢 Fixed & Verified

The map's **Tests and docs** block now names every entry directly under
`tests/`, and the guard covers that half the way it covers `bga/` and
`tools/`.

**Before**, 5 of 12 entries, with the three that mattered most absent:

```text
absent: browser.py, cdp.mjs, dom_shim.mjs, test_cli.py, test_e2e.py,
        test_golden.py, test_synthetic_multi_subproject.py
```

**After** — the block, with the two harnesses described by what they are
for rather than by what they are:

```text
tests/unit/                one file per item, named for its claim - the bulk of the suite
tests/tiers.py             which tier each file is in, from measurement (UX-238)
tests/conftest.py          the tier hook and the skip census (UX-235)
tests/dom_shim.mjs         the one DOM every viewer guard runs on (UX-264)
tests/cdp.mjs              headless Chrome over CDP, no dependencies (UX-257)
tests/browser.py           what drives it from a test; every geometric claim goes through here
tests/test_e2e.py          the whole pipeline on a committed run · test_golden.py  byte-for-byte
tests/test_cli.py          argument parsing and exit codes, at the CLI boundary
tests/test_synthetic_multi_subproject.py  the multi-project ingestion path
tests/support/             shared helpers · tests/fixtures/  committed run dirs
```

**Clause 3 was met by removal, not by counting.** Three figures were
stated as current and were five rounds old — `218 files, ~3,100 tests`
against 240 and 3,327, and `the 233 closed rows` against 263. They are
gone, and a guard now stops them coming back, because a count in a
context map earns nothing: a session needs to know that `tests/unit/`
holds one file per item, not how many items there are.

**The guard** — `tests/unit/test_the_context_map_is_the_tree.py`, now
10 tests. `_real_test_entries()` globs `tests/` **directly** and not
recursively, which is the one judgement call in it: the map points at
`tests/unit/` on purpose, because one line per guard would make §6 a
second backlog index, while a harness or a suite at the top level is a
place a session needs directing to. `NOT_IN_TESTS` carries the
exemptions and is itself checked, the same way `NOT_ON_THE_FRONT_DOOR`
is in `test_the_front_door_is_current.py` — an exemption for something
that no longer exists silently widens the check it is an exception to,
and the first draft's `tests/__init__.py` entry was exactly that. The
guard caught it on its first run, before any mutation.

Falsified, eight mutations:

```text
M1  drop the dom_shim.mjs line (the state review 2 found)  -> every_test_entry_is_on_the_map
M2  drop cdp.mjs and browser.py                            -> every_test_entry_is_on_the_map
M3  add tests/test_a_new_suite.py and name it nowhere      -> every_test_entry_is_on_the_map
M4  rename browser.py to headless.py in the map            -> map_names_nothing_that_does_not_exist
                                                            + every_test_entry_is_on_the_map
M5  put `218 files, ~3,100 tests` back                     -> map_states_no_count_it_does_not_check
M6  put `the 233 closed rows` back                         -> map_states_no_count_it_does_not_check
M7  exempt a path that does not exist                      -> exemption_list_names_only_real_paths
M8  the map as it stands (UX ids, "one file per item")     -> green, correctly
```

**M6 did not discriminate on the first attempt and the guard was fixed
rather than the mutation counted.** The count pattern required the noun
to follow the number directly, so it matched `218 files` and missed
`the 233 closed rows` two lines below — one adjective was the whole
difference. It now allows one word between them.

M8 is there because the fix has an obvious over-reach: a rule that
banned digits in the map would ban `(UX-238)`, `(UX-264)` and every
other id, and a guard that has to be worked around is a guard that gets
deleted. It is pinned as a case that must stay green.

M3 is the falsification the item asked for by name — a new file directly
under `tests/`, unnamed, reddens — and it is the one that makes this
guard worth more than the edit it enforced.
