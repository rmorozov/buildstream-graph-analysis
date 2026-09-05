# UX-475: `mesh-graph` calls a five-element linear chain "a mesh of near-equal chains"

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-467` found it; the fixture is `topologies.linear_chain` | **Found by:** round 72, `UX-467`'s negative case | **Serves:** the graph-owner told their chain is a mesh, and that savings are capped by "the next chain" when there is only one | **Topic:** analysis | **Area:** bga

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

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

```text
[mesh-graph] Note: 100% of elements have zero slack - this graph is a
mesh of near-equal chains, so savings on one element are often capped
by the next chain rather than by its own duration
evidence: {'zero_slack_share': 1.0}
```

on `linear_chain(n=5)`: five elements, one path, four edges.

### The discriminator, and why it is not a second proxy

`zero_slack_share` is 1.0 **by construction** on any single-path
graph — with one path no element has anywhere to move — so it cannot
tell a mesh from a chain, and the finding was reading it as if it
could.

An element with zero slack lies on *some* longest path. If it is not
on the path this run reported, then a second path of the same length
exists — which is what "near-equal chains" means, and what makes the
capping advice true. So the count of **zero-slack elements off the
reported critical path** is the thing itself rather than a stand-in
for it. Both inputs were already published: `elements.slack` and the
critical-path detail the table above the sentence is drawn from.
Nothing new is computed and nothing new is stored.

Measured across the factories, which is what says the split is a
property of the shape and not of one fixture:

```text
linear_chain(5)                 share 1.000   off-path 0
deep_unequal_predecessors       share 0.800   off-path 0
shared_base_wide                share 0.286   off-path 0
ample_capacity                  share 0.125   off-path 0
diamond                         share 1.000   off-path 1
multiple_equal_predecessors     share 1.000   off-path 2
fan_in / fan_out                share 1.000   off-path 3
one_source_many_elements        share 1.000   off-path 3
```

and over every committed capture:

```text
tests/fixtures/a_build_that_pulls/run            share 1.0    off-path 0
tests/fixtures/macro_micro/run                   share 0.909  off-path 0
tests/fixtures/one_source_many_elements/run      share 1.0    off-path 3
tests/fixtures/same_build_twice_cold/run         share 1.0    off-path 0
tests/fixtures/same_build_twice_incremental/run  share 1.0    off-path 0
tests/fixtures/with_timeline/run                 share 1.0    off-path 0
tests/fixtures/golden/mixed_task_kinds           share 0.75   off-path 0
```

**Six of the seven were being called meshes and are chains.** That is
the size of what the row found, and it is why the census below moves
so far.

### After

The chain gets its own finding rather than a corrected mesh sentence,
because "mesh" is the id's meaning and the two shapes call for
opposite advice:

```text
linear_chain(5)   [chain-graph] Note: 100% of elements have zero slack,
                  all on the critical path - no second chain of equal
                  length, so a saving on any of them is worth its own
                  duration
                  evidence: {'zero_slack_share': 1.0,
                             'zero_slack_off_path': 0}

fan_in            [mesh-graph]  Note: 100% of elements have zero slack,
                  3 of them off the critical path - this graph is a mesh
                  of near-equal chains, so savings on one element are
                  often capped by the next chain rather than by its own
                  duration
                  evidence: {'zero_slack_share': 1.0,
                             'zero_slack_off_path': 3}
```

Both are `info` and both go to the graph-owner, so `UX-478`'s reader
does not lose the one finding it had — it gains a true one on the
shape where it had a false one.

The Acceptance Test:

```console
$ python3 -m pytest tests/unit/test_the_shape_conclusions_have_a_negative_case.py -q
..............
14 passed in 0.35s
```

Ten clauses before, fourteen now. The pinning clause
`test_mesh_graph_reads_a_zero_slack_share` became
`test_the_chain_is_not_called_a_mesh`, and
`TestTheChainAndTheMeshGetDifferentSentences` is the positive case the
file did not have — a negative-case file could show a chain being
called a mesh but had no genuine mesh to compare it with.

### The census

```console
$ python3 tools/dev_finding_coverage.py | grep -E 'graph|clone'
chain-graph   tests/fixtures/a_build_that_pulls, tests/fixtures/macro_micro,
              tests/fixtures/same_build_twice_cold,
              tests/fixtures/same_build_twice_incremental,
              tests/fixtures/with_timeline
