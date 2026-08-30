# UX-440: two rankings over one order, and nothing says why there are two

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 69, the clause `UX-439` left unfinished | **Serves:** anyone comparing the page's ranked list against the terminal's | **Topic:** contracts

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

_Not started._
