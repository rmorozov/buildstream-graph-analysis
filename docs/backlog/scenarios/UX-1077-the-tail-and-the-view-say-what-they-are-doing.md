# UX-1077: the snapshot tail and bga view run minutes of work with no progress and no timing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R1, R5 | **Topic:** cli | **Area:** tools | **Shape:** mechanical

## Motivation

After `bst` exits only three phases draw a ticker (census, artifact
contents, `bst show`). Silent, measured at the largest size tried
([the audit](../../audits/perf-snapshot-view-2026-09-28.md)):

```text
phase                       says            5,002 el / 192k proc
Plane 2 report              one line, then   20.9s
gzip of the raw log         nothing          16.0s (417 MB)
_analyze                    nothing          35.6s
write_element_slice         nothing          18.6s
_compare                    "$ bga compare"  49.3s
bga view --export           nothing          54.9s before "Wrote"
```

## Decomposition

Input classes: a TTY, a pipe, `--no-progress`; a build that failed; an interrupted tail. Journeys: `bga snapshot` and `bga view` (serve and export).

## Required Fix

In `tools/bga_snapshot.py` and `tools/bga_view.py`: Every post-build phase of `bga snapshot`, and `bga view`'s analyze,
compare and timeline steps, announce through `bga.progress` and end
with their elapsed seconds; the snapshot's last line totals the tail
(`bga's own time after the build: N s`). Non-TTY output keeps one line
per phase.

## Out of Scope

Making any phase faster (`UX-1072`..`UX-1076`).

## Acceptance Test

`tests/unit/test_the_tail_says_what_it_is_doing.py`: With `BGA_FORCE_PROGRESS=1`, a snapshot on the golden store prints
one announcement and one elapsed line per phase, and the total line;
`--no-progress` prints the total line only. Mutation: remove one
phase's announcement, and the guard reds.
