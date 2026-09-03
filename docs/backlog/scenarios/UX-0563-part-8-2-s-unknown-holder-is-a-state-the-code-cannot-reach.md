# UX-563: Part 8.2's `UNKNOWN` holder is a state the code cannot reach

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the maintainer deciding what the spec still promises | **Topic:** analysis

## Motivation

Spec Part 8.2 (`specification.md:625-632`) and Part 42's "Holder set
+ `UNKNOWN`" row require an unidentifiable resource holder to be
reported as `blocking_tasks = UNKNOWN, ambiguous = true` — a rule
the fixing guide's hard rules repeat ("never invent data the spec
says must be UNKNOWN"). The code:

```text
bga/attribution/blame_chain.py:556-563, :780    'ambiguous': False   # "structurally always False"
bga/validation/invariants.py:323-327            sums ambiguous_wait_us from it → Part 33.4's input is a constant 0
```

The design removed the state and the spec still describes it; the
confidence gate reads a zero that can never be anything else.

## Required Fix

A decision, recorded where the spec's readers look: either the
holder-set logic regains the `UNKNOWN` outcome (with the case that
produces it in a fixture), or Part 32 gains a registry note that 8.2's
ambiguous state is retired and 33.4's term is constant — the spec's
body is not edited (§3.12), the registry is. The hard rule in
`rules.md` follows the decision.

## Out of Scope

- Any other Part — this is one state.

## Acceptance Test

Either a fixture yields `ambiguous: true` and a guard holds it, or
the registry note exists and a guard reads `'ambiguous': False` as
declared rather than as a placeholder.
