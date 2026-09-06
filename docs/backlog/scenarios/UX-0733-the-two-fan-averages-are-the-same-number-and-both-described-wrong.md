# UX-733: the two fan averages are the same number, and both described wrong

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-719 (the same swap, in the ranked blocks) | **Serves:** R3 reading the graph-shape block | **Topic:** analysis | **Shape:** judgement | **Area:** bga/structural

## Motivation

`UX-719`'s track found the mirror of its own defect one screen up, in
`graph_metrics`, and left it alone as out of scope. It is worse than a
swapped sentence.

`bga/structural/analyzer.py:188-191` computes both from the same graph:

```python
fanouts = [G.out_degree(n) for n in G.nodes()]
fanins  = [G.in_degree(n)  for n in G.nodes()]
```

`bga/schemas.py:2034-2041` describes them the other way round —
`avg_fanin` as "Direct dependents per element" (it is the mean
in-degree, which for this edge direction is *dependencies*) and
`avg_fanout` as "Direct dependencies per element". `UX-719` fixed
exactly this wording for the ranked blocks and did not reach here.

But the swap is undetectable from the data, because **the two values
are provably equal**. Every edge contributes one in-degree and one
out-degree, so both means are `|E| / |V|` — the handshake lemma. On
`tests/fixtures/macro_micro`:

```console
nodes 11  edges 34
mean(in_degree)  = 3.0909
mean(out_degree) = 3.0909
equal: True
```

So the page publishes two keys, under two contradictory sentences,
carrying one number that can never differ. A reader comparing them
learns nothing; a reader trusting either sentence learns the opposite
of the truth.

## Required Fix

The prose half is `UX-719`'s, mechanically: swap the two descriptions
so each names the degree it averages.

The judgement is whether both keys should exist. They are one quantity
— *edges per element* — and the honest publication is one key with
that name, `avg_fanin`/`avg_fanout` superseded the way `UX-641`
superseded `analyze/v5`. Against that: they are in a published
contract, a reader's script may name either, and `UX-719` declined to
rename keys for exactly this reason. Decide, and say which in the
Outcome; if both stay, the descriptions must say that the two are
equal by construction, or the next reader files this row again.

## Out of Scope

- The ranked `high_fanin_elements`/`high_fanout_elements` blocks.
  `UX-719` closed those, and unlike these two they carry genuinely
  different values.
- `elements.fan_in.direct_count`. It is per element, not an average,
  and it is the anchor `UX-719`'s guard already reads.

## Acceptance Test

A guard holds each average's description against the degree it
averages, derived from the graph rather than from the sentence; and if
both keys survive, asserts the equality the descriptions must then
state. Mutation: swap either description back — red, naming the key.
