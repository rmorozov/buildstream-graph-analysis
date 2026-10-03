# UX-1323: `compare` calls two incremental runs that rebuilt different elements IMPROVED, and the cold-then-incremental refusal names no next step

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R4 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1. The README's loop (snapshot, change, snapshot):

```text
# snapshot 2 (cold -> incremental)
Refusing to compare these runs (run_mode):
Pass --allow-mismatch to compare anyway ...
# snapshot 3 (rebuilt apps/browser.bst) vs snapshot 4 (rebuilt apps/shell.bst)
Verdict: IMPROVED  (total duration -5.36s, -56.3%, 9.51s -> 4.15s)
  Why: ... No element present in both runs shrank, so what moved is in the elements this change
  added or removed.
  apps/browser.bst: disappeared (6.30s, no delta to compare)
  apps/shell.bst: appeared (1.20s, no delta to compare)
```

The sentence is at `bga/compare.py:900`. In a developer's loop every edit rebuilds a different set.

## Decomposition

Input classes: same element set (today's verdict stays); disjoint built sets; overlapping sets
where the common elements moved; overlapping where they did not; cold vs incremental (refusal).
Surfaces: `bga compare` text and json, `bga snapshot`'s automatic compare, the CI comment, exit codes.

## Required Fix

When the two runs built different element sets and no element common to both moved
significantly, the verdict is a distinct `different work` state, not improved or regressed, with
its own line saying which elements each run built; exit code unchanged from no-change. The
cold-vs-incremental refusal names what to do: the next snapshot compares incremental against
incremental, and a fresh cache directory gives the project-wide picture.

## Out of Scope

A per-element noise band.

## Acceptance Test

On the stand-in, the browser-then-shell pair reads `different work`, and a guard over two fixture
runs with disjoint built sets asserts it in text and json. Reading taken in this container.

## Outcome
