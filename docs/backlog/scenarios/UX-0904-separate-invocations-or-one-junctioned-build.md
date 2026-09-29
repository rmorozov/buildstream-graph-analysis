# UX-904: nothing prices N separate CI builds against one junctioned invocation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-903 (the variants that make N), P4-15 / `bst_checkout_cost.py` (the precedent) | **Found by:** the 2026-09-20 rollout thread — the owner names this as one of the questions bga should answer: do the variants need separate CI builds, or are they worth embedding in one BuildStream invocation through junctions | **Serves:** R5 (the fleet that runs N of them), R3 (whose graph the junction changes), R4 and R6 (the latency of a verdict) | **Topic:** analysis | **Area:** bga | **Shape:** mechanical

**Guard:** `tests/unit/test_one_invocation_is_priced_against_n.py`

## Motivation

A pipeline that builds four variants runs four BuildStream invocations,
each paying the pipeline's own cost — loading elements, resolving them,
querying the cache — before any element builds, and each scheduling its
graph alone on its agent. One junctioned invocation pays that once and
schedules every variant's elements together, which is more parallelism
to find and a larger cache-hit surface, against a longer critical path
and a blast radius that now spans variants.

The tool has both halves of this arithmetic already and joins neither:
`pipeline_overhead` is a published per-invocation cost
(`bga/analyzer.py`, `analyze/v6`), `tools/bst_checkout_cost.py` is the
existing precedent for exactly this shape of question — N separate
invocations against one grouping element, measured rather than
speculated — and `examples/12-junctioned` is a committed project with a
real junction in it. What is missing is the answer, and the owner asks
for it directly.

## Required Fix

Price the two arrangements from captures the pipeline already produces:
given N runs of the same tree under different variants, what one
junctioned invocation would cost, and what it would win. The honest
shape is a projection with its assumptions stated, the way
`bga whatif` already is:

| term | where it comes from |
|---|---|
| pipeline cost paid N times | `pipeline_overhead`, per run |
| the union graph's floor | the N graphs joined at their shared elements, T∞ over the union |
| what is actually shared | elements identical across variants — the cache already knows |
| what the junction costs | staging the subproject, measured on `examples/12-junctioned` |

And the refusal that keeps it honest: where the N runs are not
comparable (`UX-898`, `UX-903`), say so rather than joining them.

A re-capture is still the ground truth, and the finding says so.

## Decision

```text
Route:     a new `bga/junction_cost.py` with `project(runs) -> junction-cost/v1`, shaped like `bga whatif` (document plus render, refusals are answers, exit 0); command `bga junction-cost RUN RUN [RUN...]`. Two elements in different variants are the same element only when their `cache_key` (graph/v9, `Element.cache_key`) is identical. Pipeline cost: per phase, sum over N minus max over N, assumption stated. Union floor: T∞ over the per-variant graphs merged at shared keys; the shared set is closed downward (a key covers its dependencies' keys), so the floor is computed, not assumed. Junction staging: measured on examples/12-junctioned when `bst` is on the host, else carried as an unmeasured assumption; the document says a re-capture is the ground truth. Build classes come from `bga/buildclass.py` (`same_class`, `differing_dimensions`, `homogeneous`).
Rejected:  element name plus source key (an asan and a release compile of one source would read as shared; in one junctioned invocation names carry a junction prefix, so the key is the only identity left) · a namespace in analyze/v6 (this reads N captures) · pricing it inside `compare` (pairs, not N).
Files:     bga/junction_cost.py (new), bga/cli.py (cmd_junction_cost, parser, the schema map), bga/schemas.py (JUNCTION_COST, required fields, hints), docs/spec/specification.md Part 32 only (the 32.5 list and table), docs/README.md (contract row), tests/unit/test_one_invocation_is_priced_against_n.py
Guard:     two synthetic runs of one type, different variants, known shared-key set: the document names that set, the pipeline saving, the union floor and the bound, and validates against the schema; disjoint keys give no saving and say so; different types refused through buildclass; a single run refused; runs with no cache keys refused.
Mutation:  double one run's pipeline_overhead (saving grows by exactly that); move one element out of the shared keys (shared set and saving drop); compare the variant instead of the type in the refusal (different-types pair joins).
Class:     product
```

