# UX-543: a second clause of the answer key ranks under contention

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-538` (the same species, one clause over), `UX-489` (the margin instrument) | **Found by:** `UX-538`, fixing its sibling | **Serves:** the implementing session, which must be able to believe a red | **Topic:** guards

## Motivation

`UX-538` took the timing out of `test_the_first_thing_to_fix_is_core`.
While it did, a second clause in the same file went red the same way:

```text
test_the_never_read_edges_are_the_declared_chain
  make test-touching, -n auto   red — ('lib-b.bst','lib-c.bst') missing
                                      from the restructuring finding
  alone                         green
  at base, -n 4                 green
  the re-run                    green
```

Same species, different clause: a real capture's output compared
against an expected set, where what the capture produces depends on
what the machine was doing. `UX-538`'s Motivation says why that is the
expensive failure — a red that is not a defect teaches a session to
disbelieve the suite — and one clause of a file being fixed does not
fix the file.

## Required Fix

The same two options `UX-538` weighed, on this clause's own
measurement: the margin at 1, 4 and 8 concurrent workers, pasted; then
either a floor the measured spread cannot cross, or the declared chain
read from a **recorded** capture with a cheaper live clause beside it.

Whichever it is, the docstring says what load it was measured under.

## Out of Scope

- Re-opening `UX-538`'s decision for the clause it already fixed.

## Acceptance Test

The clause green three times at 8 concurrent workers with the load
average pasted, as `UX-538`'s is.

## Outcome

**Round 81, 2026-09-03.** 4-core box, `examples/06` cold, `correlate` on
the result. The load shape is `UX-538`'s own: one capture under N-way CPU
contention, because N concurrent captures do not complete here - three
coexisting isolated CAS stores already answer `Cache too full`.

**The margin.** Which of the five declared links reach the finding:

```text
loadavg     workers  wall          chain links in the finding
0.98-7.68      1     30.9-33.3s    5 of 5, x3
6.52-6.77      4     28.9-35.7s    5 of 5, x3
8.03-9.16      8     38.2-42.4s    5 of 5, x4
```

Ten of ten, against round 80's one red - a failure that cannot be
produced on demand, which is the worst kind to leave live.

**Why no floor.** `find_restructuring_findings` calls
`_unread_gating_edges`, which keeps a pair only `if predecessor in
on_path and successor in on_path` - the **measured** critical path. So
which links reach the finding is a reading of the box, and the reading is
set membership: a link is in the finding or it is not, and there is no
scalar for a number to sit under. `UX-538`'s first option is unavailable
here for a different reason than it was there.

**The close: the second option.** The clause reads `recorded_join`, a new
module fixture that `correlate`s `tests/fixtures/macro_micro/run` - the
same recording `UX-538`'s ranking clause already uses. Its input is
bytes: at loadavg 9.03, x3, `18 edges, saving_us=24150000`, identical.
The live capture keeps a new clause of its own,
`test_a_live_capture_still_finds_a_chain`: **at least one** of the five
links, a floor of 1 against a measured 5 (ten runs) and round 80's 4. The
live half of answer 1 that load never moved - which dependency each
element never opened - was already held by
`test_codegen_is_named_unused_by_the_libraries_that_declare_it`, whose
element rows are not filtered by the critical path.

`tests/conftest.py`'s skip census goes 23 -> 24 for the added clause.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| R1 | drop `lib-b.bst -> lib-c.bst` from the recording's `unused_candidates` (24 -> 23 rows) | the recorded clause alone, naming the pair round 80's live red named | 1 failed, 2 passed, 21 deselected in 32.30s |
| R2 | drop all five chain pairs (24 -> 19 rows) | the recorded clause; **both** live clauses stayed green | 1 failed, 2 passed, 21 deselected in 34.14s |
| R3 | `find_restructuring_findings` forced to `[]` | both chain clauses - the live one is not vacuous | 2 failed, 1 passed, 21 deselected in 32.10s |

R2 is the one that matters for the split: the two clauses read different
inputs, so a recording that lost its shape cannot be excused by a live
build that kept its own. Revert: `3 passed, 21 deselected in 33.97s`.

**Acceptance Test, pasted** - the clause at 8 concurrent workers, x3:

```text
--- run 0, 8 workers, loadavg 15.12 ---   1 passed in 3.62s
--- run 1, 8 workers, loadavg 15.76 ---   1 passed in 3.50s
--- run 2, 8 workers, loadavg 16.50 ---   1 passed in 3.63s
```

**Deviation:** the eight-worker readings above are one capture under
8-way CPU contention, not eight concurrent captures - the same
substitution, for the same disk reason, `UX-538` recorded.

**Seen once, not this item's:** with `/tmp` down to 14 GB the live `bst
build all.bst` returned 255 with one element failed; `rm -rf
/tmp/pytest-of-root` freed 4.4 GB and it went green. Needs its own row.
