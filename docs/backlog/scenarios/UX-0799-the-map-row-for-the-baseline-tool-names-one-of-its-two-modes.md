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

_Not started._
