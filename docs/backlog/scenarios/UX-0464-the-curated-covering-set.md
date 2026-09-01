# UX-464: the curated covering set — T1, T2, T3 and half of T4

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-463` (which specs, and why five) · freezes under `UX-460`'s guard · closes most of `UX-459` | **Found by:** round 72 | **Serves:** the round that adds a heuristic to a reader whose fixtures cannot exercise it | **Topic:** guards

## Motivation

`UX-463`'s covering set assigns four of its five specs to curated
fixtures, because they need timings a real build cannot be asked for —
T1's requirement is *two longest paths within a few percent of each
other*, which is a property you can only write down.

The four close six of the eight uncovered findings:

| spec | closes |
|---|---|
| T1 `shared-base-wide` | `blast-radius-ranking`, `blast-radius-structural`, `criticality` |
| T2 `one-source-many-elements` | `shared-source-blast` |
| T3 `ample-capacity` | `execution-bound`, `certified-headroom` |
| T4 `the same build twice` (analysis half) | `run-mode-incremental` |

`tests/fixtures/topologies.py` already has ten factories in exactly the
shape these need — the ingested triple, `write_run_dir`,
`build_analyzer`. This is four more factories in a module that exists,
not a new mechanism.

## Required Fix

Four factories in `tests/fixtures/topologies.py`, one per spec, each
returning the same `Topology` triple every existing factory returns,
and each parametrised on the property its spec names rather than
hardcoding one timing:

- `shared_base_wide(dependents=6, tie_ratio=0.97)` — one base, N
  dependents of unequal weight, the two longest paths within
  `tie_ratio`.
- `one_source_many_elements(elements=4)` — one source id staged into N
  elements.
- `ample_capacity(elements=8, capacity=16)` — capacity above demand, so
  no task ever queues.
- `the_same_build_twice()` — a `(cold, incremental)` pair sharing one
  graph, differing in `run_context`'s run mode and in which spans are
  cache hits.

Then a **committed run directory per spec** under `tests/fixtures/`,
written by those factories, so `dev_finding_coverage.py` reads them
from a clone and the count moves. A factory alone does not close
`UX-459`: the census reads captures, not Python.

## Out of Scope

- T5 `a build that fails` — it belongs to `UX-465`'s half of the split,
  because a synthesised failure only asserts what someone already
  believed the capture path does with one (`UX-156`, `UX-148`).
- `cache-transfer-cost` — `UX-463` declared it uncovered for want of a
  remote CAS, and this item does not stand one up.
- The guard that freezes the count: `UX-460`.
- Any change to the findings themselves. If a factory cannot make a
  finding fire, that is a finding about the finding, and gets its own
  row rather than a fixture bent until it passes.

## Acceptance Test

```bash
python3 tools/dev_finding_coverage.py | tail -6
```

reports `21 findings | 17 produced by a capture | 2 declared
unreachable | 2 neither`, and the two remaining are
`cache-transfer-cost` and one of T5's pair.
