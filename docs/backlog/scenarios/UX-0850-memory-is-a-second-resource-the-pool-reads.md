# UX-850: memory is a second resource the pool reads

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-845, UX-849 | **Found by:** round 117, Direction 20 | **Serves:** R5 (a machine that overcommitted memory before) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

A token is a core; nothing in the protocol says bytes. `UX-678` put
memory in the sweep and `max_jobs_advice` refuses a row whose overlap
peak RSS exceeds the host's memory - after the fact. Under the mode
the server knows each element's peak RSS from the plan before its build
starts and the host's free memory now.

## Required Fix

`tools/bst_native_build_tracer.py`: before the broker grants a
proxy's first token beyond the implicit one, it checks free memory
(`/proc/meminfo` `MemAvailable`) against the element's planned peak
RSS times the tokens it would hold; below that it withholds, recorded
as `memory_withheld` in the ledger; where `/proc/pressure/memory`
exists, `some avg10` above a bound reads tokens back from the pool the
way `UX-845`'s CPU bound does.

## Decomposition

Input classes: a plan with peak RSS, a plan without (no withholding),
PSI present and absent, an element whose peak exceeds the machine
(one implicit token only); the journey it extends is R5's "does this
machine fit this build" question.

## Out of Scope

Swap accounting and cgroup limits - declined until a capture shows
them binding.

## Acceptance Test

`tests/unit/test_the_pool_withholds_for_memory.py` drives the broker
with a scripted `MemAvailable` series and a plan; mutation: ignore the
plan's peak - red.
