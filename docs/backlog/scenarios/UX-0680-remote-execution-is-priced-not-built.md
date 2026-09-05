# UX-680: remote execution is priced, not built

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-30 (the sweep), UX-9 (what the tool sees under RE) | **Serves:** R4 and R8 deciding whether to buy it | **Topic:** analysis

## Motivation

Direction 5 left remote execution "deliberately unfiled"
(`directions.md:591-599`), and `UX-9` recorded why: under
BuildStream's REAPI the tool observes nothing about the remote
bottleneck. Both true, and neither answers the question a CI owner
actually asks first — *what would it buy?* Two mechanisms, priced
differently: BuildStream's REAPI moves whole sandboxes to workers
(the agent keeps staging and waiting; the worker's `max-jobs`
matters there); compiler-level RE (`recc`, `reclient`, `goma`) moves
compilations from inside a sandbox that BuildStream isolates from the
network by default. The tool half-prices both today — the sweep at
unlimited builders, and Plane 2's per-element CPU share — and never
says so.

## Required Fix

A `remote_execution_whatif` finding: the sweep run to the unbounded
builder count (what REAPI removes: the builder cap), and the per-
element compute share that a compiler-level service would move off
the agent (cc1plus/ld CPU seconds, Plane 2's `by_binary`), each as a
wall-clock projection with the assumption stated; the doc sentence
distinguishing the two mechanisms in `real-project.md`.

## Out of Scope

- Observing a remote build — `UX-9` stands.

## Acceptance Test

Example 06's finding says what unbounded builders buy (the sweep's
number) and what moving cc1plus off the agent buys (its share of the
critical path); mutation: sum the two — the additivity guard reds
(they are not additive, and the finding says so).
