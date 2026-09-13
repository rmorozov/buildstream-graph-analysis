# UX-830: the serial chains, ranked, not the longest one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-719 (the bottleneck view), UX-681 (fan-in) | **Found by:** round 115, the design review | **Serves:** R3 deciding which chain to split | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`bottleneck` draws one "Longest serial chain" (walk capture:
toolchain.bst → storm.bst → all.bst, length 3) beside a "Waiting on it"
list. Blast has a ranked table with a detail row per element; a chain
has one exhibit. On a graph where the second chain is a second's
shorter than the first, splitting the first moves the critical path to
the second and the page says nothing about it until the next capture.

## Required Fix

`serial_chains`: the top N chains by duration-weighted length,
disjoint or overlapping as measured, each with its members, its wall
share and the element whose split shortens it most; the bottleneck
section draws them as a ranked table with the members as a folded cell
(`UX-532`'s shape). N follows the row cap.

## Decomposition

Input classes: a chain graph (`a_chain_beside_a_crowd`), a wide flat
graph (`shared_base_wide`, chains of length 2), and the scale graph;
the journey is R3's "which chain" question in the answer key.

## Out of Scope

- What-if on a split — `whatif/v1` already prices a lowered duration; a split is a graph change, Direction 17's question.
- The rail's per-element view — `UX-254`.

## Acceptance Test

On the scale export the table has ≥ 5 chains, the first equal to
today's longest chain; mutation: return one chain — the guard on the
count reds.
