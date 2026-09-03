# UX-573: the context map cannot see below `tools/`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-239 (the map and its guard) | **Serves:** the session that greps §6 for the hook and finds nothing | **Topic:** guards

## Motivation

`test_the_context_map_is_the_tree.py::_real_modules` globs `tools/*.py`
non-recursively, so `tools/native_trace/bwrap_shim.py`,
`trackevent.py`, `hook.c`, `spine.c` and `tools/dev_run.sh` are in
neither §6 nor `architecture.md`'s map and the guard is green:

```text
grep -n "native_trace\|bwrap_shim\|trackevent\|dev_run.sh" docs/contributing/fixing-guide.md
→ only native_trace_to_chrome_trace.py
```

The hook and the spine are Plane 2 — the map's own subject — and the
trackevent writer is Direction 15's whole mechanism. Inside `bga/`
the same blind spot: the guard holds `bga/*.py` and the packages, not
`bga/viewer/`, and the map's viewer block is 11 of 26 entries short
(`controls`, `decision`, `element`, `format`, `primitives`,
`sections`, `structured`, `tablefocus`, `perfetto.html`,
`perfetto_page.js`, `sql.html`), says `views.js` "imports nothing, by
design" (it has five imports, `./controls.js` among them), and lists
a `csv` renderer `bga/report/` does not have.

## Required Fix

The guard walks `tools/**` (Python and C, plus `.sh`) and
`bga/viewer/*.{js,html,css}`; §6 gains the five `tools/` rows and the
eleven viewer rows, loses `csv`, and the `views.js` description is
corrected (a description is judgment; its import claim is not —
`dev_js_deps.py --graph` derives it).

## Out of Scope

- Naming test helpers under `tests/` — §6's tests block is a curated
  list by design.

## Acceptance Test

Mutation: delete the `native_trace` rows — red; add a file under
`tools/native_trace/` with no row — red.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** falsified — the row counts held (5 + 11 = 16); the
`views.js` import count did not: three, not five.

The gap, from the rewritten walk against the *unedited* §6:

```text
$ python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py -q
E   AssertionError: module(s) the context map does not mention:
E   ['bga/viewer/controls.js', 'bga/viewer/decision.js',
E    'bga/viewer/element.js', 'bga/viewer/format.js',
E    'bga/viewer/perfetto.html', 'bga/viewer/perfetto_page.js',
E    'bga/viewer/primitives.js', 'bga/viewer/sections.js',
E    'bga/viewer/sql.html', 'bga/viewer/structured.js',
E    'bga/viewer/tablefocus.js', 'tools/dev_run.sh',
E    'tools/native_trace/bwrap_shim.py', 'tools/native_trace/hook.c',
E    'tools/native_trace/spine.c', 'tools/native_trace/trackevent.py']
1 failed, 12 passed in 0.07s
```

16 entries — 11 viewer, 5 under `tools/`, the item's figures.
`tools/native_trace/__init__.py` joins `NOT_ON_THE_MAP` as a package
marker beside the two already there; it is not one of the five.

The import claim, derived rather than read off:

```text
$ python3 tools/dev_js_deps.py --graph bga/viewer
views.js             drawings.js controls.js primitives.js
$ grep -c "from ['\"]\./" bga/viewer/views.js
3
```

"Imports nothing, by design" was wrong, and round 82's "five imports"
with it — three, `controls.js` among them. `bga/report/` holds
`text.py`, `json.py`, `ci_comment.py`, `_shared.py`, `__init__.py`: no
`csv`, so the row loses it.

| mutation | reddened; each reverted and re-run 15 green | run |
|---|---|---|
| drop `.c` from `MAPPED_SUFFIXES` `tools/` | population clause: *does not reach tools/native\_trace/hook.c* | 1 failed, 14 passed |
| drop `.html` from `MAPPED_SUFFIXES` viewer | same clause: *does not reach bga/viewer/perfetto.html* | 1 failed, 14 passed |
| `ls-files` → `ls-files --cached --others --exclude-standard` | `test_the_walk_reads_git_and_not_the_checkout`: the untracked probe entered the population | 1 failed, 14 passed |
| delete §6's four `native_trace` rows | `test_every_module_is_on_the_map`, naming all four | 1 failed, 14 passed |
| `git add tools/native_trace/ux573_mutation_probe.py` | `test_every_module_is_on_the_map`, naming it | 1 failed, 14 passed |
| a stale path into `NOT_ON_THE_MAP` | `test_the_exemption_list_names_only_real_paths` | 1 failed, 14 passed |

**Did not discriminate, first attempt.** Row 3 left all 15 green:
`_tracked` is `lru_cache`d and was filled by an earlier test in the
process, before the probe existed — the guard read a snapshot taken
before the condition it tests. `_tracked.cache_clear()` either side of
the probe, and it reddens naming the probe.

**Vacuity.** The population clause asserts the set is non-empty and
names one member per suffix the walk gained — `.c`, `.py` a level down,
`.sh`, `.js`, `.html`, `.css` — so narrowing it again is a red.

**Verification.**

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py -q
15 passed in 0.09s        single process; 0.01s slowest call
$ make lint
All checks passed!
$ make test-touching
2 failed, 507 passed, 3 skipped in 54.18s
```

Both failures are pre-existing at the base `c6ccb6b` and touch neither
surface: `test_every_declared_skip_reason_is_known` (UX-588's new skip
reason is undeclared) and `test_every_table_row_has_its_header_cell_count`
(`README.md:11`, a merge hotspot). Re-run on the stashed tree at the
base, they fail identically, so this commit used `BGA_SKIP_SELECTOR=1`
(UX-561) to pass the pre-commit selector hook.

**Deviation.** Dropping `csv` is a doc correction with no guard: the
existence direction reads only path-shaped tokens, and a bare `csv` has
no slash. Guarding the `bga/report/` renderer list was not in Required
Fix, so it is named here rather than done.
