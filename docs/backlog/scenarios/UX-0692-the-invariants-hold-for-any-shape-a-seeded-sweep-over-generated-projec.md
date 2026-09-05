# UX-692: the invariants hold for any shape — a seeded sweep over generated projects

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-465 (a project from a topology spec), UX-567 (the invariant guards), UX-367 (the volume budget) | **Serves:** R8 trusting the report on a graph nobody fixtured | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

The suite has no randomized test: every guard runs on the committed
fixtures and the one seeded scale run. The tool already has two
generators — `bga gen-synthetic --seed` (schedules) and
`bga_gen_project.py` (a BuildStream project from a topology spec,
`UX-465`) — and thirteen invariants plus a determinism guard that
should hold for *any* input. A hand exploration on a shape nobody
fixtured is what finds problems; a seed sweep is that exploration,
mechanised.

## Required Fix

A weekly CI job (and `make test-seeds N=…` locally): N seeds over
topology shapes (layers, width, kinds mix, chain/mesh, structural
share) through `gen-synthetic`, asserting I1-I13, determinism, the
volume budget at the class, and that every finding's provenance
resolves; each failing seed is committed as a fixture with its
filing. Cheap by construction — no browser, no `bst` — and the
input space the unit files never reach.

## Out of Scope

- Generated *real* builds — `UX-465`'s projects run under the bst
  tier and stay there; this sweep is the analysis half.

## Acceptance Test

A run of 50 seeds green; a planted invariant violation in the
replay scheduler — the sweep reds on a seed and names it; the seed
reruns red alone.
