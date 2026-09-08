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

Gap measured, per-round What-closed bullets (id before the em dash
only, so a bullet's prose mention doesn't count — round 110's `UX-772`
and `UX-607`) and `**Found by:**` header fields (not console-block
prose) read against `closed.md`'s 🟢 marker:

```console
$ python3 -m pytest tests/unit/test_the_round_history_names_every_audit.py -q
9 passed in 0.30s
round 109: What closed 13 (🟢 all), Found-by 11 -> directions.md now
  "Thirteen closed, eleven filed" (was "Fourteen closed, ten filed")
round 110: What closed 15 (🟢 all), Found-by 8 -> directions.md now
  "Fifteen closed, eight filed" (was "Fifteen closed, six filed";
  two of eight, UX-802/UX-803, filed after the row was first written)
```

Close measured: `test_a_history_row_s_counts_are_derived` added to
`tests/unit/test_the_round_history_names_every_audit.py`, parsing
words via `NUMBER_FOR_WORD`, the inverse of `tools/dev_track_cost
.count_word`, against digits. `make test-touching`: 1388 passed, 4
skipped in 180.98s. `make lint`: `lint-docs` clean, `ruff check` all
passed, `dev_baseline.py --check` clean (567 known, 0 new).

Verifier found a latent defect: the trailer regex used `\b` before
the count word, and greedy backtracking on the row's free text let
`\b` land at an internal hyphen, reading `thirty-one closed` as `1`
(and `NUMBER_FOR_WORD` stopped at 30). Fixed with `(?<=\s)` in place
of `\b`, and the word table extended to 1..99. Added
`test_the_count_trailer_reads_a_compound_word_past_thirty` on a
synthetic row.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `directions.md`: round-109 row's `Thirteen` -> `Fourteen` | `test_a_history_row_s_counts_are_derived`: "round 109: directions.md says 14 closed, 11 filed; derived 13 closed, 11 filed" | 1 failed, 8 passed |
| `_COUNT_TRAILER` reverted to the old `\b`-anchored regex | `test_the_count_trailer_reads_a_compound_word_past_thirty`: `(1, 22) == (31, 22)` | 1 failed, 9 passed |

Both restored from a scratchpad copy (never `git checkout --`);
re-run: 10 passed.
