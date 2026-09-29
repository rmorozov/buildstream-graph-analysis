# UX-1106: blast radius decodes every element's downstream set to sum durations over it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 150, Ruslan's review of PR #300 and the post-fix `bga analyze` profile (2026-09-28) | **Serves:** anyone opening a run of a few thousand elements | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_blast_radius_reads_the_bitset.py, absent from tests/

## Motivation

`compute_blast_radius` (`bga/diagnostics/analyzer.py:668`) reads
`reachable_downstream.get(elem_uid)` for every element, which decodes
`UX-1074`'s bitset into a `frozenset` (`bga/graph/edg.py:250`), then
sums durations over it. [The profile](../../audits/perf-analyze-profile-2026-09-28.md),
5,002 elements (`gen-synthetic --store --seed 1 --layers 40 --width
125`, round 150's P=80 Plane 2 report):

```text
bga analyze, best of 3             14.07 s   VmHWM 469 MB
decode, 5,747 sets (unprofiled)     2.88 s   RSS 87 -> 419 MB, held to the end
the same analysis, sums off bits    8.16 s   VmHWM 165 MB   text and JSON byte-identical
weighted sums alone, 5,002 el       4.10 s +329 MB -> 0.11 s +4 MB, per-element equal
weighted sums alone, 1,202 el       0.15 s  +16 MB -> 0.01 s +1 MB
```

The decode is graph-only; the sum is not (durations are Plane 1's), so
reusing graph work across captures cannot remove it. Not decoding can.

## Decomposition

Input classes: a chain, a wide layer, a diamond, a disconnected
element; a hand-built `graph_analysis` whose `reachable_downstream` is
a plain `dict`; 1,202 and 5,002 elements. Journey: `bga analyze`.

## Required Fix

In `bga/graph/edg.py`: `ReachabilitySets` gains a method that sums a
per-uid weight over one uid's mask without decoding it (per-byte
lookup tables over its topological order, built once per weight map).
In `bga/diagnostics/analyzer.py`: `compute_blast_radius` calls it when
`reachable_downstream` is a `ReachabilitySets`, and keeps today's sum
for a plain mapping. `analyze.json` stays byte-identical.

## Out of Scope

- `resource_blast`'s decode (`bga/sources.py:388`, 745 sets, 0.47 s,
  +40 MB after this fix): its rows publish the element lists.
- A per-graph memo of `build_element_graph` (78 calls, 0.59 s) and
  `compute_in_out_degree` (73 calls, 0.21 s) - two distinct graphs.
- Reusing graph-only work across captures (1.41 s after this fix).

## Acceptance Test

`tests/unit/test_blast_radius_reads_the_bitset.py`: on each input class
and `gen-synthetic --layers 20 --width 60 --seed 1`, every element's
`downstream_weighted_duration_us` equals the decode-and-sum reference,
and the `ReachabilitySets` has decoded no set after
`compute_blast_radius` returns; a plain-dict `graph_analysis` still
ranks as today. Mutation: restore `sum(... for uid in
reachable_downstream.get(elem_uid, []))`, and the decoded-set count
(1,202) reddens.
