# UX-595: the capacity model has a fact base and no model

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-234 (which names this as its own filing), UX-339 (the sweep), UX-594 | **Serves:** R5, the capacity operator | **Topic:** store

## Motivation

`UX-234` landed the aggregate fact-base — min/median/p95/max/MAD per
host class — and names this as the filing it does not do.
`UX-580` measured what that leaves R5 with: something aggregates, and
nothing models. Direction 9's second argued step is builders `N` plus
those profiles into utilization and wait-time distributions.

## Required Fix

A model that takes a builder count and the store's measured profiles
and answers utilization and waiting, with **every assumption printed
beside every number** — the arrival process, the service distribution,
what it does with a heterogeneous store.

## Out of Scope

- The cost translation (`UX-596`) — a separate reader and a separate unit.
- Anything requiring the requested-at instant (`UX-594`) until that lands.

## Acceptance Test

The model's output names its assumptions; mutation: remove one
assumption from the printout while the model still uses it — red.
