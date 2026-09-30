# UX-1144: one concept carries several names across the page

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H5 | **Serves:** R1, R3, R8 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_one_concept_has_one_label.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H5).

The floors read "T∞ (observed) / LB / T_C" in `#overview`, "T infinity observed / Lb / T c" in `#floors` and "T∞=..., LB=..." in a finding title. The 76.0 s gap is "Beyond the chain", "Scheduling gap" and "off the path (gap)". "Plane 2 coverage" means processes seen ("114 processes, opens 0%") in `#evidence` and element coverage ("100.0%") in the element card. Confidence renders three ways.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

styleguide §6e.2's matrix gains the floors, the gap and the two coverages, each with one reader name used everywhere.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: each concept's label set, collected from the page by its data key, has one member, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

- Reader names: the critical-path floor `T∞` (cold: `T∞ (cold)`), the resource floor `LB`, the replay makespan `T_C`, the 76.0 s `Scheduling gap`, #evidence's process count `Plane 2 processes`, the element share `Plane 2 coverage`, the headline score `Confidence`. `T∞` over `T∞ (observed)` because the finding title already says it and cold is the only other T∞.
- Files: a `TERMS` map in `bga/viewer/format.js` read by `title()` (every keyed `dt`), `views.js` (overview floors, #evidence), `decision.js` (the opportunity split); the floors drawing's part/mark labels in `bga/schemas.py`; styleguide §6e.2 gains a keyed-concept table.
- Guard: `tests/unit/test_one_concept_has_one_label.py` reads that table, boots the two-plane page plus `golden` and `macro_micro`, collects every label by its data key (`dt[data-key]`, the `dt` before `dd[data-field]`, `.wf-row[data-field]`'s label, the drawing tick's `data-mark`) and asserts one casefolded member per concept.
- Mutation: restore "Beyond the chain" in `decision.js`; the gap concept collects two names and reds.

## Outcome

The gap measured: the guard against `36cfcc7a`'s viewer and schema (`PYTEST_XDIST= python3 -m pytest tests/unit/test_one_concept_has_one_label.py -q`), label sets first letter folded:

```text
two_plane: 'the critical-path floor': ['critical path', 't infinity', 't infinity observed', 't∞ (observed)'],
  'the cold critical-path floor': ['t infinity cold'], 'the resource floor': ['lB', 'lb'],
  'the replay makespan': ['t c', 't_C'], 'wall clock beyond the critical path':
  ['beyond the chain', 'off the path', 'scheduling gap'], 'the processes Plane 2 saw': ['plane 2 coverage'], ...
golden: the same floors and gap, plus 'the headline confidence score': ['confidence', 'primary']
3 failed, 2 passed, 2 skipped in 2.89s
```

The close measured: same command, this commit - `5 passed, 2 skipped in 2.73s`; all 8 §6e.2.1 concepts found on the two-plane page. Existing guards over the renamed surfaces (sentence case, volume budget, register, drawing names, label-for-reader, two panes, planes agree, cold floor, CPU floor, 18 more files): `308 passed, 6 skipped in 85.27s`.

| mutation | reddened | count |
|---|---|---|
| `decision.js` split label back to `"Beyond the chain"` | `test_each_concept_carries_its_one_word`, all 3 pages: gap reads `['beyond the chain', 'scheduling gap']` | 3 failed, 2 passed, 2 skipped |
| `TERMS.lb` = `"Lb"` (differs from `LB` in case only) | same test, 3 pages: `the resource floor` | 3 failed, 2 passed, 2 skipped |

Merged-tree fix: Shape set to mechanical (what `dev_close_task.py --shape` derives); guard named in styleguide §6e; skip reason declared in tests/conftest.py.

Residue fix (round 154): "Peak concurrency" (`#occupancy`) and "Peak tasks at once" (`#utilisation`) were one concept with two titles; `peak_concurrency` and `max_observed_concurrency` join `TERMS`/§6e.2.1 as "Peak tasks at once", and the guard now also reds on any visible non-code text node that is a table-rejected spelling (6 failed with the title removed). Not changed: `T∞`, `LB`, `T_C` stay the decided names on rail, floors and finding title (already one label each).
