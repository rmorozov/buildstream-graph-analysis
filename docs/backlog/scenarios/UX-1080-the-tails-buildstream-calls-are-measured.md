# UX-1080: the BuildStream calls bga makes around the build have never been timed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded

## Motivation

Before the build, `bga snapshot` starts BuildStream up to three times
beside the build itself: `bst --version` (`bga_doctor.check_bst`, from
`why_the_build_cannot_start`), `bst show` for the cache key set
(`tools/bst_native_build_tracer.py:8508`, silent, 300 s timeout), and
with `--jobserver` one more `bst show` (`UX-1011`). After the build the
tail starts BuildStream again: `bst artifact
list-contents` once per 200 needed dependencies
(`tools/bst_native_build_tracer.py:4907-4940`, retried one element at
a time when a chunk fails), and `bst show --deps all` for the run
directory (`tools/bst_show_to_graph.py:253`, no timeout, unlike the
cache-key `bst show`). No reading of either exists; `bst show` alone
took about 2 s per call on the Graviton host (2026-09-25). This
container has no `bst`, so [the audit](../../audits/perf-snapshot-view-2026-09-28.md) could not take one.

Measured afterwards with BuildStream 2.8.1 in the audit container
(a PATH shim timing every `bst`), `examples/06`:

```text
call                                  cold (40.2s)   warm (5.1s, build 1.07s)
bst --version (doctor, before)           0.38s          0.31s
bst show, key set (before)               1.16s          1.18s
bst artifact list-contents (after)       1.29s          -  (nothing built)
bst show --deps all (after)              1.17s          1.27s
bst --version (hostinfo, after)          0.29s          0.26s
bga's own share outside the build        5.6s           4.0s
```

On a warm build BuildStream restarts are 3.0 of bga's 4.0 s, and the
snapshot takes 4.8x the build. `bst show --deps all` with the graph
format took 11.21 s at 1,201 elements and 42.28 s at 5,001
(`genproj.py`). `list-contents` at scale needs built artifacts and is
still unread.

## Decomposition

Input classes: a cached build and a cold one; a project of tens and of thousands of elements. Journey: `bga snapshot`'s tail.

## Required Fix

In `tools/bst_native_build_tracer.py`: Time both on `bst-examples` and a freedesktop-sdk-sized graph on the
bench host, cached and cold; then decide whether declared-vs-used
leaves the hot path (computed by `bga analyze`/`view` on demand) and
give `bst show` a timeout.

## Out of Scope

The pre-build `bst show` calls (`UX-1011`).

## Acceptance Test

The reading is pasted in the Outcome with the bench run id; the
decision names its guard.

## Outcome

**Bench host:** the Graviton host is not reachable from this
container; every reading below is local (bst 2.8.1, bubblewrap 0.9.0,
this container) - the same numbers already pasted into the
Motivation from [the audit](../../audits/perf-snapshot-view-2026-09-28.md)'s `bstshim` run of `examples/06` and
`genproj.py` at 1,201/5,001 elements (`bga snapshot` on a cache-busted
copy; `bst show --deps all --format ...`).

**Route:** `progress.timed_call(argv)` (`bga/progress.py`), a context
manager yielding `{verb, wall_us, exit}`. Buffered in `_CURRENT_CALLS`
because a call inside `with timed(name):` runs before that phase's own
row exists; the enclosing `timed()`'s `finally` drains the whole buffer
into the row it is about to append. `bga_snapshot.main` wraps the
doctor/preflight window itself in `progress.timed("before the build")`
- a named, announced phase like every other one - rather than leaning
on drain-on-close, which a verifier run on a real capture caught
crediting the doctor's `bst --version` to `Plane 2 report` (the first
phase `take_snapshot` actually opens). Drain-on-close stays as the
general fallback for a call made with nothing open at all (still
guarded, `test_a_call_with_no_phase_open_rides_the_next_one_that_closes`).
`take_snapshot` calls the new `progress.set_on_row` instead of
`reset_ledger`, so the writer attaches without discarding the phase
already recorded. Wired at all four sites: `bga_doctor.check_bst`,
`bst_native_build_tracer._list_contents`, `bst_show_to_graph.run_bst_show`,
`hostinfo._version_line` (only for `name == "bst"` - `bwrap`/`buildbox-run`/`cc`
are not BuildStream restarts). `TAIL_PHASES` (UX-1077/1078's pinned
list) gains `"before the build"` at the front.

**Timeout:** `run_bst_show` had none. `BST_SHOW_TIMEOUT_S = 300`
(`tools/bst_show_to_graph.py`) - the pre-build key-set `bst show`'s own
bound (`UX-842`/`UX-1011`), 7x the largest reading here (42.28s at
5,001 elements). The poll loop kills the process and `run_bst_show`
raises `RuntimeError("bst show timed out after ...")` rather than
hanging; the call row still lands with `exit` set to the killed
process's return code.

**Declared-vs-used recommendation (not implemented):** `read_artifact_contents`
already runs inside the "Plane 2 report" phase (`load_and_summarize`,
`tools/bst_native_build_tracer.py:6826`), which is on the hot path
already - moving it off would need `bga analyze`/`view` to read
`declared_vs_used` from a file the capture never wrote, and nothing
asked for that store shape. Leave it where it is: `list-contents`
measured 1.29s cold on `examples/06` (11 elements) and needs built
artifacts, so its cost at scale is still unread - the number this
recommendation would need does not exist yet.

**Gap measured:** the guard against the base tree (`963e4f25`, `git
archive`): `timed_call` and `set_on_row` do not exist, `run_bst_show`
takes no `timeout` - `6 failed in 0.62s`
(`test_the_tails_buildstream_calls_are_measured.py`).

**Close measured:** `python3 -m pytest tests/unit/test_the_tails_buildstream_calls_are_measured.py
tests/unit/test_the_snapshot_records_its_tail.py tests/unit/test_the_tail_says_what_it_is_doing.py`
-> `18 passed in 2.16s`. `make test-touching --base 963e4f25` -> `3821
passed, 62 skipped`, one pre-existing failure
(`test_every_cas_writing_bst_gated_file_reaches_the_isolation`,
reproduced identically at the base tree with none of this track's
edits applied - unrelated).

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `check_bst` drops `call["exit"] = result.returncode` | `test_check_bst_records_a_call` | 1 failed, 5 passed |
| `timed()` drains an empty list instead of `_CURRENT_CALLS` | all seven of this file | 7 failed, 11 passed |
| the timeout branch never fires (`if False:`) | `test_run_bst_show_timeout_kills_rather_than_hangs` | 1 failed |
| `bga_snapshot.main` drops the `"before the build"` wrap, back to a bare call (drain-on-close) | `test_the_doctor_call_sits_under_before_the_build`, both UX-1077/1078 phase-list guards (`TAIL_PHASES`) | 5 failed, 13 passed |

Reverted from the scratchpad's copy each time; clean (`7`/`18` passed).

**Deviation:** a verifier run on a real capture found the doctor's call
landing under `Plane 2 report` via drain-on-close alone - fixed by
giving it its own `"before the build"` phase (above); everything else
matches `wall_us`/`verb`/`exit`, the row shape UX-1078's Decision named
for `calls`.
