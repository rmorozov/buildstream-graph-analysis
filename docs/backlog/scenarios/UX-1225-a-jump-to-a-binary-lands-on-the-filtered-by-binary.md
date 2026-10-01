# UX-1225: a jump to a binary lands on the filtered by_binary list

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_jump_to_a_binary_lands_on_it.py`

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P10 (pre-existing), binaries page: the jump box finds a binary but lands on the top of by_binary, unfiltered (25 of 601); the elements that ran it need `binary_cost` filter `binary:lognormal-308` (31 matched, the log has 31).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A jump to a binary lands on the by_binary table filtered to that binary, and the elements that ran it are one link away.

## Out of Scope

The element jump (`UX-1198`, closed).

## Acceptance Test

Jump to a binary on the binaries page: the by_binary badge reads the filtered count, not 25 of 601; a guard in a new `test_a_jump_to_a_binary_lands_on_it.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     In wireJumpBox's go() (app.js:240-244), a binary target always filters its own section to `binary:<key>`, and `row()` searches only that section. Each binary row of the by_binary table gets a filtering link `#binary_cost` with `f.binary_cost=binary:<key>` (the UX-1214 `+N more` pattern).
Rejected:  a second palette row "Elements that ran X" (no help to a reader landing by scroll or anchor); landing on binary_cost (drops the by_binary count the jump names).
Files:     bga/viewer/app.js, bga/viewer/structured.js, tests/unit/test_a_jump_to_a_binary_lands_on_it.py
Guard:     binaries workload in Chromium: jump to an unmounted binary; by_binary's badge reads "1 of 601", not "25 of 601", and the row's link filters binary_cost to that binary's count.
Mutation:  Restore root-wide `row()` / `if (target.kind === "binary" && !row())`: badge assertion red. Remove the link: second assertion red.
Class:     product
Split:     with UX-1227 (wireJumpBox).
Question:  none
```

## Outcome

The gap measured, at `e60195184` (both source edits reverted), the 1,202-element `--workload binaries` page
(`pages.two_plane_run`), Chromium 1440x900, the guard's probe: a jump to by_binary's last mounted binary and to an
unmounted one, then the unmounted row's key link (`scratchpad/<worktree>/gap1225.py`):

```text
uniform-241    (mounted)    #by_binary    by_binary "25 of 601", box ''
lognormal-003  (unmounted)  #binary_cost  by_binary "25 of 601", box ''   (binary_cost filtered instead)
```

Two causes, not one: `jumpTargets` (`nav.js`) gave every binary that `binary_cost` also holds the section
`binary_cost` (first keyed table in the page), and `go()` searched the whole root and filtered only an unmounted
row. The close measured, same probe: both land on `#by_binary`, badge "1 matched", box `binary:<key>`; the key
link reads binary_cost "23 matched", `binary:lognormal-003`. The guard at 1440 and 390: 1 passed (15.7 s).
Golden's page half 159,357 -> 159,409 B (+52). The 97 files naming jump, `nav.js`, `app.js`, by_binary or
keyed-by: 1,546 passed, 19 skipped.

| mutation | reddened | run printed |
|---|---|---|
| `go()`: root-wide `row()`, filter only `if (!row())` | the mounted jump (by_binary "25 of 601") | 1 failed |
| `sections.js`: drop `cell.replaceChildren(link)` | the link assertion (binary_cost "25 of 11,683") | 1 failed |
| `nav.js`: binary tables in page order again | both jumps (`#binary_cost`, "25 of 601") | 1 failed |
| reverted, each | | 1 passed |

The Decision's own guard - an unmounted binary only - passed under the `go()` mutation once `nav.js` named
by_binary; the mounted case (the walk's own) is what discriminates it.
