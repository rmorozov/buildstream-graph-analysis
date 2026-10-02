# UX-1292: the stale claims the docs audit found are corrected, and the retired stub is removed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** none | **Found by:** the docs audit (2026-10-02, findings 1, 7, 9, 10) | **Serves:** R1, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`docs/design/roles.md:43` says R5 has "no queueing model, no arrival
rates", though `capacity-model/v1` ships through
`bga snapshot --capacity N,RATE`. README.md:117 and
`what-the-viewer-answers.md:53,86` say the viewer serves "eighteen"
questions; `bga.provenance.TRACE_QUERIES` holds 24 keys (whether the
page serves all 24 is unverified). `continuous-build-improvement.md:12-16`
still says it waits on "a one-line move" as of 2026-09-20.
`guides/optimization-walkthrough.md` is a 14-line retired stub.

## Required Fix

R5's cell names only what is still missing (arrival rate measured,
not typed; a price per builder). The viewer count is read from the
code, and a guard ties the prose to it. The design note's status is
dated to its real state. The stub is deleted and inbound links point
at `real-project.md`.

## Out of Scope

The restructure (UX-1289, UX-1290).

## Acceptance Test

`grep` for each stale phrase returns nothing; the count guard reddens
when `TRACE_QUERIES` gains a key and the prose does not.

## Outcome
