# UX-719: the bottleneck fan-in and fan-out labels are swapped

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-681 (which measured it) | **Serves:** R3 reading the graph's shape | **Topic:** analysis | **Shape:** judgement

## Motivation

`bottleneck.high_fanin_elements` ranks `G.in_degree`, and the edges
run predecessor → successor (`bga/structural/analyzer.py:322-331`), so
an in-edge is a **dependency**. The column's own sentence says the
opposite:

```text
bga/schemas.py:2183-2192  "Elements many others depend on directly"
                          "Elements naming this one as a dependency -
                           an in-degree, not a transitive count"
docs/guides/cli.md:1007   "elements naming this one as a dependency"
```

Measured on `tests/fixtures/macro_micro`, against `UX-681`'s map,
which computes the same quantity from the edge list directly:

```text
element        in_degree  out_degree  fan_in.direct_count
app.bst                8           1                    8
toolchain.bst          0           9                    0
```

`app.bst` has **one** dependent and eight dependencies. It is what the
"many others depend on it" list opens with. `high_fanout_elements`
carries the mirror error.

## Required Fix

Swap the two blocks' prose - `high_fanin_elements` ranks elements with
many dependencies, `high_fanout_elements` elements many others depend
on - in `bga/schemas.py` and `docs/guides/cli.md`. The values are
correct and must not move; only the sentences are wrong.

## Out of Scope

- Renaming the keys. `analyze/v*` is a published contract and the
  names are a defensible reading of a graph drawn this way; the
  sentences are not.

## Acceptance Test

`bottleneck.high_fanin_elements[0].element_uid` on `macro_micro` is
`app.bst`, and the block's description names dependencies rather than
dependents; mutation: restore either old sentence - the guard holding
each description against the degree it ranks reds.
