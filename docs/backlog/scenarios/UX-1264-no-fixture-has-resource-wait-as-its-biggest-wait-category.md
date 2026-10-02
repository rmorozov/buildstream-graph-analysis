# UX-1264: no fixture has resource_wait as its biggest wait category, so wait-category's step is unexercised

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-163 verification of UX-1256 (2026-10-02) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** test_every_finding_publishes_its_step.py::test_the_wait_category_step_is_the_resolved_hint

## Motivation

No fixture has resource_wait as its biggest wait category, so wait-category's step equalling the resource-wait hint (`bga sweep`) is unexercised.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     No new fixture: two committed ones already lead with resource_wait (shared_base_wide, a_chain_beside_a_crowd, measured with `bga analyze <run> --format json` at 4db16afe). Add shared_base_wide to RUNS and replace the resource_wait skip with an equality check against resolve_attribution_hint(category, document["capacity_verdict"]), plus the command `bga sweep <run>`.
Rejected:  a new topology in topologies.py and the covering set: it duplicates a shape that is already committed and adds a fixture to every covering-set guard; a macro_micro variant: Plane 2 overrides the hint there (_plane2_capacity_hint), so it would test a different branch.
Files:     tests/unit/test_every_finding_publishes_its_step.py
Guard:     tests/unit/test_every_finding_publishes_its_step.py::test_the_wait_category_step_is_the_resolved_hint holds the claim that on shared_base_wide the resource_wait step text is the resolved hint and its command is `bga sweep`.
Mutation:  in bga/findings.py wait-category, pass `hint + "."` (or drop the sweep command) for resource_wait_us only. Today it passes because of the skip; after the change it must go red.
Class:     product
Split:     one track, first in the finding-text track: UX-1271 reads this run in its wording guard.
Question:  none. Note for the track: if test_every_finding_carries_one_step reddens on shared_base_wide, that is a real gap and gets its own row; do not exempt it.

## Required Fix

A fixture whose biggest wait category is resource_wait; the guard reads the step equal to the hint.

## Out of Scope

The step text (UX-1256).

## Acceptance Test

Mutation: change the wait-category step for resource_wait, and the guard reds.

## Outcome (2026-10-02)

### The gap, measured

Base `b35c30e3`'s copy of the guard, run with wait-category's resource-wait
step mutated to `hint + "."` (`mutate.py`, scratchpad): RUNS held golden and
`macro_micro`, neither leads with resource wait, so the claim never ran.

```text
7 passed in 0.49s
```

### The close, measured

`shared_base_wide` joins RUNS (`bga analyze tests/fixtures/shared_base_wide/run
--format json`: wait-category `resource_wait_us`, 77.0%, 8.7 s, capacity checks
not run). The step equals `resolve_attribution_hint(category,
capacity_verdict)`, the command starts `bga sweep `; the resource-wait skip is
gone, and `test_a_fixture_leads_with_resource_wait` pins the fixture's category.

```text
tests/unit/test_every_finding_publishes_its_step.py  10 passed in 1.20s
```

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| M1 | resource-wait step `hint + "."` | resolved-hint `[shared_base_wide]`, 1 failed, 9 passed |
| M2 | resource-wait step command `None` | resolved-hint `[shared_base_wide]`, 1 failed, 9 passed |
