# UX-1005: bga recommends a builder count and a pool size from a capture, and the critical path gets the next token

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1004, UX-1003 | **Found by:** Ruslan on the jobserver batch thread (2026-09-24): whether to oversubscribe BuildStream's builders or native `max-jobs` depends on graph shape and the machine, and there is no rule for it | **Serves:** R5, R4 (a single-machine deployment sized from its own readings) | **Topic:** analysis | **Area:** unassigned | **Shape:** judgement

## Motivation

Builders are breadth across the graph, `max-jobs` depth inside a recipe,
and both draw on one machine. A static split fits one phase of the build
and wastes the other: `11-serial-giant`'s off arm idles two of four
cores behind `giant.bst` at `max-jobs: 2`. Under the pool the split
reduces to two numbers - builders, and tokens - with peak concurrency
about active builders plus tokens, since each running recipe keeps its
own implicit slot through configure and install. Nothing reads either
number off a capture, and tokens go first come, first served.

## Decomposition

surfaces: a `bga analyze` section beside the critical path; the pool's grant order in `tools/jobserver/pool.py`
guards: a fixture graph with a wide phase and a narrow one reads a builder count from its ready-set width and a pool size from the host's knee; a starved pool grants the critical-path element first
gap: whether ready-set width over time is recoverable from Plane 1 alone; and where admission lives - the shim taking a real token before exec'ing bwrap (builders set wide, BuildStream unmodified, the wait reported apart from the build) or a change proposed upstream to BuildStream's scheduler (Ruslan, 2026-09-24: not without modifying BuildStream)
track: `architect` first
gate: after `UX-1004`'s knee is on record

## Required Fix

Recommend builders from the capture's ready-set width and tokens from
the knee, memory per job and the pool's PSI readings; put the margin in
tokens, which can be withheld, not builders, which cannot.

## Out of Scope

Remote execution with separate executor hosts.

## Acceptance Test

`bga analyze` on `11-serial-giant` and on the fdsdk pair prints a
builder count and a pool size, each with the reading it came from.

## Outcome

Not started.
