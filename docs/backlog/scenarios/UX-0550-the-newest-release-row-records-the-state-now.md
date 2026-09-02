# UX-550: the newest release row records the state *now*, not the one it shipped

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-252 (the generated release body) | **Serves:** anyone answering "what changed between the bga I installed and the one I have" | **Topic:** contracts

## Motivation

Architecture review 12. `CHANGELOG.md` opens with *"What changed
between the `bga` you installed and the one you have now"* and *"A
release here records a **contract state** … as they stood"*. It cannot
answer either, because the newest row is edited rather than succeeded:

```text
release 0.3.0   dated 2026-08-27, marker 332 closed rows
  block first written 2026-08-28 (bc15935):  18 contracts, 31 commands
  block today:                               23 contracts, 32 commands
  retro-fitted into it:  analyze/v5  bundle-manifest/v1  capture-layout/v1
                         host-samples/v1  plane2/v3  +  the `bundle` command
closed rows today                            537   (0.3.0's marker: 332)
```

None of those five contracts and no `bga bundle` existed on 2026-08-27.
`analyze/v4 → v5` is a **breaking** move (three keys removed, `UX-535`)
and it now sits inside a row whose `kind` cell was decided for a
different reason, 205 closed rows earlier.

**The mechanism that produces it.**
`test_a_release_records_a_contract_state.py::test_the_recorded_state_is
_the_real_one_for_the_newest_release` asserts the newest row's set
equals `contracts.ids()` *today*. That clause is satisfiable two ways —
cut a release, or rewrite the last one — and for five rounds the second
has been the cheaper. `git log -L 101,103:CHANGELOG.md` shows four
commits doing it (`f495e12`, `929ee8d`, `fab3307`, `3c93633`), none of
them a release.

This is the round's own recurring shape one layer up: a guard another
path already satisfies.

## Required Fix

Decide which, and make the guard hold only that one:

- **Cut 0.4.0** at the current state, leaving 0.3.0's block as it was
  written — the reading the prose already assumes; or
- **say the newest row is the working state** and give it a version
  that admits it (`0.4.0-dev`), so "as they stood" is not claimed of a
  row that moves.

Either way the guard needs a second clause: an *older* release row's
recorded state must not change once written. That is the mutation the
present one cannot see.

## Out of Scope

- The release procedure itself (`docs/contributing/release-guide.md`)
  beyond the sentence this changes.
- Re-deriving 0.2.0's block: it has not been edited since it was
  written, which is the property this item wants of every row, so it is
  the example rather than the work.

## Acceptance Test

`git log -L` over the newest release's state block shows one commit;
a mutation that edits a *superseded* release's contract list reddens.