## Decomposition

surfaces: a new analysis module beside `bga/whatif.py`, the CLI entry point, `analyze/v6`'s projection namespace or a document of its own, and `examples/12-junctioned` as the fixture with a real junction
guards: two variant runs sharing most elements (a projected saving), two sharing nothing (no saving, and it says so), runs of different types (refused), and a single run (nothing to compare)
gap: whether "the same element in two variants" is decidable from cache keys alone — different variants may key differently for the same source, which is the whole question and needs a real pair to settle
track: session's own — the arithmetic is a modelling decision, not a mechanical one
gate: after `UX-903`, whose class makes "the same tree, different variant" nameable

## Out of Scope

Restructuring anyone's pipeline; the row publishes the number, not the
migration. Junction semantics themselves, which BuildStream owns.

## Acceptance Test

On two synthetic runs of one tree under two variants with a known
overlap, the projection names the shared element set, the pipeline cost
saved, the union floor, and a bound on what one invocation would cost —
each figure carrying its assumption. On two runs with no overlap it
reports no saving. On runs of different declared types it refuses.
Mutations: double the pipeline overhead (the saving grows by exactly
that), remove an element from the overlap (the shared set and the saving
both fall), make the two runs different types (refused rather than
joined).

## Outcome

**Gap measured.** At `b8072cd7` nothing prices the pair:
`git grep -c "junction-cost\|junction_cost" b8072cd7 -- bga docs/spec docs/README.md`
prints nothing (0 files), and `bga junction-cost` is not a subcommand.

**Close measured.** `PYTHONPATH=. python3 -m pytest -q -p no:randomly tests/unit/test_one_invocation_is_priced_against_n.py`:

```text
8 passed in 0.51s
```

The synthetic pair (`night`, `arch=x86_64` against `arch=aarch64`, keys
`k-base` and `k-lib` shared) projects: shared `[k-base, k-lib]`,
shared-work saving 28s, pipeline saving 3s, saving 31s, separate floors
60s and 70s, union floor 72s, one-invocation lower bound 80s, junction
staging `null`; it validates against `junction-cost/v1`. Doubling run
`a`'s phases grows the saving by exactly 3s; moving `lib` out of the
overlap drops the set to `[k-base]` and the work saving by 18s; disjoint
keys give `shared: []`, work saving 0 and an `overlap` sentence saying
so; `review` beside `night` under one variant refuses `different_types`;
one run refuses `single_run`; an unkeyed run refuses `no_cache_keys`.
On committed fixtures,
`bga junction-cost tests/fixtures/macro_micro/run tests/fixtures/host_cpu/run`:

```text
  Shared: 11 elements shared by cache key; building each once saves 27.950s of work.
  Pipeline paid once instead of N times saves 0.676s [pipeline_once]
  Floors: separate 43.200s, 24.950s; union 43.200s [unlimited_capacity]
  One invocation costs at least 44.641s, plus junction staging (not measured) [junction_staging]
```

Junction staging is carried as an unmeasured assumption: `bst` is not on
this host, so `examples/12-junctioned` was not captured.

**Mutation table** (`bga/junction_cost.py`, reverted from a copy after each):

| mutation | reddened | run |
|---|---|---|
| pipeline phase saving `sum - max` becomes `max` | known_overlap, doubling_one_runs_pipeline | 2 failed, 6 passed |
| shared needs `> 2` runs, not `> 1` | known_overlap, element_moved_out_of_the_overlap, a_captured_run_reaches_the_projection | 3 failed, 5 passed |
| type refusal compares the variant instead of the type | different_types_are_refused and 5 more | 6 failed, 2 passed |
| single-run refusal `< 2` becomes `< 1` | a_single_run_is_refused | 1 failed, 7 passed |
| no-cache-keys refusal dropped | runs_with_no_cache_keys_are_refused | 1 failed, 7 passed |
| shared work counted in full, not `sum - max` | known_overlap, element_moved_out_of_the_overlap | 2 failed, 6 passed |
| union node takes the min duration | known_overlap | 1 failed, 7 passed |

Restored: 8 passed.
