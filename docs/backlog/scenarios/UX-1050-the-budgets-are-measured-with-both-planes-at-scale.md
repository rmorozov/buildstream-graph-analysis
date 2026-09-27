# UX-1050: the volume budgets are measured on a two-plane page at scale

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1053 | **Found by:** the second styleguide audit (2026-09-27), styleguide §3e, §3f | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

`test_the_page_has_a_volume_budget.py` measures `golden`,
`macro_micro`, `scale` and `xl`. The only two-plane page is
`macro_micro` at 11 elements; `scale_run` and `xl_run` are Plane 1
alone. Measured on `main` at `814a2db8` with that file's own `_LOOK`,
1440x900, on `bga gen-synthetic <d> --store --seed 1` (`--layers 6
--width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with
`bga capture report --json <snapshot>/plane2.log --project-dir <d> >
<snapshot>/plane2.json`, exported from `<snapshot>/run`:

```text
                   landed   opened   words  controls  nodes
74, both planes     7,521   38,265  12,424       711  6,291
1,202, both planes  8,504   43,404  12,974     1,053  7,449
bound, 51-4,100     7,600   36,500   9,600       900  6,000
over                   1,202: all five; 74: opened, words, nodes
```

§3f: a bound is enforced at the largest size the tool tells people to
use, and in the mode people use it in. A capture with Plane 2 is the
mode the tool recommends, and at every size past 11 elements no guard
has met it. The synthetic store also carries history (a seventh,
store chapter), which a real store with several snapshots carries too.

## Decomposition

Input classes: Plane 1 alone and both planes at 74, 1,202 and 4,002
elements; with and without a store.

## Required Fix

`tests/pages.py` gains a two-plane page at scale (the recipe above, or
Plane 2 records generated from the run's own graph as
`scale_two_plane_snapshot` does for the timeline); the volume guard
measures it in each size class; the page is brought under the bounds
or a bound moves with its filed reason (§3e).

## Decision

`tests/pages.py` gains `two_plane_run(into, shape)`: `gen-synthetic --seed 1 --store --runs 2 <shape>`, then `capture report --json` on the newest snapshot's `plane2.log.gz`, writing `plane2.json` beside `run/` (found through `run_store.sibling_plane2`). The volume guard's `_GENERATED` gains `scale_both` (`--layers 20 --width 60`, 1,202 elements) and `xl_both` (`--layers 20 --width 200`, 4,002). The store stays in: a two-plane user has one, and history is capped by `HISTORY_POINTS_MAX`, a fixed cost.

- Rejected: `scale_two_plane_snapshot` (one program, identical processes and `maxrss`: `binary_cost` and `peak_memory` degenerate, a proxy per fixing guide §5; and no `plane2.json`, so no Plane 2 chapters); a no-store `--runs 1` label (a diagnosis, UX-1053's census); moving every bound (only part of the excess is Plane 2's fixed cost).
- Split: UX-1053 goes first. This row moves only the 4,100 class's opened height, words and DOM nodes, by Plane 2's fixed cost: 74 elements with both planes read 12,424 words against macro_micro's 13,046 at 11, so the extra is flat. Landed height (7,521→8,504 px from 74 to 1,202) and controls (711→1,053) grow with the run and do **not** move here: UX-1053 bounds them.
- Files: `tests/pages.py`; the volume guard (`_GENERATED`, `LABELS`, the new clause, the 4,100 `BUDGETS` row with its filed reason); styleguide §3e's "to 4,100 elts" row and a §3f line; the tier the session records.
- Guard: `TestEverySizeClassIsActuallyMeasured::test_every_class_is_measured_with_both_planes`: every `BUDGETS` class has a label whose run has `sibling_plane2(run) is not None`, derived from the tree, not a list of names. `TestBothBudgetsAreBound` then runs over `scale_both` and `xl_both`.
- Mutations: (a) drop both labels from `_GENERATED`: the clause reds for the 4,100 class; (b) keep them but skip `capture report`: it reds again (a name check would not); (c) the 4,100 words bound back to 9,600: `test_the_whole_page_is_bounded_too[xl_both]` reds.
- Tier: the file is LARGE at 65.0 s; paste `--durations` before and after. If the two pages add more than 30 s, drop `scale_both` (§3f wants the top of the class, `xl_both`).
- Class product; one track with UX-1053 first; parallel with UX-1049, which owns `LANDED_HEIGHT_PX`.

## Out of Scope

Plane 2's analysis; the timeline's track budget (§3g).

## Acceptance Test

The volume guard's `LABELS` include a two-plane page per size class,
green. Mutation: drop the new labels, and `TestEverySizeClassIsActuallyMeasured`
(or a new clause naming both planes) reds.

## Outcome

Not started.
