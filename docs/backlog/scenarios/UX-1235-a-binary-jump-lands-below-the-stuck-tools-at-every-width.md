# UX-1235: a binary jump lands below the stuck tools, at every width, with the rail open

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-161 verification of UX-1225 and UX-1220 (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

UX-1225 replaced `test_jump_finds_what_the_rail_lists.py`'s `margin > section for TR` (UX-1177's stuck-tools check) with `hash == "#by_binary"`, a proxy for the section, not for tools against row. Probed at 1440 on the heavy-binary page: tools 0-38 sticky, one row at top 60, margin 60. A binary jump at 390 with the rail open pushed one entry and Back returned to y 6000, but only a deleted probe read it; UX-1220's guard jumps to an element. UX-1220's Forward clause cannot fail on a jump (hashchange relands the card).

## Decomposition

Input classes: the binaries-workload 1,202-element page, mounted and unmounted binaries, at 1440 and 390, rail open and shut.

## Required Fix

The landing probe asserts the stuck tools' bottom is at or above the row's top and the filtered tbody shows one row; a binary jump at 390 with the rail open is guarded for one push and Back to the place read.

## Out of Scope

The jump's route (UX-1225); the element jump (UX-1220).

## Acceptance Test

Mutations: a sticky toolbar taller than the section margin reds the landing; `go` pushing without `navigate` for a binary reds the 390 case.
