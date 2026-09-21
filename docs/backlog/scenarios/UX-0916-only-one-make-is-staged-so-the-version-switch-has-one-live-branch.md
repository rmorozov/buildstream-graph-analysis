# UX-916: only one make is ever staged, so `style_for_make_version`'s two branches are never both exercised

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-915 | **Found by:** round 133 — Ruslan asked for the corner cases to be covered after the fast unblock lands (2026-09-21) | **Serves:** every host that runs the examples, whatever its own make | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`style_for_make_version` has two outcomes, `fifo` and `fd`, and which
one a capture takes is decided by whichever single `make` the staging
host happened to have. Today that is 4.3 everywhere, so the `fd` branch
is the only one with a live example behind it; after `UX-915` it will
be 4.4 everywhere and the `fd` branch loses its example instead. One
staged make can only ever exercise one branch, and a repository whose
examples measure what the host decided is exactly the defect `UX-914`
names.

`UX-874`, `UX-878`, `UX-879` and `UX-880` all turn on this switch. None
of them has an example that crosses it.

## Required Fix

Stage both a 4.3 and a 4.4, and give an example a way to say which one
its elements build against, so a single run crosses the switch in both
directions on any host. Whether that is two toolchain elements in one
example, two examples, or a variable the project declares is a choice
this row makes with a reading rather than up front.

Whatever it is, the selection has to be visible in the report: a
capture that took the `fd` path and one that took `fifo` must be
distinguishable without reading the workflow that produced them.

## Out of Scope

Staging make 4.4 at all, which is `UX-915` and comes first. The rest of
the sysroot (`UX-914`). Changing any jobserver default, and `UX-913`'s
second gate.

## Acceptance Test

One CI run captures the same element under both staged makes and the
two captures report different styles, each the one its version implies.
A mutation pointing both arms at the same make must redden the guard
that holds them different — a switch with one live branch is what this
row exists to end, so a guard that passes when both arms agree guards
nothing.

`examples/11-serial-giant`'s `check_jobserver_width.py` reports no
scrubbed auth under either arm.

## Outcome
