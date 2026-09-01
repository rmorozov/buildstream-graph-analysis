# UX-478: the graph-owner is not offered a reader on the one build whose defect is the graph

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-477` (the diagnosis both R3 findings key off) | **Found by:** round 72, `UX-468`'s planted walk 3 | **Serves:** the graph-owner who opens the report on a strict chain and finds their reader is not there | **Topic:** analysis

## Motivation

`UX-468` generated a project that is six elements in one line — no
branch, nothing to parallelise — built it, and read the published
reader index:

```console
$ bga analyze @last --diagnostics --format json \
    | python3 -c 'import json,sys; print([r["id"] for r in json.load(sys.stdin)["readers"]])'
['local-optimizer', 'recipe-author', 'ci-gatekeeper', 'capacity-operator']
```

**No `graph-owner`.** `FINDING_READERS` gives R3 exactly two findings —
`mesh-graph` and `criticality` — and neither fired, so `reader_index`'s
dead-control rule (`UX-194`: a report with no capacity numbers offers
no capacity reader) removed the reader.

The rule is right. The consequence here is not: R3's question is *"What
does the shape of this graph make impossible?"*, and the shape made
everything impossible, and the reader was dropped.

The same spec with the per-element seconds tripled — an identical graph
— brings it back:

```text
  per link   diagnosis          readers offered
    1.5s     scheduler_bound    local-optimizer, recipe-author, ci-gatekeeper, capacity-operator
    4.5s     chain_bound        local-optimizer, graph-owner,   ci-gatekeeper, capacity-operator
```

So R3's presence is a function of `UX-477`'s denominator, not of the
graph. Meanwhile the front door pointed the reader at element-level
advice and at the capacity sweep:

```text
  link0.bst is the first thing to fix - this is what changing it rebuilds.
  This build is scheduler-bound: 1.4s of wall-clock is beyond the critical path
      - the sweep says what more builders would buy.
```

on a run whose own `Parallelism Profile` is `min=1.0x, avg=1.1x,
max=2.0x`.

## Required Fix

`UX-477` fixes the denominator and this reader comes back on *this*
project. That is necessary and not sufficient, because R3 would still
be reachable only through a threshold:

- **R3 needs a finding that is true of a graph's shape rather than of
  a diagnosis.** The candidates are already computed and published —
  `Parallelism Profile` (avg 1.1x), `Max Depth` (7 of 9 elements),
  `Serialized` pairs, `Bottlenecks Identified: 7` — and none of them
  is a finding, so none reaches a reader. One structural finding,
  keyed off the graph and not off wall-clock, is the fix.
- **Say what it is a finding *about*.** `UX-231`'s rule: it names its
  reader at birth, and `docs/design/roles.md` changes in the same
  commit (fixing guide §8).
- **The negative case is the point.** `tests/unit/test_the_shape_
  conclusions_have_a_negative_case.py` (`UX-467`) already pins which
  shapes produce which conclusions; the new finding joins that census,
  with a shape it must **not** fire on.

## Out of Scope

- **Offering every reader always.** `UX-194`'s dead-control rule is
  what stops the page carrying an empty capacity section, and `UX-203`
  is the older defect on the other side. The fix is a finding that
  fires, not a reader that is offered with nothing behind it.
- **`mesh-graph`'s wording**, which is `UX-475` — it calls this same
  chain "a mesh of near-equal chains" when it does fire.
- **`criticality`'s threshold** — whether its own cut is right is a
  separate question from whether R3 has a structural finding at all. It
  fired on `planted-fat-shared-base` and not here, and either answer to
  that question leaves this row's defect exactly where it is.

## Acceptance Test

```bash
python3 tools/bga_gen_project.py \
    --spec tests/fixtures/specs/planted-serial-chain.json --out /tmp/chain
cd /tmp/chain && bga snapshot -- bst build all.bst >/dev/null
bga analyze @last --diagnostics --format json \
  | python3 -c 'import json,sys; print([r["id"] for r in json.load(sys.stdin)["readers"]])'
```

lists `graph-owner`, and the finding it leads with says the shape.

## Outcome

_Not started._
