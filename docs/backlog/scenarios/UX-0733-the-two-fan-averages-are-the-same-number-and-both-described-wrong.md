# UX-733: the two fan averages are the same number, and both described wrong

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-719 (the same swap, in the ranked blocks) | **Serves:** R3 reading the graph-shape block | **Topic:** analysis | **Shape:** judgement | **Area:** bga/structural

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

**The decision, taken here: both keys stay, and say so.** `UX-719`
declined to rename `high_fanin_elements`/`high_fanout_elements` because
`analyze/v*` is published and a reader's script may name either; the
same argument holds one screen up, and superseding two keys to save a
duplicate value is a contract move for a wording defect. So: swap the
two descriptions to name the degree each averages, and each
description states that the two are equal by construction — `|E|/|V|`,
every edge being one in-edge and one out-edge — so the next reader
sees the redundancy in the sentence rather than rediscovering it.
Collapsing them to one key is the better shape and the wrong trade at
this price; if a later round moves `analyze/v7` for another reason,
that is when to take it.

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

## Outcome

**Gap measured** - re-ran the Motivation's reading on
`tests/fixtures/macro_micro`, from `graph.json`'s edge list directly:

```text
nodes 11  edges 34
mean(in_degree)  = 3.0909
mean(out_degree) = 3.0909
equal: True
```

Matches the task file exactly; no correction needed. `avg_fanin`
averages in-degree (dependencies), `avg_fanout` out-degree
(dependents) - `bga/schemas.py:2034-2041` had them swapped.

**Close measured** - swapped the two `bga/schemas.py:2034-2041`
descriptions so `avg_fanin` says "Direct dependencies per element" and
`avg_fanout` "Direct dependents per element", per the Required Fix;
per the decision paragraph, both keys stay and each description now
also states the equality by construction (`|E|/|V|`, every edge one
in-edge and one out-edge), naming the counterpart key. `docs/guides/
cli.md` carries no `avg_fanin`/`avg_fanout` sentence (checked;
`fan_in`/`fan_out` there is `UX-719`'s ranked-block prose, untouched).

`make test-touching`: `102 file(s) selected (14 census + 88 naming the
change) · 2065 passed, 40 skipped in 64.51s`. `make lint`: clean.
`dev_baseline.py --check`: 299.

**Mutation table** (`tests/unit/
test_a_fan_average_names_the_degree_it_averages.py`, scratch-copy edit
and restore, never `git checkout --`).

| mutation | clause reddened | result |
|---|---|---|
| restore old `avg_fanin` sentence ("Direct dependents…") | `test_avg_fanin_names_dependencies_not_dependents`, `test_avg_fanin_names_avg_fanout_and_the_reason` | 2 of 8 fail |
| restore old `avg_fanout` sentence ("Direct dependencies…") | `test_avg_fanout_names_dependents_not_dependencies`, `test_avg_fanout_names_avg_fanin_and_the_reason` | 2 of 8 fail |

Each reverted from the saved copy; suite green again (8/8) after each.

**Deviation** - none from the Required Fix or the decision paragraph.
`docs/guides/cli.md` was checked, per scope, and found to carry
neither sentence - no edit made there.
