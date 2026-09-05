# UX-684: the cached-build verdict — does the graph rebuild the cheapest subgraph?

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-682 (expected rebuild cost), UX-477 (the cold verdict's rule) | **Serves:** R3 showing evidence, R8 reading it | **Topic:** analysis | **Shape:** judgement

## Motivation

The cold build has a verdict — chain-bound / scheduler-bound /
inconclusive (`bga/findings.py:1610-1637`), with the floors and the
sweep behind it. The cached build, which is most builds, has none:
the graph owner cannot say whether the shape lets the likely changes
rebuild little, and the tool's blast findings speak of one resource
at a time.

## Required Fix

A `cached_shape` verdict from `UX-682`'s distribution: the share of
the change history whose rebuild stayed under the p50 weighted blast
("most changes rebuild the cheapest subgraph"), the elements whose
changes dominate the expected cost, and height versus weight stated
separately — stack and other assembling elements add height for
free, a single heavy element adds weight — so "split the tall chain"
and "isolate the heavy element" are two different advices. The
verdict's rule and its denominator are stated the way `UX-477` states
the cold one's.

## Out of Scope

- Simulating a proposed split — `UX-230`'s what-if prices fixes to
  durations; pricing a graph edit is its own model, filed when the
  verdict has a consumer.

## Acceptance Test

Example 06's history: the verdict names the share of changes under
the p50 blast and the dominant element; mutation: weigh by count
instead of duration — red.
