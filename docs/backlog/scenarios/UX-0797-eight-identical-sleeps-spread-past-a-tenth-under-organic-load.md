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

_Not started._
