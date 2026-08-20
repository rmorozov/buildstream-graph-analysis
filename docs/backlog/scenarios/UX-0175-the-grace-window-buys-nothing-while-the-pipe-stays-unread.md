# UX-175: the grace window buys nothing while the pipe stays unread

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-163 (the lifecycle this completes), UX-157 (the salvage it protects)

## Motivation

UX-163 raised the SIGINT grace to 300s so a big build's graceful stop
could finish and its closing Pipeline Summary — the `queue_summary`
every incompleteness sentence is built from — would survive. The
round-18 review demonstrated the grace cannot deliver that, with a
SIGINT-trapping fake bst: on interrupt, `run_wrapped`'s read loop
exits (`tools/bst_run_wrapped.py:174-184`) and **nothing ever reads
the child's stdout again**, so the summary bst writes *during* its
graceful stop never reaches `build.log` — it ends at "Stopping the
build after KeyboardInterrupt" no matter how quickly bst complies.
Secondary effect: once the pipe buffer (~64KB) fills, the shutting-down
bst blocks in `write()` and burns the entire grace before the SIGTERM
escalation kills it — the grace *causes* the slow path it was meant to
prevent.

Two adjacent seams in the same lifecycle, same review:

- `shutdown_build_group` now returns whether bst stopped on its own —
  and its only production caller discards it
  (`bst_run_wrapped.py:183`), so "say why the summary is missing
  instead of just missing it" (UX-163 item 3's own wording) reaches
  tests only. The function also carries two stacked docstrings, the
  second dead.
- **A re-extracted interrupted capture forgets it was interrupted**:
  `extract_run(interrupted=...)` exists but `bga extract` has no flag
  for it, so the paste-the-hint recovery path (UX-163's own feature)
  produces a `run/` that does not declare unfinishedness — and
  `format_post_build_interrupt` says "The build itself completed" even
  when the thing interrupted was the salvage of a *mid-build*
  interrupt.

## Required Fix

1. The shutdown path **drains the pipe to EOF** (with the grace as the
   deadline) while waiting, appending everything the stopping bst
   still says to the wrapped log — the summary arrives, and the child
   can never block on a full buffer.
2. The caller consumes the return value: a killed bst's run says "bst
   was escalated before it could print its summary" where the counts
   would have been. Delete the dead docstring.
3. `bga extract` gains `--interrupted` (and the printed hint includes
   it when the interrupted capture was mid-build), so a recovered run
   carries the same incompleteness the direct path records;
   `format_post_build_interrupt` words the mid-build-salvage case as
   what it is.

## Out of Scope

- The interrupt windows themselves (UX-163, verified working live in
  all three positions this round).

## Acceptance Test

The review's fake-bst reproduction, turned into a test: a child that
traps SIGINT, prints a marker summary and exits within the grace — the
marker is **in the wrapped log** and the escalation never fires; a
child that ignores SIGINT and floods stdout past 64KB is escalated at
the deadline with the flood captured up to it. The recovered-run path:
interrupt mid-build, interrupt the salvage, paste the printed hint —
the resulting run analyzes as interrupted (banner present), asserted
end to end. Mutation: reverting the drain to `proc.wait()` reddens the
marker assertion.
