# UX-1338: two snapshot tests leak `BGA_NO_PROGRESS` into whichever test runs next

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** round 171's push-check (2026-10-07): `test_no_shelling_phase_is_silent.py` red 2 under the touching selector, green alone | **Serves:** R1 | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_no_shelling_phase_is_silent.py`

## Motivation

`bga_snapshot.main(["--no-progress", ...])` sets `os.environ["BGA_NO_PROGRESS"] = "1"`
(`tools/bga_snapshot.py:706`) and nothing undoes it. Two tests call it
in-process: `test_a_snapshot_with_no_bst_build_leaves_no_husk` and
`test_no_progress_prints_the_total_only`. Any progress guard that lands
after either on the same xdist worker draws nothing:

```text
$ pytest -p no:xdist -p no:randomly tests/unit/test_a_build_run_through_a_wrapper_script_is_captured.py \
    tests/unit/test_no_shelling_phase_is_silent.py
FAILED ...::test_a_batch_per_frame / ::test_the_retry_says_it_is_retrying
2 failed, 12 passed
```

The same pair passes on `d0e434e2` only because the worker split put
them apart; round 171's new test files moved the split.

## Decomposition

Input classes: the wrapper-script test first; the tail test first;
neither. Journey: `make push-check` on any diff whose selection holds
both files.

## Decision

```text
Route:     each leaking test sets BGA_NO_PROGRESS through monkeypatch before main, so teardown undoes main's os.environ write.
Rejected:  delenv in the shelling guard only - the next progress guard would leak the same way.
Files:     tests/unit/test_a_build_run_through_a_wrapper_script_is_captured.py, tests/unit/test_the_tail_says_what_it_is_doing.py
Guard:     tests/unit/test_no_shelling_phase_is_silent.py, run after each leaking file in one process
Mutation:  drop either setenv - the paired run reddens 2
Class:     product
```

## Required Fix

Each test sets `BGA_NO_PROGRESS` through `monkeypatch` before calling
`main`, so teardown restores the environment `main` writes.

## Out of Scope

Threading `--no-progress` through instead of the environment (UX-183's
choice).

## Acceptance Test

Each leaking file followed by the shelling guard in one process: green.

## Outcome

Gap, on the round branch before the fix (`-p no:xdist -p no:randomly`):

```text
wrapper test, then shelling guard    2 failed, 12 passed
```

Close:

```text
wrapper test, then shelling guard    14 passed
tail test, then shelling guard       11 passed
```

| mutation | paired run |
|---|---|
| drop the wrapper test's `setenv` | 2 failed, 12 passed |
| drop the tail test's `setenv` | 2 failed, 9 passed |
