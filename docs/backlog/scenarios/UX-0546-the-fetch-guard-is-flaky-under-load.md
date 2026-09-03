# UX-546: the fetch-counting handoff guard is flaky under the full suite

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-521` (which landed the file this round), `UX-538` and `UX-543` (the same species elsewhere) | **Found by:** `UX-530` and `UX-535`, independently | **Serves:** the implementing session, which must be able to believe a red | **Topic:** guards

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

## Outcome

**Round 81, 2026-09-03.** 4-core box.

**Neither of the two candidates is the shared thing.** A plugin wrapping
`serve` logged the bound port and the identity of the per-serve handler
class per clause, `-n 2` at loadavg 8.29:

```text
ports    39673 40025 36357 39417 43821+44521 38385   all distinct
class    one per live server (a repeated id is CPython address reuse
         after the previous server was closed, not sharing)
```

`serve` takes `port=0` and builds `_BoundHandler` per call, so the port
is the kernel's and the counter is that class's. `tests/unit` at `-n 8`
beside 8 burners, loadavg 9.6 rising to **63.4**, did not reproduce it
either: `1 failed, 6070 passed, 95 skipped in 515.65s`, and the one
failure was `test_native_build_tracer.py`'s real cmake build.

**What is shared is the counter's *write*, not the counter.** `_trace`
increments in the request thread **after** `copyfileobj` has emptied the
file into the socket, so *"the client holds the last byte"* and *"the
count moved"* are two events with nothing ordering them. Fetch, then ask
immediately, x600:

```text
loadavg   first read stale   the count arrived
  0.09      0 of 600         -
  7.12      3 of 600         4.2, 5.5, 5.9 ms late
  7.76      1 of 150         2.0 ms late
```

That predicts the evidence clause for clause: the three that assert a
**non-zero** count straight after a fetch are exactly the three round 80
saw red, and none of the three that assert zero ever appeared.

**The close.** `_status_when(url, fetches, within=10.0)` polls the status
endpoint until the count reaches what the clause claims and returns the
last reading either way, so it waits on the condition rather than on a
duration and a count that never arrives still reddens. Used by
`test_a_served_body_is_a_fetch_and_carries_its_size`,
`test_a_second_reader_is_a_second_fetch` and
`test_two_servers_do_not_share_the_answer`. **No marker was added** -
there is nothing to serialise, and `--dist loadgroup` is not in use, so
`xdist_group` would have been a no-op. No product change: `UX-521`'s
counting is untouched.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `cls.trace_served += 1` -> `+= 0` - the condition never arrives | all three waiting clauses, each at its 10s bound | 3 failed, 4 passed, 11 deselected in 33.51s |
| M2 | `+= 1` -> `= min(cls.trace_served + 1, 1)` | `test_a_second_reader_is_a_second_fetch` alone | 1 failed, 6 passed, 11 deselected in 13.68s |
| M3 | `cls.trace_served_bytes = size` -> `size + 1` | the two clauses asserting the whole dict | 2 failed, 5 passed, 11 deselected in 3.59s |

M1 is the one the brief asked for: the wait does not paper over a count
that never comes. Revert: `18 passed in 5.19s`.

**Acceptance Test, pasted** - the file at `-n 8`, x3:

```text
--- run 0, loadavg 16.50 ---   18 passed in 4.55s
--- run 1, loadavg 16.86 ---   18 passed in 3.77s
--- run 2, loadavg 17.27 ---   18 passed in 4.53s
```

and x10 earlier at loadavg 5.72-7.90, all `18 passed`.

**Deviation:** the Acceptance Test asks for three runs inside a full
`make test`; the orchestrator owns the suite gate, so this is the file at
`-n 8` under load plus one whole-`tests/unit` sweep at `-n 8`.

**A leak, not fixed:** `serve` mkdtemps `bga-serve-*` per served run and
nothing removes it - 2799 of them, 28 MB, on this box. Needs its own row.
