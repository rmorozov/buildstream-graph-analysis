# UX-87: the efficiency gates silently stop gating when occupancy_ratio is absent

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-39, UX-40 (both done)

## Motivation

Both efficiency gates read `occupancy_ratio` from the two runs; if
either run lacks it, the gate helpers return False — pass — with
nothing printed (`bga/compare.py:468-500`). A pipeline that believes it
is gating on efficiency is not, and no output says so. This is the
identical failure mode UX-40 was filed to eliminate for the confidence
interaction ("a gate that is not running must say it is not running"),
one field over. UX-40's own fix text is the precedent: fail-open is a
legitimate policy, *silent* fail-open is not.

## Required Fix

When `--fail-on-efficiency-regression`, `--max-efficiency-drop` or
`--min-efficiency` is requested and either run has no `occupancy_ratio`,
print a one-line stderr warning naming the run and the missing field
(mirroring the UX-40 low-confidence warning), and publish
`efficiency_gate_evaluated: false` in compare's JSON so a CI consumer
can distinguish "passed" from "did not run". Optionally a strict flag
(`--require-efficiency-signal`) that turns the condition into a failure
for pipelines that would rather break than not gate.

## Out of Scope

- Why a run might lack occupancy (producer-side; any legacy or
  hand-built run directory can).

## Acceptance Test

Compare a run directory with `occupancy_ratio` stripped against a
normal one with `--fail-on-efficiency-regression`: exit 0 **and** a
stderr line naming the missing signal, and
`.efficiency_gate_evaluated == false` in `--format json`. With
`--require-efficiency-signal`, non-zero exit. Existing behavior with
both signals present is unchanged, including the gate exit codes.
