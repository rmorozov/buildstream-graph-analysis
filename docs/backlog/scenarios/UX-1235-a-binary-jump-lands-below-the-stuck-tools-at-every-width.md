# UX-1235: a binary jump lands below the stuck tools, at every width, with the rail open

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-161 verification of UX-1225 and UX-1220 (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

UX-1225 replaced `test_jump_finds_what_the_rail_lists.py`'s `margin > section for TR` (UX-1177's stuck-tools check) with `hash == "#by_binary"`, a proxy for the section, not for tools against row. Probed at 1440 on the heavy-binary page: tools 0-38 sticky, one row at top 60, margin 60. A binary jump at 390 with the rail open pushed one entry and Back returned to y 6000, but only a deleted probe read it; UX-1220's guard jumps to an element. UX-1220's Forward clause cannot fail on a jump (hashchange relands the card).

## Decomposition

Input classes: the binaries-workload 1,202-element page, mounted and unmounted binaries, at 1440 and 390, rail open and shut.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     _LAND reads the sticky tools' bottom and the count of filtered tbody rows shown, at 1440 and 390 with the rail open; the 390 Back test gains a "binary" mode.
Rejected:  hash == "#by_binary" (UX-1225's proxy); a new page fixture (the big fixture on --workload binaries keeps layer12/mod030; one page serves all three modes).
Files:     tests/unit/test_jump_finds_what_the_rail_lists.py, tests/unit/test_the_narrow_rail_jump_box_keeps_the_place_read.py
Guard:     test_a_jump_lands_on_its_target: tools bottom <= row top and 1 row shown; test_the_narrow_rail_jump_box_keeps_the_place_read[binary]: history.length +1, Back returns to 6000.
Mutation:  .table-tools { padding-bottom: 80px } reds the landing; a binary go pushing without navigate reds [binary].
Class:     product
Split:     one track.
```

## Required Fix

The landing probe asserts the stuck tools' bottom is at or above the row's top and the filtered tbody shows one row; a binary jump at 390 with the rail open is guarded for one push and Back to the place read.

## Out of Scope

The jump's route (UX-1225); the element jump (UX-1220).

## Acceptance Test

Mutations: a sticky toolbar taller than the section margin reds the landing; `go` pushing without `navigate` for a binary reds the 390 case.
