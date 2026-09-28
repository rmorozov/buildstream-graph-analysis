# UX-1080: the snapshot tail's BuildStream calls have never been timed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded

## Motivation

After the build the tail starts BuildStream again: `bst artifact
list-contents` once per 200 needed dependencies
(`tools/bst_native_build_tracer.py:4907-4940`, retried one element at
a time when a chunk fails), and `bst show --deps all` for the run
directory (`tools/bst_show_to_graph.py:253`, no timeout, unlike the
cache-key `bst show`). No reading of either exists; `bst show` alone
took about 2 s per call on the Graviton host (2026-09-25). This
container has no `bst`, so [the audit](../../audits/perf-snapshot-view-2026-09-28.md) could not take one.

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
