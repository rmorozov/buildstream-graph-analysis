# UX-679: a jobserver every sandbox joins — the prototype bga can run

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-105 (the bwrap shim), UX-675 and UX-676 (the instruments that judge it) | **Serves:** R4 and R5 — dynamic sharing instead of static tuning | **Topic:** capture

## Motivation

Every native build system BuildStream drives speaks the GNU jobserver
protocol (`make`, `ninja`, `cmake`'s generators, `cargo -j`), and
BuildStream runs no jobserver — so five sandboxes each believing they
own eight cores is the whole utilization problem. The tool already
injects into every sandbox (the `bwrap` shim mounts the hook; the
hook is `LD_PRELOAD`ed in every process) and already measures what
happens inside (Plane 2). A jobserver FIFO passed through the same
shim, with `MAKEFLAGS=--jobserver-auth` and the ninja/cmake
equivalents set in the sandbox environment, is a prototype no other
tool is placed to build — and its evaluation is `UX-676`'s envelope
before and after.

## Required Fix

A design spike, not a feature: `bga capture --jobserver N` runs a
jobserver outside the sandboxes, binds the FIFO in through the shim,
sets the environment; the snapshot records it as a capture option;
`UX-676`'s envelope on the same project with and without it is the
result, pasted in the Outcome. Whether it becomes a supported mode is
decided on that number.

## Out of Scope

- BuildStream's own remote execution — a different mechanism
  (`UX-680`).
- Build systems without jobserver support — they keep their static
  `max-jobs` (`UX-677`).

## Acceptance Test

Example 06 captured both ways: the envelope's under-utilized share
and the wall clock, side by side, on one machine; the shim guard
holds that the FIFO is bound only when the flag is given.
