# UX-861: a builder count above the host's cores is never recommended verbatim

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-116 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R5 (a recommendation the operator can apply as read) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`compute_capacity_recommendation` (`bga/correlate.py`) takes the
CPU constraint as `host_cores * builders / cores_busy` and binds on the
smallest of three; nothing clamps it. When the graph and memory
constraints allow more, the CPU figure decides alone, and the
repository's own fixture asserts it recommends 16 builders on an 8-core
host. `UX-116` bounded the *absent* constraint (never infinite); the
present one still names a builder count above the cores it sits beside.

## Required Fix

`bga/correlate.py`: a CPU-bound `recommended_builders` is clamped to
`host_cpu_count`, the constraint row records `clamped_from` (the
unclamped figure) and the finding's sentence says the host's cores
bound it; `bga/schemas.py` gains the key (additive).

## Decomposition

Input classes: CPU allows under, at and above the cores; the journey
it extends is R5's capacity question from `UX-116`.

## Out of Scope

A memory-bound or graph-bound figure above the cores, which the host
can hold; re-deriving the constraint from a peak rather than the average.

## Acceptance Test

`tests/unit/test_capacity_recommendation.py`: the fixture at
`cores_busy=2.0, host=8, builders=4` reads `allows 8` with
`clamped_from 16`; mutation: remove the clamp - red.
