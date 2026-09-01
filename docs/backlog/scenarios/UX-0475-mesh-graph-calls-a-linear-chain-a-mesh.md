# UX-475: `mesh-graph` calls a five-element linear chain "a mesh of near-equal chains"

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-467` found it; the fixture is `topologies.linear_chain` | **Found by:** round 72, `UX-467`'s negative case | **Serves:** the graph-owner told their chain is a mesh, and that savings are capped by "the next chain" when there is only one | **Topic:** analysis

## Motivation

`linear_chain(n=5)` is the least mesh-like graph that exists: five
elements, one path, four edges. `analyze` says:

```text
[mesh-graph] Note: 100% of elements have zero slack - this graph is a
mesh of near-equal chains, so savings on one element are often capped
by the next chain rather than by its own duration
evidence: {'zero_slack_share': 1.0}
```

The evidence is the whole defect. `zero_slack_share` is **1.0 by
construction** on any single-path graph — with one path, no element
has anywhere to move, so every element has zero slack. The finding
reads that share as evidence of a *mesh*, which is fixing guide §5 in
a shipped conclusion: an instrument reading a proxy for the thing it
names.

The consequence is not cosmetic. The sentence tells the reader their
saving will be "capped by the next chain", and on a chain there is no
next chain — the saving is exactly the element's own duration, which is
the opposite of what they are told. A graph-owner acting on it would
decline the one optimization that does work.

`mesh-graph` is one of the graph-owner's two findings, and
`UX-463` measured that reader as having one of two producible from a
clone. This is what the thin coverage was hiding.

## Required Fix

Distinguish "many near-equal paths" from "one path". Zero slack is
necessary and not sufficient: a mesh needs *several* paths of similar
length, which the graph already knows — the critical path is computed,
the path count is derivable, and `linear_chain` has one.

Whatever the discriminator, the two shapes must produce different
sentences, and the fixture pair is already committed:
`topologies.linear_chain` (one path) against a genuine mesh. The
clause that pins the current behaviour is
`test_the_shape_conclusions_have_a_negative_case.py::TestThePreconditionsTheFiledRowsRestOn::test_mesh_graph_reads_a_zero_slack_share`,
and closing this row rewrites it into the assertion that a chain gets
the chain sentence.

## Out of Scope

- The mesh sentence itself where it is *right*. On a real mesh the
  advice is sound and this row does not touch it.
- `blast-radius-ranking`'s separate defect, which is `UX-474`.
- Adding a path-count field to any published contract unless the fix
  needs one — the critical path is already published and the
  discriminator may be derivable from what is there.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_the_shape_conclusions_have_a_negative_case.py -q
```

green with the chain producing a sentence that does not say "mesh",
and a mutation that removes the discriminator reddening it.
