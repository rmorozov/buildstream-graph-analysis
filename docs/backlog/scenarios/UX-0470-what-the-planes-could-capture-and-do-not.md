# UX-470: nothing compares a plane's capability with the records it writes

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** none; `UX-466` named the gap and declined to guess at it | **Found by:** round 72, closing `UX-466` stage 3 | **Serves:** the round that wants a signal the hook could already have produced and has no way to know it | **Topic:** capture

## Motivation

`UX-466` asked three questions and answered two. Its stage 3 was
written as *"what the planes could capture and do not"*; what the
census could honestly answer was *"what the planes do capture and the
trace drops"*. Those are different, and the difference was declared
rather than folded in:

> The other half needs a comparison between the hook's *capability* -
> the syscalls it interposes, the `rusage` fields it reads - and the
> records it writes, which is a third instrument over `tools/` rather
> than over emitted artifacts.

`UX-379` is the precedent for the gap being real: the hook was already
reading `rusage` fields it did not record, and a round had to notice by
reading the source. That is the sighting this item would make
mechanical.

## Required Fix

An instrument that reads, per plane, what the code *can* observe and
what its record schema *carries*, and reports the difference.

Unlike `UX-466`'s census this one necessarily reads source — the
capability is not in any emitted artifact — so it is a **text scan**,
which fixing guide §5 is about. That has to be handled rather than
ignored: the scan reads the interposed symbol list and the record
struct, both of which are declarations rather than prose, and every
answer it gives must be checkable against a real capture before it is
believed. A finding it reports and a capture cannot confirm is a
finding about the scan.

That difficulty is why this is filed at Low and separately, rather
than done inside `UX-466`.

## Out of Scope

- Adding any field to any plane — this measures, and what it finds
  gets filed.
- Fields the capture already holds and the trace drops: `UX-469`.
- Plane 1, whose capability is BuildStream's log format rather than
  this repository's code, and which `UX-110` already measured for
  read-lag.

## Acceptance Test

The instrument's output over both Plane 2 and Plane 3, pasted, with
every reported gap either filed as a row or confirmed against a real
capture — and, per the Required Fix, at least one confirmed the hard
way before any of it is quoted elsewhere.
