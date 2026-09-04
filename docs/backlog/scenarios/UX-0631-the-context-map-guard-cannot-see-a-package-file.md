# UX-631: the context map's guard cannot see a file inside a package

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-573 (which fixed this walk for two trees), UX-608 (the map guard) | **Found by:** architecture review 15 | **Serves:** a reader looking a module up in the map | **Topic:** docs

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

## Outcome (round 86, 2026-09-04) — 🟢 Done

**Premise:** held — the walk is half the defect, the naming rule the
other half.

### The gap, measured

```text
$ len(_real_modules())                                        104
$ directory entries in it                                      12
$ .py files inside those 12 packages, minus __init__.py        26
$ of the 26, named on their own package's row                   5
$ tracked under bga/report/
__init__.py  _shared.py  ci_comment.py  json.py  rate.py  text.py
$ map row: text.py, json.py, ci_comment.py - renderers, no analysis
```

104 and 26 hold, and the row named three of five. What the filing did
not see: `_named` was `basename-without-suffix in <the whole map>`, so
files alone would still not have caught `bga/report/rate.py` — `rate`
is inside `generated`, on the release-notes row. Eight more were
answered by a word on another package's row: `scheduler` in
`bga/attribution/`'s description for `bga/replay/scheduler.py`, the
`bga/provenance.py` row for `bga/validation/provenance.py`,
`bga/ingest/`'s for `bga/structural/models.py`. That substring rule was
a proxy for "the map has a row for this file", and 21 of the 26 — not
11 — were unnamed once that was asked.

`UX-573` did fix this walk for `tools/**` and `bga/viewer/*`; its
Motivation held "`bga/*.py` and the packages", so directory
granularity was deliberate there.

### After

Two probes staged inside packages; the second's stem `analysis` is in
§6 twice already, which the old rule accepted.

```text
$ python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py -q \
      -k every_module_is_on_the_map
E   AssertionError: module(s) the context map does not mention:
E   ['bga/report/probe_ux631.py', 'bga/utilisation/analysis.py'].
1 failed, 29 deselected in 0.11s
```

§6 gained the 21 filenames on their packages' rows; `bga/report/`'s
row carries `_shared.py` and `rate.py`, the latter converting build
seconds into the reader's unit rather than rendering.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | the package contributes its directory again | walk clause, 1 — "does not reach bga/report/rate.py" |
| A2 | the naming rule reads the whole map, not the row | naming clause, 1 — `bga/ingest/`'s row answered for `bga/structural/models.py` |
| A3 | `rate.py` deleted from §6's `bga/report/` row | every-module clause, 1, naming it |
| A4 | a filename matched without its `.py` | naming clause, 1 — `text` answered `text.py` |
| A5 | the naming rule can never say yes | 3, the floor included |

**Two of mine did not discriminate at first.** A2 came back green: the
negative examples were saved by the `.py` suffix and not by the row
scoping, so scoping was untested — it now carries the case only
scoping answers, two packages holding a `models.py`. A1's first run
reddened the format-row clause for a reason that was not the mutation —
`_names_the_module` split a trailing-slash path into an empty filename,
matching every row. Fixed, with its own clause.

**One is now structurally green.** The format-row clause asks whether
the `--format` row can answer a module question; under the row rule a
one-line row cannot, ever — the fix subsumed it. Kept as a witness
against the old rule returning, with a floor (A5 reddens it).

### Deviation from the Required Fix

**One.** Files as the population do not close the Acceptance Test
alone: the naming rule had to stop being a substring of the whole map.
Both are here. `rate.py`'s design stayed out of scope.

`make test-touching`: 23 file(s) selected · 650 passed, 3 skipped.
