# UX-826: five bare task ids and a pipe-delimited task key reach the reader

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-669 (the rule), UX-824 (the guard) | **Found by:** round 115, the design review | **Serves:** every reader of a finding | **Topic:** analysis | **Area:** bga | **Shape:** mechanical

## Motivation

Four sentences in the analysis carry a task id in parentheses and one
row prints an internal key:

```text
bga/correlate.py:1181   "does not model contention (UX-14), and cores-busy is an average"
scale export            UX-478 (twice), UX-345, UX-477 in rendered prose
duration_resolution     "Tasks?" row: all.bst|FETCH|FETCH|0
```

`UX-669` fixed three such sentences in round 82 and left the rule
unguarded; these are the ones it did not reach.

## Required Fix

In `bga/correlate.py` and `bga/findings.py` each citation becomes the section's question or a backticked id per
§4b, and `duration_resolution` renders the task as element · kind
(`all.bst`, FETCH) rather than the join key. `UX-824`'s guard is what
finds the next one.

## Decomposition

Input classes: a finding with a caveat sentence (the contention
caveat), a `duration_resolution` block with and without tasks, and the
golden fixture; the journey is the findings list in the answer key.

## Out of Scope

- The guard — `UX-824`.
- The section keys — `UX-825`.

## Acceptance Test

`grep -n "(UX-[0-9]*)" bga/*.py` names no reader-facing sentence;
`tests/unit/test_a_reader_never_sees_the_register.py` green on both exports for the id and task-key lines; mutation: put one `(UX-14)` back — red.
