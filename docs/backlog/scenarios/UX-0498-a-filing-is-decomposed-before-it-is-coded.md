# UX-498: a filing is decomposed before it is coded

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-426 (the loop this gives a first step) | **Serves:** the implementing session, before its first edit; the round that wants two sessions on one slate | **Topic:** docs

## Motivation

The house procedure goes filing → code → guard → falsify → close, and
nothing between the filing and the first edit asks how the work
splits. Measured on rounds 66-73:

```text
tasks closed with 1 commit     51
tasks needing 2-4 commits      26      (a design found wrong after the first)
commits that were CI/tier/index housekeeping   19 of 162
```

The repeated shapes: a guard written for the population a fixture
happened to have (`UX-388`, `UX-365`, `UX-367` — one class each, found
one at a time); items that turned out to share a file and serialized
late; and every track colliding on the same three index files at the
end. Round 64's test plan named the *classes* (zero/one/many, legacy
contract, cold/incremental, spine on/off, shim/Chrome/export, this
machine/CI-only); nothing asks a task to enumerate them before its
guards are written.

## Required Fix

A `decompose` skill, invoked before implementing anything wider than
one module and when planning a batch:

1. **Surfaces**, derived — `git diff --stat` after a sketch,
   `make test-touching ARGS=--why`, `dev_js_deps --graph` for the
   viewer, `--schema` when a key moves; one row per surface naming
   the document it makes wrong and the guard family that reads it.
2. **Partition** — the input-class table with the boundary that bit
   each class, one guard per class, a class with no guard filed as a
   gap.
3. **Tracks** — parallel iff surfaces are disjoint; the three shared
   index files are touched only by the orchestrating session; a track
   runs in a worktree and reports touched-vs-declared surfaces.
4. **The gate** — per item `test-touching` + falsify; per batch one
   PR opened first and one `make test`, *in addition to* §3 until
   `UX-500` measures.

Output: a five-line `## Decomposition` block in the task file or the
round document. `CLAUDE.md` names the skill in the order a task uses
them.

## Out of Scope

- An implementer agent that runs a track in a worktree — `UX-504`;
  the agents guard forbids editing today and that is a rule change.
- Replacing §3's per-item suite with the batch gate — `UX-500`
  measures first.
- A guard that a task file *carries* a Decomposition block — one
  round of use first; the block's value is unmeasured.

## Acceptance Test

`tests/unit/test_the_agent_configuration_holds.py` green with the
skill in place (name, description with its trigger); `CLAUDE.md`
within its guards; the skill's commands each run on this tree.

## Outcome (round 74, 2026-09-01) — 🟢 Done

### The gap, measured

```text
commits per closed task, rounds 66-73:  1 → 51 tasks · 2 → 16 · 3 → 9 · 4 → 1
housekeeping commits (CI/tier/index)    19 of 162
skills naming a step before the first edit   0
```

### After

`.claude/skills/decompose/SKILL.md`, 91 lines: surfaces (derived by
four commands that run on this tree), the partition table with six
dimensions and the item that bit on each boundary, tracks with the
four shared files named, the gate with `UX-500` as its measurement.
`CLAUDE.md` lists it second in the skills order.

```text
$ python3 -m pytest tests/unit/test_the_agent_configuration_holds.py -q
62 passed
```

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | description loses its "Use before" trigger | `test_each_description_says_when_to_use_it` |

### Deviation from the Required Fix

None. The block's value is unmeasured, which is why no guard requires
a task file to carry one (Out of Scope, third bullet).
