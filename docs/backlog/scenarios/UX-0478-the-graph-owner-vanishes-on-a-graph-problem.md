# UX-478: the graph-owner is not offered a reader on the one build whose defect is the graph

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-477` (the diagnosis both R3 findings key off) | **Found by:** round 72, `UX-468`'s planted walk 3 | **Serves:** the graph-owner who opens the report on a strict chain and finds their reader is not there | **Topic:** analysis

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

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, and what it really was

The reader was missing, but the mechanism is not "R3 has too few
findings" — it is that **every finding R3 had was a function of
measured durations**. `criticality` needs a contested path;
`mesh-graph`/`chain-graph` read the slack the durations produce. So
the same graph with the seconds tripled changes whether R3 exists,
which the row's own table recorded:

```text
  per link   diagnosis          readers offered
    1.5s     scheduler_bound    local-optimizer, recipe-author, ci-gatekeeper, capacity-operator
    4.5s     chain_bound        local-optimizer, graph-owner,   ci-gatekeeper, capacity-operator
```

A reader about shape whose presence turns on how long the build took
is not a reader about shape.

### The finding

`graph-width` reads `elements.unweighted_depth` and nothing else.
Group the elements by depth and you have the dependency stages;
nothing in a stage can start before the stage above it finishes,
whatever the capacity, so **the widest stage is a ceiling on
concurrency that no number of builders lifts**. That is the shape
making something impossible, stated as the number it is:

```text
linear_chain(5)     The graph is 5 elements in 5 dependency stages, and its
                    widest stage holds 1 - so no more than 1 can ever be
                    building at once, whatever the capacity
shared_base_wide    The graph is 7 elements in 2 dependency stages, and its
                    widest stage holds 6 - ...
ample_capacity      (silent)
```

`ample_capacity` is the negative case the Required Fix asked for: one
stage, every element independent, the widest stage is the whole graph
and the shape forbids nothing. A finding there would be describing the
*absence* of a constraint as if it were one.

### The Acceptance Test

```console
$ python3 tools/bga_gen_project.py \
      --spec tests/fixtures/specs/planted-serial-chain.json --out /tmp/chain
{"out": "/tmp/chain", "name": "planted-serial-chain", "elements": 7}
$ cd /tmp/chain && bga snapshot -- bst build all.bst >/dev/null
$ bga analyze @last --diagnostics --format json | python3 -c '...'
['local-optimizer', 'recipe-author', 'graph-owner', 'ci-gatekeeper', 'capacity-operator']

R3: leads_with 'mesh-graph', findings ['mesh-graph', 'graph-width']
  graph-width | The graph is 9 elements in 8 dependency stages, and its
                widest stage holds 2 - so no more than 2 can ever be
                building at once, whatever the capacity
  mesh-graph  | Note: 100% of elements have zero slack, 1 of them off the
                critical path - this graph is a mesh of near-equal chains ...
```

`graph-owner` is listed, which is the clause. Two notes on what it
leads with, since the row asked about that too:

- The lead is `mesh-graph`, and after `UX-475` that sentence is
  **true** here — the generated project is 9 elements (7 from the spec
  plus the generator's `base`/`runtime` scaffolding) and one zero-slack
  element really is off the critical path, so there are two chains of
  equal length. It says the shape, with the count that makes it so.
- `graph-width` sits second because the mesh/chain sentence is
  rendered inside the concentration table it qualifies (`UX-70`'s
  placement) while `graph-width` belongs with the descriptive findings
  (`UX-365`'s ordering: actions, then what the run *is*). Reordering
  the report to put a description above an action was not worth doing
  for a lead, and is not what the row is about.

**As above with a real build, the run needs a cold cache** — the
generated project is deterministic, so a second run of these exact
commands is incremental and publishes no durations at all. These
figures are from `XDG_CACHE_HOME=/tmp/ux478cache bga snapshot -- bst
build all.bst`, the same reproducer `UX-479` recorded.

### The reader, on every shape

```text
linear_chain(5)                R3=yes chain-graph      diagnosis=chain_bound
diamond                        R3=yes mesh-graph       diagnosis=chain_bound
shared_base_wide               R3=yes criticality      diagnosis=scheduler_bound
one_source_many                R3=yes mesh-graph       diagnosis=scheduler_bound
ample_capacity                 R3=yes criticality      diagnosis=chain_bound
independent_branches           R3=yes mesh-graph       diagnosis=chain_bound
fan_in                         R3=yes mesh-graph       diagnosis=chain_bound
multiple_equal_predecessors    R3=yes mesh-graph       diagnosis=chain_bound
deep_unequal_predecessors      R3=yes chain-graph      diagnosis=chain_bound
blast_disagrees                R3=ABSENT               diagnosis=chain_bound
```

That was the state after `UX-475`, and `blast_radius_disagrees_with_horizon`
was the last hole: `zero_slack_share` 0.4 is under the shape threshold
and its criticality list scores every element 1.0 or 0.0, which
`_criticality_findings` drops as ranking nothing. It has two
dependency stages, so `graph-width` speaks about it and R3 is offered
on all eleven.

### The census

```console
$ python3 tools/dev_finding_coverage.py | grep -E 'graph-width|clone'
graph-width   tests/fixtures/a_build_that_pulls, tests/fixtures/macro_micro,
              tests/fixtures/same_build_twice_cold,
              tests/fixtures/same_build_twice_incremental,
              tests/fixtures/shared_base_wide, tests/fixtures/with_timeline
