# UX-797: eight identical sleeps spread past a tenth, under organic load

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-741 (the two clauses beside it, re-expressed), UX-110 | **Found by:** round 110, `UX-741`'s verifier, 20 bare runs of the file | **Serves:** the gate that reds on a host reading nothing in the diff touched | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

```console
$ for i in $(seq 20); do python3 -m pytest tests/unit/test_spine_ground_truth.py -q; done   # load 6-12 on 4 cores, no hogs
19 × "2 passed" · 1 × FAILED test_spine_ground_truth.py::test_plane2_ground_truth
E   assert max(durations) - min(durations) < 0.1
```

`tests/unit/test_spine_ground_truth.py:118` holds that eight
`sleep 3` elements measure identically to within 0.1 s. `UX-741`
re-expressed the two clauses beside it against readings contention
cannot stretch and left this one, on the task file's word that it
"held at load 16" — it held under sixteen CPU hogs and reddened once
in twenty at organic load 7–9, which is a different load: I/O and
scheduler contention stretch one sleeper's teardown and not another's.
The claim is right — a spread is what makes the eight a measurement
rather than a coincidence — and the bound is a fixed tolerance on wall
clock, the shape `UX-741` just closed one clause over.

## Required Fix

In `tests/unit/test_spine_ground_truth.py` the spread clause reads what the
contention cannot move: each sleeper's
`duration_s` is bounded below by the stated sleep and above by the
harness's enclosing span (`UX-741`'s bounds, applied per element), and
the *spread* claim becomes a claim about the distribution the spine
records — the eight CPU readings identical to within `IDLE_CPU_US`,
which no load has moved — so the identical-work property is held on a
quantity that is identical under load. If a wall-clock spread bound
stays, its tolerance is measured from a population taken under
organic load (≥ 20 runs at load ≥ 6, the numbers pasted), never typed.

## Out of Scope

- `PLANE_AGREEMENT_S`'s lag magnitude — `UX-110`.
- Skipping under load — closed by `UX-741`'s measurement.

## Acceptance Test

20 bare runs of the file at load ≥ 6 with no hogs: 20 × `2 passed`.
Mutation: one sleeper's recorded `cpu_us` raised past `IDLE_CPU_US`
— red; the eight-identical clause names the element.

## Outcome

**Route taken:** both routes, not one. The identical-work claim is
held on the eight `cpu_us` readings (`max - min < IDLE_CPU_US`, no
load moves it) **and** on wall clock, now with a tolerance measured
from a population rather than typed: `WALL_SPREAD_S = 0.13`, 2× the
observed max, rounded up. The two per-element bounds UX-741 wrote are
unchanged. Both new clauses name the outlier element.

**The population** (20 bare runs, this 4-core box, organic load
9.5-14.6, no hogs — box already loaded): `max(durations)-min(durations)`
per run, seconds:

```text
0.0146 0.0279 0.0326 0.0204 0.0094 0.0264 0.0229 0.0156 0.0222 0.0334
0.0131 0.0480 0.0140 0.0200 0.0627 0.0191 0.0157 0.0078 0.0163 0.0207
```

min 0.0078, max 0.0627, mean 0.0231, p95 0.0480. Rule: `2 × max` =
0.1254, rounded up to `WALL_SPREAD_S = 0.13`.

**Gap measured** (Motivation, round 110, old code, organic load 6-12,
no hogs, 20 bare runs): 19 × `2 passed`, 1 × `FAILED`
(`assert max(durations) - min(durations) < 0.1`).

**Close measured:** 20 bare runs, new code, organic load 6-23 (peaked
23.38), no hogs: 20 × `2 passed`, 0 failed. File green 5× bare after
the final restore (load 9.2-13.0): 5 × `2 passed`.

**Mutation table** (each: edited, run, restored from a scratch copy,
never `git checkout --`):

| mutation | expected | got |
|---|---|---|
| one sleeper's `cpu_us` set to `IDLE_CPU_US` exactly | red, naming the element | red: `work-a.bst: 30000us of CPU spreads 30000us from work-b.bst's 0us` |
| one sleeper's `duration_s` += `WALL_SPREAD_S` + 0.5 | red, naming the element | red: `work-a.bst: 3.646s spreads 0.641s from work-f.bst's 3.005s` |

**What each clause discriminates.** Per-element bounds: a sleep that
finished early, exceeded the whole build's span, or burned CPU past
`IDLE_CPU_US`. CPU spread: a sleeper burning CPU below that bound but
inconsistent with its siblings (boundary case; raising `cpu_us` past
`IDLE_CPU_US` reds the per-element bound first, not this clause — the
mutation above isolates it at the boundary). Wall spread: a sleeper
stalled in wall clock while idle on CPU and inside the per-element
bounds — the case the coordinator's HOLD named (a 5.0s stall against
3.0s siblings). **What none can catch:** a sleeper stalled inside
`WALL_SPREAD_S` (e.g. 3.10s against 3.01s siblings) — identical-ish,
not identical, and no measured tolerance can tell the two apart.

**Acceptance Test, pasted:** 20 bare runs of the file, organic load
(peaked 23.38, no hogs needed — box was not quiet): 20 × `2 passed`.
