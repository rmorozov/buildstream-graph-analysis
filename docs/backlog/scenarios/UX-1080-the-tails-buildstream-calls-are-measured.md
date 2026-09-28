# UX-1080: the BuildStream calls bga makes around the build have never been timed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded

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
