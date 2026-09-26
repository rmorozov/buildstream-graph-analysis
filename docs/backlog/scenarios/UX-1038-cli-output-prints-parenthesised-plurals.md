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
no `[a-z](s)`. Mutation: restore `element(s)` in `bga/analyzer.py`, and
it reds.

## Outcome

Not started.
