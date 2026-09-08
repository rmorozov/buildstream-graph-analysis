# UX-799: the map row for the baseline tool names one of its two modes

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-697 (the pyright mode), UX-780 (the same row shape, one row over) | **Found by:** review 21, round 110 | **Serves:** the reader of §6 choosing which tool prices a finding | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

```console
$ sed -n 383,385p docs/contributing/fixing-guide.md
tools/dev_baseline.py        every current finding by identity in
                             tests/quality_baseline.json; a new one is red,
                             the list only shrinks (UX-694)
$ grep -c "pyright" tools/dev_baseline.py
14
```

`UX-697` gave the tool a second source — pyright's `--outputjson`,
293 findings priced into the same baseline — and the row still
describes the first. `test_the_context_map_is_the_tree.py` reads the
row's path and its cited ids, not what the row says the file does.

## Required Fix

In `docs/contributing/fixing-guide.md` the `dev_baseline.py` row names
both sources — ruff, bandit and pyright findings by identity, cited
`UX-694/697` — and a guard in
`tests/unit/test_the_context_map_is_the_tree.py` reads each `tools/`
row against the tool's own `TOOLS` (or the names its findings
functions carry): a tool the row does not name is red.

## Out of Scope

- The rest of the map's descriptions — `UX-689` owns the map's
  structure; this row is the one review 21 read.

## Acceptance Test

Mutation: `pyright` removed from the row — red, naming the row and
the tool.

## Outcome

**The gap, measured.** `sed -n 383,385p docs/contributing/fixing-guide.md`
still read `every current finding by identity in
tests/quality_baseline.json`, one source, citing only `UX-694`.
`tools/dev_baseline.py`'s own docstring: `Two producers feed one
list: ruff (json) ... and pyright (--outputjson ...)` - `grep -c
bandit tools/dev_baseline.py` and `grep -c pylint tools/dev_baseline.py`
both `0`; the "bandit" named in this task's own Required Fix does not
exist in the module. No `TOOLS` mapping existed to check a row against.

**The close, measured.** Row now reads `every current ruff and pyright
finding by identity in tests/quality_baseline.json; a new one is red,
the list only shrinks (UX-694/697)`, three lines, guide unmoved at
`~50 KB` (55,319 B -> 55,339 B, same 10 KB bucket -
`tools/dev_touching.py --size`). New class
`TestTheMapNamesEachToolsToolPrices` in
`test_the_context_map_is_the_tree.py`, population: `tools/dev_*.py`
files exposing `TOOLS` - one member today, `dev_baseline.py`.

**Verifier finding, fixed.** `TOOLS` first pointed at the raw fetchers
while `main()` called them directly, so a producer wired into `main()`
and not into `TOOLS` reddened nothing. `TOOLS` now holds
`_ruff_producer`/`_pyright_producer` (fetch+normalize, uniform
`(root, paths)`), `main()` builds `current` by iterating
`TOOLS.values()` (`--pyright-from` binds via `functools.partial`
before the loop), and `suppression_findings` is added after, with a
one-line why: it is the repo's own scan, not a tool.

```console
$ python3 -m pytest tests/unit/test_the_baseline_only_shrinks.py \
    tests/unit/test_the_context_map_is_the_tree.py -q
53 passed in 22.12s
$ python3 tools/dev_baseline.py --check
clean: 567 finding(s) match tests/quality_baseline.json; ...
```

**Mutations.**

| mutation | guard | result |
|---|---|---|
| `pyright` dropped from the row's finding-list phrase | `test_every_tools_key_is_named_on_its_row` | `["pyright in tools/dev_baseline.py's row"]` - `1 failed, 1 passed` |
| fake `"bandit": _ruff_producer` added to `TOOLS` | same | `["bandit in tools/dev_baseline.py's row"]` - `1 failed, 1 passed` |
| both reverted from a scratchpad copy, never `git checkout` | same | `2 passed` |

`make test-touching`: `1620 passed, 3 skipped`. `make lint`: `ruff`
clean, `dev_baseline.py --check` clean, `lint-docs` clean. Merged
`919d4db3` (UX-802, `--pyright-from`) first, clean auto-merge.
