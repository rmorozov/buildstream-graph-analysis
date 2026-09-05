# UX-474: "Elements Most Worth Optimizing First (by blast radius)" ranks three elements whose blast radius is zero

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-467` found it and `tests/unit/test_the_shape_conclusions_have_a_negative_case.py` pins its precondition | **Found by:** round 72, `UX-467`'s answer key over the T1 fixture | **Serves:** the local-optimizer told which three elements to fix first, by a quantity that is zero for all three | **Topic:** analysis | **Area:** bga

## Motivation

On `tests/fixtures/shared_base_wide` — a shared base with six
dependents, the shape the blast findings exist for — `analyze`
publishes:

```text
[blast-radius-ranking] Elements Most Worth Optimizing First (by blast radius):
    1. mod0.bst (0 downstream elements)
    2. mod1.bst (0 downstream elements)
    3. mod2.bst (0 downstream elements)
```

Every element in the payload:

```text
  mod0.bst         downstream=0  structural=False
  mod1.bst         downstream=0  structural=False
  ...
  toolchain.bst    downstream=6  structural=True
```

The one element with any reach is the base, and `_ranking_findings`
correctly excludes structural elements from the *ranking* — `UX-76`
and `UX-258`, a base image with a thousand dependents is a fact about
the graph rather than a task. What is left is six elements that reach
nothing, and the finding ranks three of them and calls them the ones
"Most Worth Optimizing First (by blast radius)".

An ordering over a constant is not a ranking. The reader is being told
a priority derived from a quantity that does not vary, at MEDIUM
severity, above the fold.

**The note that would have said so is absent too.** `_blast_scale`
appends `, p90+` from the distribution and `_density_sentence`
describes it, but:

```text
blast_radius_distribution: None
```

so neither the scale tag nor the `is_flat` sentence appears. The
finding's own hedge is switched off by the same condition that makes
it wrong.

## Two things the mutation pass turned up beside it

**The gate fires in the wrong direction on these two shapes.** On the
chain the blast counts genuinely vary — `{elem0: 4, elem1: 3, elem2: 2,
elem3: 1, elem4: 0}` — and the ranking is suppressed as chain-bound.
On T1 they are all zero and it is published. The one shape where an
ordering by blast radius would carry information is the one that does
not get it, and the shape where it carries none does. Whether the
chain-bound gate is right is a separate question from this row, but
the pair is the evidence to argue it with.

**`_ranking_findings`'s own `chain_bound` guard is unreachable.**
`compute_findings` branches on `chain_bound` and only calls the
function in the `else`, so the `if chain_bound or not top_blast_radius`
on its first line can never see a true `chain_bound`. Removing it
changes no behaviour, which is how the mutation pass found it. Dead,
not wrong — but a reader (this round included) takes it for the gate,
and the real gate is fifty lines away.

## Required Fix

`_ranking_findings` publishes nothing when every element it would rank
scores zero — or publishes a sentence that says the graph offers no
blast-radius ordering, which is a genuine and useful answer for a
project whose only reach is its base. Which of the two is a judgement
about whether "there is nothing to rank here" is worth a line; the
dead-control rule (`UX-194`) and `UX-365`'s "the list opens with an
action" both argue for silence.

The clause is written and waiting in
`test_the_shape_conclusions_have_a_negative_case.py::TestThePreconditionsTheFiledRowsRestOn::test_the_only_element_with_reach_on_t1_is_structural`
— it currently asserts the defect's precondition, and closing this row
turns it into the assertion that the ranking is absent.

## Out of Scope

- The structural exclusion itself — `UX-76` and `UX-258` argued it and
  it is right; this row is about what happens when it empties the list.
- `blast-radius-structural`, which is correct on this fixture: it names
  `toolchain.bst`, which really is structural and really does reach six
  elements.
- `mesh-graph`'s separate defect, which is `UX-475`.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_the_shape_conclusions_have_a_negative_case.py -q
```

green with the clause flipped to assert absence, and the golden
snapshot regenerated if the fixture it covers changes shape.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

On `tests/fixtures/shared_base_wide`, the shape the blast findings
exist for:

```text
[blast-radius-ranking] Elements Most Worth Optimizing First (by blast radius):
    1. mod0.bst (0 downstream elements)
    2. mod1.bst (0 downstream elements)
    3. mod2.bst (0 downstream elements)
```

with `blast_radius_distribution: None`, so neither `_blast_scale`'s
percentile tag nor `_density_sentence` appeared — the finding's own
hedge switched off by the same flat counts that made it wrong.

### The fix: rank what reaches something

`_ranking_findings` now selects the elements to rank on
`downstream_count > 0` rather than truncating a pre-sorted list.
Silence rather than a sentence about there being nothing to rank —
`UX-194`'s dead-control rule and `UX-365`'s "the list opens with an
action", both of which the Required Fix cited.

The same list feeds `blast-radius-reach` (`UX-479`), so `shown` is a
subset of `reaching` and the two arms stay exactly separated by
`not shown`. On `shared_base_wide` both are now silent and
`blast-radius-structural` says the true thing:

```text
Reaching most of the graph by design: toolchain.bst (6 downstream)
  - structural elements (import) whose dependents are the graph's shape,
    not a task
```

### What silence cost, and the fixture that answers it

Stopping the ranking from ordering zeros made it **produced by
nothing**:

```console
$ python3 tools/dev_finding_coverage.py | tail -2
(a clone) 24 findings | 21 produced by a capture | 2 declared unreachable | 1 neither
  neither: blast-radius-ranking
```

