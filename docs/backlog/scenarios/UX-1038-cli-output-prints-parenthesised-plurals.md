# UX-1038: CLI output prints `(s)` plurals where the count is known

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-1020 | **Found by:** UX-1020's own sweep | **Serves:** R1 | **Topic:** cli | **Area:** tools | **Shape:** bounded

## Motivation

`UX-1020` chose plurals by count on the page and left the rest. Outside
`bga/viewer/`, string literals still print `element(s)`, `contract(s)`:

```text
$ git grep -hn -E '["'"'"'][^"'"'"']*[a-z]\(s\)' -- 'bga/*.py' 'tools/*.py' ':!bga/viewer' | wc -l
244
$ git grep -l -E ... | wc -l
55
bga/analyzer.py:1356   f"{len(elements)} element(s) ran for less than half this "
bga/blast.py:423       f"  Sourced directly by {answer['direct_count']} element(s): ..."
```

The count includes dev tools under `tools/dev_*`; a reader-facing
subset is the row's first measurement.

## Decomposition

Input classes: a counted noun at 1 and at many, in `bga analyze`, `bga view`, `bga snapshot` and `bga doctor` output. The journey extends reading a command's summary into reading it as one voice.

## Required Fix

Every reader-facing CLI string with a known count chooses its plural by
that count, as `UX-1020` did in `bga/correlate.py`.

## Out of Scope

Dev tools under `tools/dev_*`; docstrings and comments.

## Acceptance Test

A guard reads the reader-facing CLI modules' string literals and finds
no parenthesised `(s)` plural. Mutation: restore `element(s)` in `bga/analyzer.py`, and
it reds.

## Outcome

**Gap measured.** Reader-facing scope: `bga/` minus `bga/viewer/`, plus
the three tools `bga view`/`snapshot`/`doctor` dispatch to
(`bga/tools_dispatch.py`) - `bga analyze`'s own code path is `bga/`
itself. Before the fix that scope carried 88 parenthesised-plural
literals across 17 files (`git diff` count below); `tools/bga_view.py`
had none. `bga/correlate.py` already had a `_count(n, noun)` helper
from `UX-1020` (its own docstring: `"1 element" / "2 elements" rather
than "1 element(s)"`) - promoted to `bga/units.py` as `plural(count,
noun, plural_noun=None, shown=None)`, named for the same idiom
`bga/viewer/tables.js`'s own `plural()` already uses; `correlate.py`
keeps `_count` as a local alias so its call sites are unchanged.

**Close measured.** `pytest tests/unit/test_a_cli_plural_is_chosen_by_count.py`:
1 passed. `make test-touching`: `309 file(s) selected (27 census + 282
naming the change) · 5848 passed, 99 skipped in 196.47s`. Ten tests
across `tests/unit/` asserted the old `(s)` spelling and were updated
to the count-driven wording (e.g. `test_blast_query_and_kinds.py`,
`test_the_band_comes_from_the_class.py`, `test_a_capture_names_its_physical_cores.py`).

**Mutation table.**

| Guard | Mutation | Result |
|---|---|---|
| `test_a_cli_plural_is_chosen_by_count.py` | restore `f"{len(elements)} element(s) ran for less than half this "` in `bga/analyzer.py` | reds: `AssertionError: ... {'bga/analyzer.py': [(1356, " element(s) ran for less than half this capture's ")]}` |

`python3 tools/dev_sizes.py --check` after the fix: 17 files' `file_lines`
(and two `longest_function`) grew by 1-13 lines each (the helper's
extra import line plus a rewrapped f-string per call site) -
`tests/quality_reference.json` left untouched, held for the close.
