# UX-906: the jobserver's corner cases live in twelve task files and no register

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-841..UX-852, UX-878, UX-884, UX-888 | **Found by:** the 2026-09-20 rollout thread — the owner asks which corner cases the integration has to survive, and answering it meant reading twelve closed task files | **Serves:** R2 (whose recipe is the corner case), R5 and R4 (who need to know what the mode does not cover before switching it on) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

What the injected jobserver has to survive is real knowledge this
repository has paid for — a GCC LTO ICE (`UX-878`), a `make` policy
whose exclusion is unproven (`UX-884`), a ninja wrapper that had to own
ninja's `-j` (`UX-888`), a pin rule that must never force `-j1`
(`UX-842`), a minimal sandbox that broke on a shim needing `dirname`
(round 126) — and it lives scattered across twelve task files and two
rounds. Nobody can answer "what breaks under this mode" without reading
all of them, which is the question the owner asked and the question
every adopter asks first.

The list in section 7a of
[`continuous-build-improvement.md`](../../design/continuous-build-improvement.md)
is this round's attempt at it, written from the tree. It is a
brainstorm, not a measurement: some rows have a guard and a closed task
behind them, several have neither.

## Required Fix

Turn that list into a register with a column that says, per corner case,
which of three states it is in: **guarded** (a test or an example
fails when the mode breaks it), **known and unguarded** (a task file
names it, nothing fails), or **unexamined** (this round wrote it down
from reasoning, and no capture has met it). Each guarded row names its
guard; each unexamined row is a candidate filing rather than a claim.

The register is derived where it can be — the policy table in the shim
is code, and the closed rows are files — rather than a list that drifts
from both.

## Decomposition

surfaces: the design document's section 7a, the jobserver's policy table in `tools/native_trace/bwrap_shim.py`, and a guard that reads both
guards: a test that every policy the shim implements appears in the register, and every register row claiming a guard names one that exists
gap: the unexamined rows cannot be resolved by reading — each needs a capture that meets the case, which is why they are candidates and not findings
track: `implementer` for the derived half; the states are the session's to judge
gate: with `UX-905`, which will meet several of these rows on a real project

## Out of Scope

Fixing any corner case the register finds unguarded — each one is its
own row, filed when the register says which. Corner cases of the capture
that are not about the jobserver.

## Acceptance Test

The register lists every policy the shim implements, each row carries
one of the three states, every "guarded" row names a guard that exists,
and a guard reddens when a policy is added to the shim without a row.
Mutations: add a policy to the shim (the guard names the missing row),
point a row at a guard that does not exist (red), change a state word to
one not in the three (red).

## Outcome
