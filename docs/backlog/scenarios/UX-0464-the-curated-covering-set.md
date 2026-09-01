# UX-464: the curated covering set — T1, T2, T3 and half of T4

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-463` (which specs, and why five) · freezes under `UX-460`'s guard · closes most of `UX-459` | **Found by:** round 72 | **Serves:** the round that adds a heuristic to a reader whose fixtures cannot exercise it | **Topic:** guards

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

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done**

### The gap, measured

```text
$ python3 tools/dev_finding_coverage.py | tail -12
(a clone) 21 findings | 11 produced by a capture | 2 declared unreachable | 8 neither
  neither: blast-radius-ranking
  neither: blast-radius-structural
  neither: cache-transfer-cost
  neither: certified-headroom
  neither: criticality
  neither: execution-bound
  neither: run-mode-incremental
  neither: shared-source-blast
```

### The gap, closed

Four factories in `tests/fixtures/topologies.py`, five committed
captures under `tests/fixtures/` (T4 is a pair), written by

```bash
python3 -m tests.fixtures.topologies --write
```

which is byte-stable — the same command twice produces the same
sha256 over all five directories, so a regeneration puts no diff in
front of a round that changed nothing.

```text
$ python3 tools/dev_finding_coverage.py | tail -3
(a clone) 21 findings | 18 produced by a capture | 2 declared unreachable | 1 neither
  neither: cache-transfer-cost
```

Eleven produced → eighteen. The one left is `cache-transfer-cost`,
which `UX-463` declared uncovered for want of a remote CAS.

### Which capture produces which — measured, not designed

```text
blast-radius-ranking     one_source_many_elements, shared_base_wide
blast-radius-structural  shared_base_wide
certified-headroom       shared_base_wide
criticality              ample_capacity, one_source_many_elements, shared_base_wide
execution-bound          ample_capacity, one_source_many_elements,
                         same_build_twice_cold, same_build_twice_incremental
run-mode-incremental     same_build_twice_incremental
shared-source-blast      one_source_many_elements
```

Two corrections to `UX-463`'s covering-set table fall out of this, and
both are recorded there:

1. **`certified-headroom` is T1's, not T3's.** The table put it on
   `ample_capacity`, which was backwards: headroom is what a run that
   *queued* leaves on the table, so a fixture built to never queue is
   the one shape that cannot have any.
2. **The set is not minimal.** Only four of the seven findings have a
   single producer. `criticality` and `execution-bound` come out of
   three or four of the five captures, because any run whose elements
   do not wait on each other is execution-bound whether or not it was
   designed to be, and criticality goes fractional on any handful of
   independent same-ish tasks. The equivalence classes `UX-463`
   derived were coarser than the findings' real gates.

   The fixtures still earn their place: `UX-464`'s brief was *isolated
   cases that are easy to debug*, and a named minimal case where the
   contested critical path is the point beats an incidental one where
   it is a side effect. But "five specs for ten findings" overstated
   how tight the covering was, and this file says so rather than the
   table standing.

### Mutations applied

Each mutation was confirmed present in the file before the guard ran.

| # | Mutation | Went red | Census |
|---|---|---|---|
| M1 | `toolchain.bst`'s kind `import` → `manual` | `..._has_a_structural_base_and_a_near_tie` | 18 → **17** |
| M2b | `tie_ratio` replaced by an ordinary tail weight | `..._has_a_structural_base_and_a_near_tie` | 18 (unchanged) |
| M3 | `lanes` 2 → 6, so wall-clock *is* the critical path | `..._is_not_chain_bound` | 18 → **16** |
| M4 | `ample_capacity` gains one dependency edge | `..._declares_more_capacity_than_it_uses` | 18 (unchanged) |
| M5b | the incremental run drops an edge | `..._differs_only_in_the_skipped_count_and_the_spans` | — |
| M6b | every capture gets the inventory | `test_only_the_source_fixture_writes_an_inventory` | — |
| M7 | a nonce in `graph.json` | `..._writes_the_same_bytes_twice` | — |

M1 and M3 are the two that move the census, and they are the two that
carry `UX-464`'s actual claim: the base's kind is what splits one blast
finding into two, and the lane count is what keeps the run off the
chain-bound path where `_ranking_findings` returns nothing at all.

### Mutations of mine that did not discriminate

Two, both caught by re-running rather than by reading:

- **A first `M2` deleted the `[1.0, tie_ratio]` pair outright.** It
  reddened five clauses, including byte-stability and the inventory
  check, which have nothing to do with a near-tie: the mutated fixture
  was simply unanalysable, so everything downstream of
  `write_covering_set` fell over. A mutation that breaks the fixture
  proves nothing about the clause. Replaced by M2b, which keeps the
  fixture valid and changes only the ratio.
- **A first `M5` popped an element from the shared `els` list.** Both
  runs read that list, so both graphs changed identically and
  `cold_graph == inc_graph` still held — the clause stayed green while
  two smoke tests failed. Replaced by M5b, which changes one run only.

There is also a **process** failure worth recording. A first batch ran
M1–M3 through a shell helper and reported M3 as *green*; run again on
its own, with the mutated line printed first, M3 reddens and drops the
census by two. The batch's result was never reproduced and is not
evidence either way. What went wrong is that the helper did not prove
the mutation had landed before running the guard, which is the
`falsify` skill's own second step; every mutation in the table above
was re-run with that proof.

### Deviation from the Required Fix

The Acceptance Test predicted `17 produced | 2 neither`, with the two
being `cache-transfer-cost` and one of T5's pair. The real answer is
`18 produced | 1 neither`. Both halves of the prediction were wrong in
the same way: T5's `build-failed` and `failed-task-time` are counted
under *declared unreachable*, not *neither*, so they were never in the
"neither" column to begin with; and `certified-headroom` came from T1
rather than being missed. Eighteen is the honest number and the
sentence above the table is the corrected claim.

`write_run_dir` grew two optional arguments — `sources` for the
`sources/v1` inventory (one factory needs a fourth file) and `indent`
so the committed JSON is readable in a diff. Neither changes any
existing caller.

### Tier and suite

`tests/unit/test_topology_fixtures.py` re-measured single-process:
0.27s over 26 tests, below `MEDIUM_FLOOR_S` (1.0s), so it stays SMALL
by default and neither `tests/tiers.py` nor `tests/ci_reference.json`
moves.

```text
$ make test
5522 passed, 28 skipped, 1 warning in 299.02s (0:04:59)
$ make lint
All checks passed!
```
