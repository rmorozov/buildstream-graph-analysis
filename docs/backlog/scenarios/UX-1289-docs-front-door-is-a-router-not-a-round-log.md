# UX-1289: `docs/README.md` is a one-screen router by job, and the round log moves under `audits/`

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** none | **Found by:** the owner's docs audit request (2026-10-02, "stale or incomplete, or quite messy"); audit finding 3-4 | **Serves:** R1, R4, R5, R8 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`docs/README.md` (388 lines) is the front door, and about 60% of it is
a list of ~130 audit-round links (lines 195-330) plus five audits
filed as "case studies". The "commands to know first" (lines 24-42)
repeat README.md's quick start and `cli.md`, interleaved with UX ids.
The doc map is duplicated in `README.md:284-293`. A newcomer scrolls
past the round log before reaching anything they can act on.

## Required Fix

`docs/README.md` becomes one screen: an "I want to..." table by job
(try it, optimise a real project, run a pilot in CI, share a capture,
read the report, look up a command or a contract), each row one link.
The round list and the audit-only "case studies" move to
`docs/audits/README.md` (linking `round-register.md`, which already
derives the list). README.md's doc map links the router instead of
repeating it. Hand-typed contract counts in `docs/README.md:94-109`
are derived from `bga.contracts` by a guard or dropped.

## Out of Scope

Rewriting the guides themselves (UX-1290, UX-1291).

## Acceptance Test

`docs/README.md` ≤ 80 lines; every row links an existing file; no
round link left in it; the link guard green; `docs/audits/README.md`
holds every round link the old page held (a set comparison pasted).

## Outcome
