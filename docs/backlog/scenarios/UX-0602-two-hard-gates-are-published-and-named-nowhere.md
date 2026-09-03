# UX-602: two hard gates are published and named nowhere

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-567 (the I6 gate), UX-566 (the advisory map) | **Serves:** anyone reading `confidence.hard_gates` to decide whether a run is trustworthy | **Topic:** contracts

## Motivation

Architecture review 14 measured the gate list against the Part that
declares it:

```text
$ python3 -c "json.load(...with_timeline/analyze.json)['confidence']['hard_gates']"
['blame_chain_coverage_full', 'critical_path_coverage_full',
 'dominator_coverage_full', 'occupancy_within_capacity',
 'ordering_violations_zero', 'run_identity_consistent']          6
$ sed -n '1913,1926p' docs/spec/specification.md                 4
$ grep -n 'run_identity_consistent\|occupancy_within_capacity' <36 front-of-house .md>
0 hits
```

`occupancy_within_capacity` arrived with `UX-567` this round;
`run_identity_consistent` predates it. Both are published, both gate a
run's trustworthiness, and neither is named in Part 33.1 or in any
document a reader opens.

## Required Fix

Part 33.1's list and the published set agree, derived rather than
restated — the `UX-564` shape, a `§32.7.x` row recording the decision
because Part 33's own text is outside the region a round may edit.
A guard reads `confidence.hard_gates` against whichever list becomes
authoritative, so a seventh gate cannot arrive unnamed.

## Out of Scope

- Editing Part 33's text — the spec outside Part 32 is read-only for a round.

## Acceptance Test

Mutation: publish a seventh gate without recording it — red naming
the key; drop one from the record — red the other way.
