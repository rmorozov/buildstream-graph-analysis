# UX-440: two rankings over one order, and nothing says why there are two

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 69, the clause `UX-439` left unfinished | **Serves:** anyone comparing the page's ranked list against the terminal's | **Topic:** contracts

## Motivation

`UX-439` made the blast-radius order total, which incidentally made
`top_blast_radius` and `optimization_horizon` agree — before it, they
disagreed about `core.bst` and `codegen.bst` inside one `analyze.json`:

```text
top_blast_radius     ["toolchain.bst", "codegen.bst", "core.bst", ...]
optimization_horizon ["core.bst", "codegen.bst", "lib-a.bst"]
```

They agree now because both read one order. **Nothing asserts that, and
nothing says why there are two lists at all.** `UX-439`'s Required Fix
asked for "one ranking, or a stated reason for two" and its Outcome
records the clause as unfinished rather than met — this is that row.

The two are not obviously the same question: one names elements by
blast radius, the other is an optimization horizon with savings
attached. If that difference is real it should be written down, and if
it is not, one of them should go.

## Required Fix

- **Say what each list is for**, in the schema's own sentence, or merge
  them.
- **A guard that they do not contradict each other** where they overlap
  — the same pair in a different order is the defect `UX-439` measured,
  and it is currently prevented only as a side effect.

## Out of Scope

- **The ordering itself**: `UX-439` settled it and this does not
  reopen the key.
- **Adding a third ranked list** — whatever this decides, it decides
  for the two that exist.

## Acceptance Test

```bash
bga analyze @last --format json
```

Where an element appears in both lists, their relative order agrees,
and each list's purpose is stated where a reader meets it. A mutation
reversing one list must redden the guard.

## Outcome

**Round 70, 2026-08-31.** One bullet built, one refused with a
counterexample, and the refusal is the finding.

### They are two questions, not one ranking published twice

| where | ranked by |
|---|---|
| `elements.top_blast_radius` | what a change to this element rebuilds |
| `optimization_horizon` | what fixing it saves, greedily, in sequence |

The horizon does not read the blast-radius order at all: it recomputes
the longest path after each fix and takes the largest realizable saving,
so its second entry is the best fix *after* the first rather than
today's second-best. Nothing about either list implies the other.

Note also that this item's Motivation quotes `top_blast_radius` at the
document's top level. It has not been there since `UX-344` moved the
element population under `elements`; the published path is
`elements.top_blast_radius`, and at the old path the value reads as
absent on every run — which is how the first measurement here came back
empty on all three fixtures.

### Why they agree on the fixtures

They do, and it is a property of those two graphs:

```console
$ bga analyze tests/fixtures/macro_micro/run --format json --diagnostics
  elements.top_blast_radius ['toolchain.bst', 'core.bst', 'codegen.bst', 'lib-a.bst', 'lib-b.bst']
  optimization_horizon      ['core.bst', 'codegen.bst', 'lib-b.bst', 'lib-d.bst', 'lib-f.bst']
  overlap ['core.bst', 'codegen.bst', 'lib-b.bst'] | tb ranks [1, 2, 4] | oh ranks [0, 1, 2]
```

### The Required Fix's second bullet asserts something false

`topologies.blast_radius_disagrees_with_horizon` is an ordinary build —
a cheap common ancestor with several dependents, one of which is a
hundred times longer than it — the shape of any project with a
toolchain at the bottom. On it:

```text
elements.top_blast_radius  ['hub.bst', 'heavy.bst', 'leaf0.bst', 'leaf1.bst', 'leaf2.bst']
optimization_horizon       ['heavy.bst', 'hub.bst']
overlap ['heavy.bst', 'hub.bst']  |  tb ranks [1, 0]  |  oh ranks [0, 1]
```

A guard asserting "their relative order agrees where they overlap"
would pass on both committed fixtures and redden the first time someone
analysed a build like this one — a false invariant kept green by the
fixture population, which is the class this repository keeps finding.
So it was not built. `TestTheyAreTwoQuestions` pins the **inversion**
instead, so a later round reaching for the same idea meets a build where
matching would be wrong rather than a fixture where it happens to hold.

### What was built

- **Both sentences name the other list and say the orders differ**, so a
  reader who meets one knows it is not the other. `top_blast_radius`
  gains "Not the order to fix things in: that is `optimization_horizon`
  … the two legitimately disagree"; `optimization_horizon` gains "a
  different question from `elements.top_blast_radius` and gives a
  different order".
- **`tests/unit/test_the_two_rankings_answer_two_questions.py`**, nine
  clauses, 0.23s (small by measurement, so `tests/tiers.py` is
  unchanged): the inversion, that the inverted pair really is in both
  lists, that each list is ordered by the key its own sentence names,
  and that each sentence points at the other.

### Falsification

| # | mutation | result |
|---|---|---|
| R1 | the horizon takes the longest element instead of the best saving | **red** — both `TestTheyAreTwoQuestions` clauses |
| R2 | `top_blast_radius` emitted sorted by uid instead of by rank | **red** — the inversion clause and `test_the_blast_ranking_is_ordered_by_what_it_says` |
| R3 | the blast sentence stops naming the horizon | **red** — `test_the_blast_ranking_names_the_horizon` |
| R4 | `leaves=0`, so the hub has one dependent instead of four | **green — did not discriminate** |
| R4b | `hub_us` and `heavy_us` swapped, so the contrast goes away | **red** — both `TestTheyAreTwoQuestions` clauses |

**R4 is recorded because it failed to discriminate.** The inversion does
not depend on the fan at all — one dependent is enough — it depends on
the duration contrast, which R4b confirms. The leaves stay in the
topology because they give the blast ranking more than two entries to be
in order, which a different clause reads, and the docstring now says so
rather than leaving a knob a later reader would assume is load-bearing.

### Deviation from the Required Fix

**The second bullet was refused, not deferred.** It asks for a guard
that the two lists do not contradict each other; they can and do, on an
ordinary build, and the counterexample above is the evidence. The
property that is true of each list on its own — ordered by its own
stated key — is guarded instead. The first bullet is met as written.

### The suite

```console
$ make lint
All checks passed!

$ make test
5399 passed, 28 skipped, 1 warning in 273.77s (0:04:33)
```
