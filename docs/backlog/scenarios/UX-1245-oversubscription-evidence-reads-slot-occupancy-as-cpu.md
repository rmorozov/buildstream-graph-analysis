# UX-1245: utilisation calls full builder slots "High CPU use", and its peak concurrency is always 1

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding H2 | **Serves:** R5 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** test_utilisation.py

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §H2).

`#utilisation` reads "Potential oversubscription: yes", "Oversubscription evidence: High CPU use", "Peak tasks at once: 1". In the same chapter `#occupancy` reads "Peak tasks at once: 4", `#capacity_verdict` "Capacity matched demand: neither over- nor undersubscribed", and Plane 2 measured 0.86 cores busy of 4.

Both are instruments reading a proxy (fixing guide §5):

- `HIGH_CPU_UTILIZATION` fires on useful *slot*-time over capacity at 95% (`bga/utilisation/__init__.py:552`) - builder occupancy, not CPU.
- `max_observed_concurrency` reads `len(interval['concurrent_tasks'])`, which `bga/analyzer.py:2164` always builds as a one-item list, so it is 1 on every run and evidence 2 can never fire.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     slot-time >= 95% becomes new evidence HIGH_SLOT_OCCUPANCY and alone no longer sets potential_oversubscription; _attach_plane2_capacity (cli.py:175) re-runs a pure oversubscription_evidence(slot_share, cores_busy, effective_cpus) and writes HIGH_CPU_UTILIZATION only when cores_busy >= 0.95 x effective CPUs. Peak concurrency becomes a start/end sweep over task intervals; analyzer.py:2164 `concurrent_tasks` deleted.
Rejected:  renaming the enum value (breaks consumers; adding is additive); passing Plane 2 into the analyzer (attached after analyze()); removing the peak field.
Files:     bga/utilisation/__init__.py; bga/analyzer.py (~2155-2175); bga/cli.py; bga/schemas.py (~5231); bga/viewer/format.js ("Builder slots full"); tests/unit/test_utilisation.py.
Guard:     test_utilisation.py: overlap gives peak 2; full slots + cores_busy 0.86/4 gives potential_oversubscription False, HIGH_SLOT_OCCUPANCY; 3.9/4 gives HIGH_CPU_UTILIZATION.
Mutation:  one-item list again (overlap reds); slot-share sets oversubscription (0.86 reds).
Class:     product
Split:     Track B, then UX-1246.
```

## Required Fix

The oversubscription evidence reads CPU where Plane 2 measured it (cores busy against effective CPUs) and says slot occupancy where it did not; peak concurrency is computed from overlapping task intervals, or the field is removed and its label with it.

## Out of Scope

The occupancy section; the capacity recommendation's wording (`UX-1246`).

## Acceptance Test

On this page oversubscription reads no (0.86 of 4 cores) and peak tasks at once 4 in both sections; a two-task overlap fixture reads 2. Mutation: restore the one-item list, and the overlap guard reds.

## Outcome (2026-10-01)

### The gap, measured

The Motivation's page (`gen-synthetic --seed 1 --layers 40 --width 60
--workload binaries`, `capture report --json` in `20260303T091500Z`),
`bga analyze --format json --plane2 plane2.json <snapshot>/run` on base
`92a48946`:

```text
utilisation: potential_oversubscription True, evidence HIGH_CPU_UTILIZATION, max_observed_concurrency 1, effective_cpus 4.0
occupancy peak_concurrency: 4    cores_busy: 0.857
```

### The close, measured

Same command, this branch:

```text
utilisation: potential_oversubscription False, evidence HIGH_SLOT_OCCUPANCY, max_observed_concurrency 4, effective_cpus 4.0
occupancy peak_concurrency: 4    cores_busy: 0.857
```

`#utilisation` reads "Potential oversubscription: no", "Builder slots
full", "Peak tasks at once: 4". Committed analyses refreshed:
`mixed_task_kinds` and `with_timeline` peak 1 -> 2, nothing else moved.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | peak read from a one-item list per task again | overlap peaks at 2, concurrency over cores, delegated + observed: 3 failed |
| M2 | full slots set `observed` | slots alone, 0.86 of 4 cores: 2 failed |
| M3 | `_reread_oversubscription` passes no cores busy | Plane 2 rewrites the evidence: 1 failed |

### Deviation from the Required Fix

Config violation with full slots and no CPU evidence reads `LOW`, not
`HIGH_SLOT_OCCUPANCY` (slots are no hint; config is). Three stale pyright
baseline entries for the deleted lines dropped by `dev_baseline.py
--shrink` (`tests/quality_baseline.json`, not in the Decision's Files).
