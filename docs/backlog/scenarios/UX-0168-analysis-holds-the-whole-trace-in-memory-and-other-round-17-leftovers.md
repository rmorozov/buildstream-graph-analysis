# UX-168: analysis holds the whole trace in memory, and other round-17 leftovers

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-157/UX-148/UX-160 (the landings these trail)

## Motivation

The round-17 review's remaining-sharp-edges list, filed so the
big-project axis keeps a worklist. The headline is capacity:
`load_and_summarize` slurps the entire `trace.log` into one string and
then a full event list (`tools/bst_native_build_tracer.py:3498-3500`).
A multi-hour build with hundreds of thousands of processes means
hundreds of MB to GB of RSS at analysis time — on the machine that
just finished the build, in the phase right after it. The census has
the same shape one size down: `census_project` computes a per-element
dependency closure (`:2259`) that is quadratic-ish on thousands of
elements, serial, announced by one line.

The small ones, each a sentence:

1. `run_teed`'s read loop waits for the pipe's write end to close,
   which every sandbox descendant holds — a sandboxed process that
   daemonizes past bwrap's exit hangs the shim under `--diagnose`
   (`bwrap_shim.py:527-543`). Unlikely under `--die-with-parent`;
   worth a read timeout or a documented limit.
2. `format_sandbox_stderr`'s elided branch indexes
   `row['stderr_path']` without `.get` (`tracer.py:4560`).
3. `SELF_TEST_ARGV = SELF_TEST_ARGV = "…"` double assignment
   (`bwrap_shim.py:570`).
4. The interrupt notice prints between the Plane 2 summary and the
   Plane 1 report ("analyzed above" when half is below).
5. The census summary reads "0 with static binaries (spine traced)" —
   the parenthetical describes the zero elements, which is at best a
   riddle; say "spine not needed" when the count is 0.
6. `--list` and `_warn_if_large` stat-walk the whole store every
   snapshot invocation — seconds on a many-GB store, per run; cache
   or sample.

## Required Fix

Stream the trace parse (line-iterate, aggregate incrementally — the
format is line-oriented and the summarizer's aggregations are all
associative); memoize the census closure. Then the six one-liners.

## Out of Scope

- Trace format changes (the bytes are fine; the reader is not).
- UX-108's overhead measurement (still its own item).

## Acceptance Test

Peak RSS of `bga analyze` on a synthetic 1M-line trace is bounded (a
test generates one and asserts RSS < ~4× the largest single-element
aggregate, or simply < a fixed budget where the old reader exceeds
it); census on 1,000 synthetic elements completes in seconds not
minutes (timed bound). Each one-liner: the riddle wording gone, the
KeyError branch `.get`s, the double assignment single, the notice
placed after both reports, a daemonizing-descendant test times out the
tee rather than hanging.
