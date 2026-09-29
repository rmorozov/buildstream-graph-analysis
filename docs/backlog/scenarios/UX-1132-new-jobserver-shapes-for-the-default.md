# UX-1132: three new example shapes and their arm legs test the "safe cap plus auto" default

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1010 | **Found by:** round 152's architect, splitting UX-1014 into what a session can build and what needs the owner's hosts | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** runner:bst-examples

**Guard:** none — open, no guard named yet

## Motivation

UX-1014 asks for readings on shapes the default has not met. The
shapes themselves, their `graviton_arms.sh` legs and a probe that keeps
its captures are buildable here; the Graviton spend, the x86 16-core
host and a real project stay with UX-1014.

## Decomposition

Input classes: two independent giants; a chain of wide elements; a memory-bound giant under PSI withdraw.
Journey: `bga capture run --jobserver off|auto` then `bga analyze`, on `bst-examples` and the Graviton arms.

## Required Fix

`examples/14-two-giants` (two independent giants, two critical chains),
`examples/15-wide-chain` (a chain of wide elements), and
`examples/16-memory-bound-giant` (a giant whose units are memory-heavy,
so the pool's PSI withdraw fires), built on the same staged toolchain as
`05`-`13`; a `graviton_arms.sh` leg per shape; `codspeed-probe.yml`
gains those legs and an `upload-artifact` of the arms' captures. Each
shape builds once on `bst-examples` and its designed property is
checked there.

## Out of Scope

Running the Graviton arms (UX-1014, at the round's end, by the owner's
word of 2026-09-29), the x86 host, a real project.

## Acceptance Test

`bst-examples` builds each new shape and prints its property check
(two giants building concurrently, each chain element wider than 1,
the memory giant's peak RSS per job). Mutation: make the second giant
`notparallel`; the two-giants width check fails.

## Outcome
