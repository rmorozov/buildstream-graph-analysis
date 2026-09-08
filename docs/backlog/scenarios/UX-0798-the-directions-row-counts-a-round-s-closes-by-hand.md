# UX-798: the directions row counts a round's closes by hand

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-583 (the round-history link guard), UX-772 | **Found by:** review 21, round 110 | **Serves:** the reader of `directions.md` deciding what a round did | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

```console
$ grep -n "Fourteen closed, ten filed" docs/design/directions.md
1893:| 109 | ... Fourteen closed, ten filed ...   # the round-109 row, its link elided
$ sed -n '/^## What closed/,/^## What the verifiers/p' docs/audits/round-109.md | grep -oE "UX-[0-9]+" | sort -u | wc -l
14        # one of them, UX-789, the same section says is filed and open
$ grep -rl "Found by:.*round 109" docs/backlog/scenarios/*.md | wc -l
11
```

The row's two counts are typed; the round document and the task
files hold the population. `test_the_round_history_names_every_audit.py`
reads the row's link and never its prose, so the sentence drifted the
day it was written — `UX-789` closed in round 110, under a commit that
says so.

## Required Fix

In `docs/design/directions.md` the round-109 row reads *thirteen
closed, eleven filed*, and a guard in
`tests/unit/test_the_round_history_names_every_audit.py` reads each
row's "N closed, M filed" against the round document's *What closed*
ids that are 🟢 in `closed.md` and the task files whose `Found by:`
names the round — rows from round 109 on; older rows are records.

## Out of Scope

- Rewriting the rows' prose beyond the two counts — declined: the prose is the round's summary, and `UX-772` owns the register the rows sit beside.

## Acceptance Test

Mutation: the row's `thirteen` typed as `fourteen` — red, naming
the round and both numbers.

## Outcome

_Not started._
