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
