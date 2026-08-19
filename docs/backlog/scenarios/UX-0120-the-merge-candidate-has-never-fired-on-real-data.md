# UX-120: the merge candidate has never fired on real data

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-100 (reopened by this filing)

## Motivation

UX-100's acceptance named a positive case: *"a purpose-built
fine-grained example (N trivial elements sharing one heavy dependency)
… the merge candidate names the group, and the projected saving is
within the documented band of a real merged rebuild."* That fixture was
never built and the clause never ran — and unlike the task's two other
deviations, both recorded in the file, this omission is recorded
nowhere. The merge-candidate branch and its replayed projection have
fired only on synthetic unit-test input; every real capture it has seen
(`examples/06`, fdsdk incremental) correctly produced the *negative*
answer, which cannot distinguish a working detector from an inert one —
the exact evidence gap `examples/07` was built to close for UX-46.

Round 12 reproduced the negative results live (no candidates on either
capture) and downgraded UX-100 to 🟡 accordingly.

## Required Fix

Build the fine-grained fixture the acceptance describes (an
`examples/06` variant with sub-second libs sharing the staged
toolchain), capture it, and run the full loop: the merge candidate
names the group with its projected saving; then actually merge the
group and rebuild, and record measured-vs-projected. If the projection
misses its own documented band, that is the finding — fix or re-hedge
the projection before returning UX-100 to 🟢.

## Out of Scope

- The split-candidate half (its fdsdk evidence path ran).

## Acceptance Test

UX-100's original clause 1, run and pasted: fixture, capture, the
fired candidate, the real merged rebuild's number, and the band
comparison. `examples/06/optimized` still yields no candidate.
