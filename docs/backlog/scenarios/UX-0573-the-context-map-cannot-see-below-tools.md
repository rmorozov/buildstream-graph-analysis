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