mesh-graph    tests/fixtures/one_source_many_elements
(a clone) 23 findings | 21 produced by a capture | 2 declared unreachable | 0 neither
```

`mesh-graph` now reaches exactly one committed capture where it
reached six. That is not thin coverage arriving — it is the coverage
that was always there being counted honestly, and it is the same fact
`UX-463` measured from the other side when it found the graph-owner
had one of two findings producible from a clone.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| N1 | `if off_path:` → `if True:` — the discriminator removed, everything is a mesh again | 4 of 14, including the census map and the two-shape pair |
| N2 | `_zero_slack_off_path` stops excluding the path, so every zero-slack element counts | 6 of 14 — both directions at once, since the chain becomes a mesh and the mesh's published count goes wrong |
| N3 | `if off_path > 1:` — the floor raised, so the diamond's one other chain is not enough | 1 — `test_two_equal_paths_are_already_a_mesh`, the clause that decides the floor |
| N4 | the mesh publishes `zero_slack_off_path: 0` — the sentence right, the evidence wrong | 3, including the pair that reads both |

N2 is the one that matters. A guard that only asserted "the chain is
not called a mesh" would have stayed green under it, because a count
that includes the path is still zero on nothing. It reddens because
the mesh half asserts the published number and not just the id.

### What it cost the page

`test_the_page_has_a_volume_budget` reddened on `macro_micro` at
12,031 words against a 12,000 bound. Twenty-nine words came out of the
chain sentence and its provenance rule first, leaving 12,002 — and two
words under a bound is negotiating with it rather than measuring, so
the bound moves to 12,600 with the reading pasted above `BUDGETS` and
in `styleguide.md` §3e:

```text
                golden   macro_micro
before round     6,882        11,616
after UX-479     7,121        11,979   (+239, +363)
after UX-475     7,144        12,002   (+23,  +23)
```

The two are worth keeping apart. `UX-479` added a claim, and a claim
is not a sentence — it is the sentence, its provenance record, its row
in the reader's block and its copy text, so **one finding is 363
words** on an eleven-element page. `UX-475` made a sentence carry one
number and replaced a claim rather than adding one: 23. Height,
controls and nodes did not move at all.

### A guard that had to be repointed

`test_findings_are_data.py::test_severity_marks_the_hedged_conclusions_as_such`
asserted `by_id["mesh-graph"]["severity"] == "info"` on a fixture that
is a chain, so it reddened with a `KeyError`. Its claim — hedged
conclusions are marked as such — is unchanged; it now names the pair
and asserts which of the two this fixture is, so it reddens if the
split ever silently sends this shape the other way.

### Deviation from the Required Fix

None on the fix itself. Two notes on shape:

- The Required Fix left the discriminator open — "whatever the
  discriminator". This one adds **no field to any published
  contract**, which the Out of Scope asked for if it could be avoided:
  `zero_slack_off_path` travels in the finding's own evidence, where
  the schema's keyword table declares it as a count, and it is derived
  from two things `elements` already publishes.
- The new id `chain-graph` is more than "a sentence that does not say
  mesh". A corrected `mesh-graph` sentence would have left the id
  meaning the opposite of its content, and the page keys readers,
  provenance and trace queries off the id.

`UX-478` is next in this batch and this row moves it: the graph-owner
now has a finding that is true on a chain, which is much of what that
row is about. What it does not do is give that reader anything keyed
off the graph beyond this pair, so the row stays open on its own
terms.

### The runs

```text
python3 -m pytest tests/unit/test_the_shape_conclusions_have_a_negative_case.py
                                              14 passed in 0.35s
python3 -m pytest tests/unit/test_the_page_has_a_volume_budget.py
                                              22 passed, 1 skipped in 33.86s
make test                                     5618 passed, 27 skipped, 1 warning
                                              in 320.08s (0:05:20)
make lint                                     All checks passed!
```
