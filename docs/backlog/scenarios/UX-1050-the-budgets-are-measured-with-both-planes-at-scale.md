# UX-1050: the volume budgets are measured on a two-plane page at scale

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3e, §3f | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

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

## Out of Scope

Plane 2's analysis; the timeline's track budget (§3g).

## Acceptance Test

The volume guard's `LABELS` include a two-plane page per size class,
green. Mutation: drop the new labels, and `TestEverySizeClassIsActuallyMeasured`
(or a new clause naming both planes) reds.

## Outcome

Not started.
