# UX-1389: `bga view` says Plane 2 is beside the run, then draws it absent

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** walk seed 7 (2026-11-27) | **Serves:** R6, R3 | **Topic:** viewer | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

[`walk-seed-7.md`](../../audits/walk-seed-7.md) findings 2 and 3: on
`tests/fixtures/macro_micro/run` with its `plane2.json` beside it, `bga view run
--export e.html` prints "Plane 2 was captured — its report is beside this run —
but the raw trace log ... was not kept", and the page it writes says "Plane 2 was
not captured for this run, so there is no per-process detail". `bga analyze` and
`bga correlate` find that `plane2.json` unasked; `bga view` has no `--plane2`
and does not. A CI user reads two answers to one question.

## Decomposition

Input classes: Plane 2 report beside the run, given by flag, absent. Journey: extends the walk's seed 7 class.

## Required Fix

`bga view` reads the Plane 2 report the other commands find beside a run, or
its message stops saying one is there. Either way the stderr and the page agree.

## Out of Scope

Keeping the raw trace log for a timeline.

## Acceptance Test

On the fixture above, the export's planes census and its stderr agree on
Plane 2, and a mutation that drops the beside-the-run lookup reddens it.
