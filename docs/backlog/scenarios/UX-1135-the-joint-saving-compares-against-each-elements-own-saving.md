# UX-1135: the joint saving compares against each element's own saving, not the horizon's steps

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-74 | **Found by:** the 0.5.0 release walk, seed 4 (round 152, commit `74aa14f2`) | **Serves:** R1, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_joint_saving_is_priced_one_element_at_a_time.py`

## Motivation

On `tests/fixtures/macro_micro` the report says "Together, the top 3
are worth 23.1s (50% of the build) - exactly the sum of their
individual savings, so they are three separate pieces of work that do
not overlap", for core, codegen and lib-b. But
`bga whatif --element codegen.bst` reads `43.200s -> 43.200s (saves
0.000s)`: codegen is worth nothing alone, and only after core is fixed.

`sum_of_individual_us` (`bga/analyzer.py`, the `joint_saving` block)
sums the optimization horizon's *step* savings, each measured after the
steps above it are done. Those telescope, so `joint >= sum` holds by
construction and the sentence claims independence on every run.

## Decomposition

surfaces: `joint_saving` in `bga/analyzer.py`, its sentence in `bga/findings.py`, the golden snapshot
guards: an element worth 0 s alone and more after another is fixed makes the sentence say the set must be worked in order; a set of independent elements still reads as separate
gap: none - `compute_joint_saving(graph, durations, [uid])` already prices one element alone

## Required Fix

`sum_of_individual_us` sums each element's own saving priced alone.
The sentence says the savings add, overlap (joint below the sum), or
compound (joint above the sum: an element is worth more once another
is fixed, so work them in the listed order).

## Decision

- `sum_of_individual_us` = sum over the joint set of `compute_joint_saving(graph, durations, [uid])` (each element priced alone, as `bga whatif --element` does - verified to agree on the fixture).
- Three relations, keyed on joint vs that sum (tolerance 1 ms): equal -> "exactly the sum of their individual savings, so they are separate pieces of work that do not overlap"; joint below -> the existing "less than ... fixing one makes the others worth less"; joint above -> "more than the X s they are worth one at a time - <the element(s) worth less alone> pay off only once <earlier one> is fixed, so work them in the order listed". Keep the evidence keys; add a `relation` string ("add"/"overlap"/"compound") beside `savings_add`, which keeps meaning joint == sum within tolerance.
- Regenerate the golden snapshot and document-shape figures with `tools/dev_refresh_analysis.py --write`, never by hand.
- Guard: `tests/unit/test_the_joint_saving_is_priced_one_element_at_a_time.py`. Mutations: sum the horizon steps again (red); swap the above/below branches (red).
- Taken in the track: the pricing moved out of `Analyzer` into `price_joint_saving` in `bga/graph/edg.py` so the guard prices a graph directly; `JOINT_SAVING_TOLERANCE_US = 1_000` beside `JOINT_SAVING_SET_SIZE`.
- Taken in the track: `joint_saving.worth_more_after` (the steps worth more at their horizon step than alone, by more than 1 ms) names the "pay off only once" elements; the "earlier" ones are those listed before the first of them. Both new keys are declared in `bga/schemas.py`'s `joint_saving` section (additive); only `relation` joins the provenance paths - a list value has no leaf `value` and `provenance.render` raised `KeyError: 'value'` on it.
- The "add" sentence drops "three": the set is `JOINT_SAVING_SET_SIZE` at most, not always three.
- `docs/guides/cli.md` names both keys in the `joint_saving` row and its surface figure moves 602 -> 604 keys, as `test_the_documents_keep_up_with_the_contracts.py` requires.

## Out of Scope

The horizon's ordering; the headline table's own set.

## Acceptance Test

`bga analyze tests/fixtures/macro_micro/run` no longer calls the top 3
"separate pieces of work"; it names the order, and its individual sum
matches `bga whatif` per element.

## Outcome

**Gap measured.** Base `2c672f3c`, `bga analyze tests/fixtures/macro_micro/run`:

```text
Together, the top 3 are worth 23.1s (50% of the build) - exactly the sum of their individual savings, so they are three separate pieces of work that do not overlap
```

with `sum_of_individual_us 23050000` = the horizon's steps summed, while `bga whatif --element` prices core.bst 12.050s, codegen.bst 0.000s, lib-b.bst 4.000s alone.

**Close measured.** Same command after the fix:

```text
Together, the top 3 are worth 23.1s (50% of the build) - more than the 16.1s they are worth one at a time - codegen.bst pays off only once core.bst is fixed, so work them in the order listed
```

`sum_of_individual_us 16050000` = 12.050 + 0.000 + 4.000, the three `bga whatif --element` savings; `relation compound`, `savings_add False`. The golden `mixed_task_kinds` stays `add` (11000 = 11000). Guard: 4 passed.

**Mutation table** (`python3 -m pytest -n 2` on the guard):

| mutation (`bga/graph/edg.py`, `price_joint_saving`) | reddened | count |
|---|---|---|
| `sum_us = sum(step["saving_us"] for step in steps)` (the horizon steps again) | compound, overlap, whatif-agrees | 3 failed, 1 passed |
| `elif joint_us > sum_us:` (above/below swapped) | compound, overlap, whatif-agrees | 3 failed, 1 passed |
| reverted from the copy | - | 4 passed |
