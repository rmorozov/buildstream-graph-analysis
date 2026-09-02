# UX-546: the fetch-counting handoff guard is flaky under the full suite

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-521` (which landed the file this round), `UX-538` and `UX-543` (the same species elsewhere) | **Found by:** `UX-530` and `UX-535`, independently | **Serves:** the implementing session, which must be able to believe a red | **Topic:** guards

## Motivation

`test_the_handoff_says_whether_perfetto_fetched.py` landed this round
(`UX-521`). Two tracks hit it independently under `-n auto`, on
**different clauses each time**:

```text
track G, run 1   test_a_served_body_is_a_fetch… + test_two_servers_do_not_share_the_answer
track G, run 2   test_a_second_reader_is_a_second_fetch
track I          the file again, a different clause
isolation        6 of 6 green, with and without the diff, and at the base commit
```

A different clause each run, green alone, green at base: that is the
signature of shared state rather than a defect in any one clause. The
file binds ports and counts fetches, so two workers running it — or
running it beside another server-binding file — can see each other's
answers.

`UX-538` recorded why this class is expensive: a red that is not a
defect teaches a session to disbelieve the suite.

## Required Fix

Find the shared thing, measured rather than guessed: run the file
against itself at `-n 2` and `-n 8` with the port and the counter
logged, and say which of the two is shared. Then either give each
clause its own, or serialise the file with the marker the suite
already has for it.

Its docstring says what load it was measured under, as `UX-538`'s now
does.

## Out of Scope

- `UX-521`'s claim itself — the fetch counting is right; this is about
  whether two of them can run at once.

## Acceptance Test

The file green three times at `-n auto` inside a full `make test`,
with the load average pasted.
