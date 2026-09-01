# UX-474: "Elements Most Worth Optimizing First (by blast radius)" ranks three elements whose blast radius is zero

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-467` found it and `tests/unit/test_the_shape_conclusions_have_a_negative_case.py` pins its precondition | **Found by:** round 72, `UX-467`'s answer key over the T1 fixture | **Serves:** the local-optimizer told which three elements to fix first, by a quantity that is zero for all three | **Topic:** analysis

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
