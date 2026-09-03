# UX-572: "by construction" survived the construction it now depends on

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-406 (the emit-time join that made it true), UX-530 | **Serves:** the reader of the trace dictionary | **Topic:** docs

## Motivation

`docs/spec/trace-dictionary.md:96` and the comment at
`tools/bga_timeline.py:495` both say the concurrency counter's peak
"equals the report's `max_concurrency` by construction". Round 64
measured it false with the spine on (peak 44 against 24); `UX-406`
made it true again through the emit-time join and
`test_one_process_is_one_slice.py:223-236` holds it — but neither
sentence was amended, so the dictionary states as a construction what
is now a guarded consequence of a join it does not mention. And
`test_the_counter_the_constant_was_waiting_for.py` still skips on this
machine ("no real capture in this tree") with a real capture present
under `examples/06-macro-micro-optimization/.bga/runs/`.

## Required Fix

Both sentences name the join and the guard; the skipping counter
guard is pointed at the capture path it wants (or its skip reason
says which path it looked in).

## Out of Scope

- The counter's arithmetic — held by `UX-406`'s guard.

## Acceptance Test

The dictionary sentence names `UX-406`'s join; the counter guard runs
green on this machine with the capture present.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held — the equality is true, and true *only* because
`render` calls `UX-406`'s join; on a spine-on capture the unjoined
stream reads 24 against a published 13.

The measurement, over every real capture on this machine (script in the
session scratchpad; `concurrency_series` peak before and after
`merge_record_streams`, against each run's own `plane2.json`):

```text
capture                srcs                     raw joined peak_raw peak_join report
20260821T170127Z       [('hook', 813)]          813    813       20        20     20
20260829T174845Z       [('hook', 87), ('spine', 87)]   174     87       24        13     13
```

`UX-310` was closed on the first row, where the join is a no-op and
"by construction" is indistinguishable from the truth. The second row
is the distinction: unjoined the counter counts both records of every
dynamically-linked process. So the sentence stated a construction where
a guarded consequence was meant, exactly as filed.

**The skip.** Filed as "skips on this machine"; measured, it skips in a
**linked worktree** and not in the main checkout, because
`parents[2]` is the tree that never has a gitignored capture:

```text
$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_the_counter_the_constant_was_waiting_for.py -q -rs
SKIPPED [1] ...:258: no real capture in this tree
SKIPPED [1] ...:294: no real capture in this tree
SKIPPED [1] ...:318: no real capture in this tree
9 passed, 3 skipped in 0.35s
```

After: the lookup also asks `git rev-parse --git-common-dir`, and the
reason names the path it looked for.

```text
$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_the_counter_the_constant_was_waiting_for.py -q -rs
12 passed in 0.67s
```

With the path made absent (the same mutation), 3 skips reading
`no real capture at examples/06-macro-micro-optimization/.bga/runs/
20260821T170127Z, in this tree or the checkout it was linked from` —
declared in `tests/conftest.py` at 3, and static so
`test_every_skip_reason_is_declared.py`'s `UNRESOLVABLE` stays 58.

**The mutation table** — `tests/unit/test_the_equality_names_its_join.py`:

| mutation | reddened | run |
|---|---|---|
| dictionary: `UX-406`'s `merge_record_streams` join → `the join` | `..._dictionary_sentence_names_the_join_and_its_guard` | 1 failed, 3 passed |
| dictionary: the named guard → `a guard in the suite` | same clause, guard-name assertion | 1 failed, 3 passed |
| dictionary: `a consequence of the join below…` → `by construction` | same clause, retired-phrase assertion | 1 failed, 3 passed |
| timeline comment: `` `UX-406` joined with `merge_record_streams` `` → `the reader joined earlier` | `..._timeline_comment_names_the_join_and_its_guard` | 1 failed, 3 passed |
| rename `test_the_counter_peak_is_the_reports_max_concurrency` | `..._named_guard_exists_and_reads_the_counter_peak` | 1 failed, 3 passed |
| `merge_record_streams` → `return list(records)` | `..._equality_is_false_without_the_join` (`assert 4 == 2`) | 1 failed, 3 passed |

Reverted after each; 4 passed. New file at `-p no:xdist`: 0.24s, 0.29s,
0.31s over three runs.

**Deviation.** Two surfaces beyond the two declared.
`tests/conftest.py` gains the new skip reason — the census fails CI on
an undeclared one, so the reason could not change without it.
`tests/unit/test_one_process_is_one_slice.py` had a docstring quoting
the retired phrase as current; annotated per fixing-guide §3.6, not
rewritten. `docs/spec/trace-dictionary.md` is not `specification.md`
and carries no Part 32 restriction.

**Not fixed here.** `tests/unit/test_every_skip_reason_is_declared.py`
fails at the base commit `c6ccb6b` and after this change, on
`UX-588`'s undeclared reason `the floor has moved to 3.10; PEP 604 is
allowed`. Pre-existing, verified by `git stash`; left for `UX-588`.
