# UX-1345: the append guard copies the live closed index and assumes its last chunk has room

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** `make push-check` on the 0.6.0 cut (2026-10-07) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** test_the_closed_index_reads_as_one.py

## Motivation

`UX-1344`'s close filled `closed/0010.md` to 128 rows, `CHUNK_ROWS`.
`test_a_close_appends_to_the_last_chunk` copies the live tree, closes one
more row and asserts no chunk opened:

```text
E   AssertionError: a close with room in the last chunk opened one
E     Left contains one more item: '0011.md'
```

The guard reds on every 128th close, whatever `dev_close_task.py` does.

## Required Fix

The guard makes the room its premise needs in its own sandbox, as its
sibling `test_the_129th_row_opens_a_new_chunk` fills it.

## Out of Scope

`CHUNK_ROWS`.

## Acceptance Test

The file passes with `closed/0010.md` at 128 rows.

## Outcome (round 172, 2026-10-07) — 🟢 Done

**Premise:** held.

### The gap, measured

```text
$ pytest -q tests/unit/test_the_closed_index_reads_as_one.py   # closed/0010.md at 128 rows
E   AssertionError: a close with room in the last chunk opened one
1 failed, 8 passed
```

### After

```text
$ pytest -q -p no:xdist tests/unit/test_the_closed_index_reads_as_one.py
9 passed
```

When the sandbox's last chunk holds `CHUNK_ROWS`, the guard drops its last
row first; a close then appends, which is the claim.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | the room-making branch disabled (`if False:`) | `test_a_close_appends_to_the_last_chunk`, 1 failed, 8 passed |
