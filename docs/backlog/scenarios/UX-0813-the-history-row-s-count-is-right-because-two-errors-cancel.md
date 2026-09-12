# UX-813: the history row's count is right because two errors cancel

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-798 (the derived counts), UX-806 (the row it miscounts) | **Found by:** round 113, review 22 | **Serves:** the reader of the directions table; a guard whose population is the sentence's | **Topic:** guards | **Area:** unassigned | **Shape:** bounded

## Motivation

`test_the_round_history_names_every_audit.py`'s `_what_closed_ids`
walks every `- ` bullet of a round document's *What closed* and takes
the ids before the em dash. Round 111's section ends with a bullet
that has no em dash — "Direction 19 marked landed once `UX-695`
closed." — so the whole line is read and `UX-695` is counted twice;
`UX-806`, closed in that round, sits under *In progress* and is never
seen. Sixteen derives from fifteen distinct ids, one twice:

```text
$ python3 -c "import sys; sys.path.insert(0,'tests/unit'); import test_the_round_history_names_every_audit as t; ids=t._what_closed_ids(111); print(len(ids), len(set(ids)), 'UX-806' in ids)"
16 15 False
$ grep -c "UX-806" docs/backlog/scenarios/closed.md
1
```

`directions.md`'s row says sixteen and the guard reads `16 == 16`.

## Required Fix

`_what_closed_ids` reads only bullets that carry an em dash and
returns each id once, in order; a unit test on a synthetic document
(one id twice, one trailing bullet with no dash) holds it. Round
111's *What closed* gains `UX-806`'s bullet, so the row's sixteen is
sixteen distinct ids. Mutation: drop the dash test and the dedupe —
the synthetic test reds and round 111 derives seventeen.

## Out of Scope

- Other rounds' sections — the count guard re-derives every row; a
  second miscount would red there, and none does.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_round_history_names_every_audit.py -q`
green; the mutation red; `_what_closed_ids(111)` returns sixteen
distinct ids including `UX-806`.

## Outcome

**Gap measured.** `_what_closed_ids(111)` → 16 ids, 15 distinct,
`UX-806` absent (pasted above); `directions.md` says sixteen and the
count guard read `16 == 16`.

**Close measured.** The walk reads only em-dash bullets and returns each
id once; round 111's section gains `UX-806`'s bullet:

```text
$ python3 -c "...; ids=t._what_closed_ids(111); print(len(ids), len(set(ids)), 'UX-806' in ids)"
16 16 True
$ python3 -m pytest tests/unit/test_the_round_history_names_every_audit.py -q
11 passed        # 10 before, plus the synthetic-document test
```

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| walk every bullet, no dedupe (the old code) | `test_what_closed_ids_reads_each_bullet_s_head_once`, `test_a_history_row_s_counts_are_derived` (round 111 derives 17) | 2 of 11 |

Reverted; 11 passed.

**Deviation.** None. Session-side, from review 22, one commit with
`UX-814`.