That is the census guard doing exactly what `UX-460` built it for: the
covering set had no shape on which an ordering by reach carries
information. Measured over every committed capture — actionable
elements with any reach at all:

```text
a_build_that_pulls              ['lib0.bst', 'lib1.bst', 'lib2.bst']  (chain-bound)
macro_micro                     ['core.bst', 'codegen.bst', ...]      (chain-bound)
same_build_twice_cold           ['lib0.bst', 'lib1.bst', 'lib2.bst']  (chain-bound)
same_build_twice_incremental    ['lib0.bst', 'lib1.bst', 'lib2.bst']  (chain-bound)
with_timeline                   ['core.bst', 'codegen.bst', ...]      (chain-bound)
ample_capacity                  []
one_source_many_elements        []
shared_base_wide                []
```

Every capture with varying reach is chain-bound, where `UX-65` gates
the ranking; every scheduler-bound capture has nothing to rank.

So `a_chain_beside_a_crowd` joins the covering set — T7. Three
conditions have to hold at once and no other fixture holds all three:

- **the reach varies among elements someone owns** — `lib0.bst` is
  depended on by everything (9), `lib1.bst` by two, `lib2.bst` by one;
- **the run is scheduler-bound**, because a chain alone cannot be, so
  the crowd of six independent elements runs beside it on two lanes;
- **a wait category dominates**, which is what makes it the only
  committed capture where `headline.top_actions` comes from the blast
  ranking at all — `_opportunity_findings` emits `time-concentration`
  only when no category clears the floor, and `_top_actions` prefers
  concentration wherever it exists.

The third condition was found by measurement rather than by design:
the first version of the fixture had the crowd starting at zero, which
made the run execution-bound, and `top_actions` came from
`time-concentration` — which reddened two clauses in
`test_the_first_screen_is_a_decision.py` that read the blast arm.
Making the crowd wait behind `lib0.bst` is what produces the wait.

```console
$ bga analyze tests/fixtures/a_chain_beside_a_crowd/run --diagnostics --format json
diagnosis: scheduler_bound 0.571
    1. lib0.bst (9 downstream elements, at or above p99 of this run)
    2. lib1.bst (2 downstream elements, at or above p90 of this run)
    3. lib2.bst (1 downstream elements, at or above p80 of this run)
    Shape: half of this run's 10 elements reach 0 or fewer, the top tenth
           reach 2 or more (max 9)
$ python3 tools/dev_finding_coverage.py | tail -1
(a clone) 24 findings | 22 produced by a capture | 2 declared unreachable | 0 neither
```

The percentile tags and the density sentence are both there, which is
the other half of what this row recorded: the hedge is on where the
ranking is.

### Three guards that were standing on the defect

Each read `shared_base_wide`'s ranking, and each was reading a finding
that should not have been published:

- `test_the_shape_conclusions_have_a_negative_case.py::test_the_ranking_shows_the_counts_the_payload_holds`
  asserted the published counts match the payload — true, and
  **vacuously**, since every one of them was zero. It reads the T7
  fixture now, with two new clauses beside it: the counts are three
  different numbers in descending order and all above zero, and the
  distribution's tag and sentence are present.
- `test_the_first_screen_is_a_decision.py`'s scheduler-bound run. Its
  `top_actions` came from the blast ranking, so with the ranking
  silent it had no actions at all and
  `test_a_scheduler_bound_run_ranks_by_who_depends_on_it` would have
  passed over an empty list. Repointed to T7.
- `test_copy_a_finding.py`'s `RANKING` fixture — the copy text those
  five clauses read was the copy text of the defect. Repointed to T7.

The pinning clause the Required Fix named,
`test_the_only_element_with_reach_on_t1_is_structural`, is now
`test_nothing_is_ranked_where_every_candidate_reaches_nothing`: the
precondition is unchanged and still asserted, and what changed is that
an ordering over a constant is no longer published.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| Q1 | `shown = [] if chain_bound else actionable[:BLAST_RADIUS_SHOWN]` — the defect reintroduced | 2 of 22 — the census map and the pinning clause |
| Q2 | the filter's floor moved from `> 0` to `>= 0`, which admits every zero again | the same 2 |
| Q3 | `reaching[::-1]` — the ranking ordered the other way | 1 — `test_the_ranking_orders_counts_that_actually_differ`, which is what says the new clause reads the order and not just the presence |

### Deviation from the Required Fix

None on the fix. The Required Fix offered two options — silence, or a
sentence saying the graph offers no blast-radius ordering — and asked
for a judgement. Silence, for the two reasons it named itself, and
because `blast-radius-structural` already says the true thing about
that shape: an ordering-shaped absence would be a third sentence about
the same nothing.

Two things done beside it that the row did not ask for, both because
`make test` was red without them and neither is a choice about scope:
the T7 fixture (see above — the census is a gate, not advice) and the
three guards that were standing on the defect.

The row's "two things the mutation pass turned up beside it" are both
closed elsewhere in this batch: the gate firing in the wrong direction
on these two shapes, and the unreachable inner `chain_bound` guard,
are `UX-479`, which separated the three claims and deleted the dead
copy.

### The runs

```text
python3 -m pytest tests/unit/test_the_shape_conclusions_have_a_negative_case.py
                                              22 passed in 0.50s
python3 -m pytest tests/unit/test_copy_a_finding.py
                                              15 passed in 2.21s
make test-touching                            1608 passed, 16 skipped in 98.62s
make test                                     5626 passed, 27 skipped, 1 warning
                                              in 339.54s (0:05:39)
make lint                                     All checks passed!
```