(a clone) 24 findings | 22 produced by a capture | 2 declared unreachable | 0 neither
```

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| P1 | `if stages <= 1:` → `<= 0:` — the negative case removed, so a flat set is told it has a ceiling | 3 of 20, including the census map and `test_no_shape_finding_speaks_about_every_shape` |
| P2 | `widest = len(depth)` — the widest stage becomes the whole graph, so the ceiling is never binding | 3, all three that read the published numbers |
| P3 | the stage count read from `critical_path_detail` instead of the graph's depth | **nothing, first time.** See below |
| P3′ | the same mutation, after the fixture below | 1 — `test_the_stages_are_the_graph_and_not_the_measured_path` |

### The mutation that did not redden, and what it cost to fix

P3 is the mutation that matters most for this row: it swaps the
graph's own depth for the length of the **measured** critical path,
which is exactly the class of defect the row was filed about. It
passed all nineteen clauses.

The reason is that on every shape this repository had committed, the
two numbers are equal — the deepest chain is also the heaviest, so the
critical path visits every dependency stage:

```text
                              stages   critical path rows
deep_unequal_predecessors          4                    4
blast_disagrees                    2                    2
graph_with_terminal                2                    2
independent_branches               3                    3
diamond                            3                    3
```

`deep_unequal_predecessors` gains a `shallow_us` parameter (default
unchanged, so the covering set is untouched): make the shallow
predecessor heavy enough and the critical path runs through it — two
elements — while the graph still has four dependency stages.

```text
default          stages=4 path=['deep0.bst', 'deep1.bst', 'deep2.bst', 'target.bst']
heavy shallow    stages=4 path=['shallow.bst', 'target.bst']
```

With that fixture the same mutation reddens on the number:
`assert 2 == 4`. The clause is `test_the_stages_are_the_graph_and_not_the_measured_path`,
and it is the one this row would have shipped without.

### What it cost the documents

Two bounds moved, both restated with the reading rather than the
record reshaped to fit:

- `test_no_level_carries_nothing`'s golden `deeper_than_three` bound,
  0.47 → 0.48. Each new finding costs the document a `provenance[]`
  record whose `rule` block is six leaves, all four deep, and nothing
  else; a 695-leaf document gaining deep leaves without shallow ones
  moves the ratio. Measured after: golden 0.4705 (695 leaves, 327
  deep), `macro_micro` 0.4121 (2,138, 881) — both far below the 0.574
  and 0.671 `UX-344` was filed on. The note records that the real
  answer if this keeps climbing is `UX-483`, not a looser bound.
- The README's stated report length, 91 → 92 lines. The pasted block
  itself did not change: the new sentence lands inside a region the
  block already elides.

### Deviation from the Required Fix

None. All three clauses done: a finding keyed off the graph rather
than the diagnosis, its reader named at birth with `docs/design/roles.md`
changed in the same commit (fixing guide §8), and the negative case in
`UX-467`'s census file with a shape it must not fire on.

One judgement worth stating: the Required Fix listed `Parallelism
Profile`, `Max Depth`, `Serialized` pairs and `Bottlenecks Identified`
as candidates. Parallelism profile and bottleneck counts are both
**measured** — they describe what the scheduler did with these
durations, which is the property this row was filed against. Depth is
the only one of the four that is a fact about the graph alone, and the
widest stage is what makes it actionable rather than trivia.

`graph-width` carries **no evidence path** in its provenance record,
which is unusual and deliberate: what it reads is
`elements.unweighted_depth`, a map keyed by element uid, and `record`
inlines whatever a path resolves to. Citing it would put a copy of
that population in the record — `UX-479` measured what that costs and
`UX-483` is the row for the builder that permits it. The three numbers
are in the finding's own evidence and the rule sentence names them.

### The runs

```text
python3 -m pytest tests/unit/test_the_shape_conclusions_have_a_negative_case.py
                                              20 passed in 0.43s
make test-touching                            1537 passed, 17 skipped in 101.22s
make test                                     5624 passed, 27 skipped, 1 warning
                                              in 332.52s (0:05:32)
make lint                                     All checks passed!
```
