# UX-901: the jobserver is a subtool behind a boundary, not a mode woven through bga

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-841..UX-852 (the mode as it landed), UX-851 (the capture option) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 3) — the owner's proposal: keep the jobserver integrated for before/after measurement, and build it so it can later move into a separate project of BuildStream helpers | **Serves:** R5 and R4 (the mode's value, measured), R2 (an element whose pin must survive), and every reader who needs bga to answer without it | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

Until Direction 20, `bga` measured and never acted. The jobserver acts:
it injects a token pool into sandboxes, and the cost of acting is
already on the record — round 126's minimal-sandbox breakage and
`UX-878`'s GCC LTO ICE. That is a different risk class from a reader,
and it belongs behind a boundary rather than distributed through the
capture path, for two reasons that are not the same:

- **Extractability.** The owner intends the jobserver to be able to
  leave for a helpers project. What decides whether it can is whether
  its surface is a boundary or a set of call sites.
- **Non-dependence.** A tool whose answers require its own intervention
  to be switched on has stopped being an instrument. A capture with the
  mode off must answer everything a capture with it on answers, minus
  the ledger the mode itself writes.

## Required Fix

Name and document the boundary, then hold it with a guard: which module
owns the pool, the wrappers and the policy table; what bga calls to
start and stop it; and what crosses back — the token ledger, and nothing
else. Publish the mode's own facts as contract data (`UX-847`'s ledger
in Plane 2) rather than as something only the subtool's logs hold, so
that a future move takes the code and leaves the answers.

State in the same document what the boundary is *not*: it is not a
plugin system, and bga does not gain a second one for anything else.

## Decomposition

surfaces: the tracer's jobserver modules under `tools/`, the capture option `UX-851` added, `docs/design/architecture.md`'s Plane 2 map, and the Plane 2 contract's `jobserver` block
guards: a capture with the mode off carries every key a capture with it on carries but the ledger; an import guard that names which modules may reach the pool
gap: whether the boundary is a process boundary (the subtool is spawned) or an import boundary (a package with a declared surface) — the first extracts more cleanly, the second keeps the measurement cheap
track: session's own — it is an architecture decision with a measured consequence
gate: after `UX-895`, whose overhead number tells the boundary what it may cost

## Out of Scope

Moving the code to another repository. Changing the mode's default,
which stays off until a compile-bound capture's wall clock says
otherwise (Direction 20's bar). Any new intervention.

## Acceptance Test

The architecture document names the boundary and what crosses it; a
guard fails when a module outside the named set imports the pool; a
capture with `--jobserver off` and one with `auto` produce key sets
differing only by the jobserver block. Mutations: import the pool from
an unlisted module (red), drop one key from the off-capture (the set
comparison names it).

## Outcome
