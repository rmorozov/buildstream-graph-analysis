# UX-681: fan-in — what an element depends on, ranked

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-479 (blast for elements), UX-407 (never-read edges) | **Serves:** R2 minimising incoming dependencies, R3 spotting the suspicious fan-in | **Topic:** analysis | **Shape:** judgement

## Motivation

```text
downstream_count / blast_radius / blast_radius_distribution    bga/findings.py:1256-1391  — fan-out, with deciles
grep fan_in|upstream_count|consumers bga/*.py                   0 hits                     — fan-in does not exist
compute_dominators                                              bga/graph/edg.py:371, called once at :950 — never published
```

The element owner's first question — how many things do I pull in,
and which of them do I actually use — has the second half answered
(`UX-407`'s never-read edges) and no first half. The graph owner's
"suspicious fan-in" is the same number ranked.

## Required Fix

Per element: direct and transitive upstream counts, the share of
those edges Plane 2 saw read (`UX-407`), and the dominator — the one
element every path from the roots passes through, which is the
rebuild gate a developer waits on. Ranked with deciles like the
blast distribution, by kind, with the same structural exemption. A
`fan_in` section and a `fan-in-*` finding family mirroring
`blast-radius-*`.

## Out of Scope

- Pruning edges — the never-read list is the advice; the owner edits
  the recipe.

## Acceptance Test

Example 06: lib-f's transitive fan-in names codegen among the
never-read; the dominator of app.bst is core.bst; mutation: count
direct edges as transitive — the closure guard reds.
