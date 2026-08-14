# P4-15: Structural consolidation heuristic - `stack`-based checkout batching & element-count overhead advisory

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) - Direction 1 (structural advisory) and Direction 2 (kind-aware weighting, resolved jointly with `P4-12`) implemented; Direction 3 (documentation-only correction) already covered by `docs/ingestion-pipeline.md` | **Depends on:** `P4-12` (`element_kind` foundation, done), `P4-14` (done - real measurement confirmed per-element/pipeline overhead is material)

## Spec Reference
Not spec-mandated - `docs/specification.md` has zero matches for "stack" as an element kind, "sandbox", or "artifact checkout" (confirmed via grep). `bga`'s own added heuristic, same non-spec territory as `P4-12`/`P4-13`/`P4-14`.

## Background
Two related user observations, raised together:
1. A common post-build workflow is `bst artifact checkout`, and BuildStream's `kind: stack` element can "significantly speed everything up by initializing sandbox and accessing CAS only once" instead of once per checked-out element.
2. More granular projects (more, smaller elements) might make "different operations" slower as element count grows, and splitting a large project into subprojects, or using `stack` elements, might mitigate this.

**Observation 1 is confirmed real and precisely grounded** (BuildStream 2.7.0 source, `_stream.py::checkout()`): `bst artifact checkout <target>` calls `element._prepare_sandbox(scope=..., integrate=...)` **once** for the target, staging the target's full dependency scope (per `--deps run/build/all`) into that single sandbox, then exports the whole thing in one `_export_artifact()` call. Checking out N elements individually as N separate `bst artifact checkout` invocations means N separate `_prepare_sandbox()`/`_export_artifact()` calls - N sandbox setups/teardowns and N export operations, each walking/exporting its own tree from CAS. A `kind: stack` element depending on all N - its own docstring explicitly recommends exactly this use ("Checking out and deploying toplevel stacks") - collapses this to *one* `_prepare_sandbox()`/`_export_artifact()` call covering all N at once. `StackElement` produces no artifact content of its own (`BST_ELEMENT_HAS_ARTIFACT = False`, `get_unique_key()` returns a constant `1`) - it's purely a grouping/staging convenience. This is a genuinely real, verified mechanism, not speculation.

**Observation 2 is not confirmed**, and on the same source evidence, is likely wrong as stated for the *build* phase specifically: nothing in BuildStream's scheduler (`CacheQueryQueue`, `FetchQueue`, `BuildQueue`, etc.) treats an element differently based on which `project.conf`/junction it's declared in - every planned element is processed individually by the same queues regardless of project structure. Splitting one project into several junctioned subprojects does not, by itself, reduce the number of per-element cache-query/build/fetch operations BuildStream performs - junctions are an organizational/dependency-management tool (independent versioning, namespace isolation), not a runtime-overhead-reduction mechanism. **This distinction must be stated plainly in whatever comes out of this task**, not left as an implied endorsement of the subproject idea - the `stack`-based checkout batching (observation 1) is the part with real mechanical backing; project subdivision, for this specific claimed effect, is not.

This shares its evidence base with `P4-14`: whether *build-time* per-element overhead (cache-query, sandbox setup during `BUILD` itself) is large enough to be worth optimizing against at all is an open, unmeasured question. `P4-14`'s large-project measurement, if done, would tell us whether "more elements = slower" (the real premise behind observation 2, independent of the subproject-specific claim) is even true in a way this tool could detect, before this task tries to build advice on top of it.

## Candidate Directions
1. **Structural report signal (presentational, like `P4-12`'s Direction 1)**: given `graph.json`'s dependency structure and `element_kind`, identify clusters of leaf/co-consumed elements that are always checked out/consumed together but have no `stack` aggregator grouping them, and surface this as an advisory note (e.g. "N elements are always co-dependencies of target X with no `stack` element grouping them - consider whether a `stack` element would simplify checkout"). Zero risk to any invariant, purely additive - but the clustering heuristic itself ("always co-consumed") needs real design and a real multi-target fixture to validate against, not a single-target toy case.
2. **`element_kind == "stack"` awareness in existing signals** (ties directly into `P4-12`'s own candidate directions): a `stack` element's own recorded "build" work, if logged at all, shouldn't be weighted the same as a real compile step in blast-radius/criticality signals - `StackElement.assemble()` just creates an empty directory, so any observed duration is near-zero real work, not a meaningful compute signal. Same open question `P4-12` already raises for other structural kinds (`import`, `junction`, `filter`, `compose`) - should be resolved together with that task, not separately.
3. **Explicitly correct, not implement, the subproject-count claim**: this task's deliverable could be *purely documentation* (a note informed by the real source evidence above, e.g. in `docs/ingestion-pipeline.md`) if no real project-topology data is available to validate a genuine clustering heuristic - don't force a half-validated heuristic into the report just to have shipped something.

## Out of Scope
- Don't build any heuristic that assumes splitting a project into subprojects/junctions reduces per-element runtime overhead - that specific claim is not supported by BuildStream's own scheduler mechanics (see Background), and encoding it would actively mislead users.
- Don't let any `stack`/consolidation suggestion override or replace directly-observed timing data - same "metadata never substitutes for measurement" discipline as `P4-12`.
- Don't attempt to model `bst artifact checkout` timing at all unless a real checkout-phase log becomes part of what `bga` ingests - today's ingestion pipeline (`P4-05`/`P4-08`/`P4-09`/`P4-10`) is scoped to `bst build` logs; whether checkout logs are ever in scope is itself an open product question worth raising with the user before assuming it, not deciding unilaterally in this task.

## Acceptance Test
A real multi-element fixture with a genuine `stack`-groupable cluster: `tests/fixtures/bst_show_project/elements/all.bst` (new, `kind: stack` depending on `base.bst`/`base2.bst`) plus a real 5-leaves-and-a-stack throwaway project and a real 1500-element throwaway project (both built specifically to validate this task, not checked in - see Verification Log) demonstrate the chosen heuristics produce real, correct, verifiable output. No change to any existing invariant-bearing test's numeric result (confirmed via the golden-snapshot diff - purely an additive `consolidation_candidates: []` key for the existing fixture, which has no qualifying cluster).

## What was built
1. **Real per-element checkout data made ingestible (prerequisite)**: found and fixed two real bugs in `P4-14`'s `WrapperTraceConverter` while researching `bst source checkout`/`bst artifact checkout` real log behavior - see `docs/ingestion-pipeline.md` fact 12. Both were needed before any of this task's own work could be grounded in real data rather than assumption.
2. **`tools/bst_checkout_cost.py`** (new, deliberately standalone - not part of `bga`'s core `analyze` pipeline, since a checkout invocation shares no horizon with a build trace, I4's `Sum(attribution)==H`): `summarize`/`compare` real, measured cost from real checkout-command logs. **Real, important finding from actually measuring it** (not assumed): consolidating under a `stack` is *not* automatically a net win - it depends entirely on whether the consolidated target's own resolved closure is proportionate to what was actually needed. A real 1500-element project measurement showed checking out 5 individual elements totaled ~0s pipeline overhead (each element's own closure was trivial), while checking out the *full-project* `stack` covering all 1500 cost 6s (its closure was the whole project) - a clear net *loss* for that specific pairing. A matched-closure comparison (5 individual vs. a 5-element `stack`) showed no measurable difference at this fixture's scale. The tool reports the real `savings_us`/`savings_fraction_of_individual` for a given pair of logs rather than assuming the sign - deliberately renamed away from an earlier `pipeline_overhead_payments_avoided` framing that implied a guaranteed benefit.
3. **Structural consolidation advisory (Direction 1)**: `bga/structural/consolidation.py::find_consolidation_candidates` - purely structural (graph topology + `element_kind` only, no timing data), groups elements sharing the exact same immediate-consumer set with no existing `stack` element already covering them. Wired into `result.structural['consolidation_candidates']` and shown in `bga graph`'s "Structural Analysis" text block when non-empty, pointing at `tools/bst_checkout_cost.py` for anyone who wants a real measurement of a flagged candidate before acting on it.
4. **Direction 2 (kind-aware weighting)**: resolved jointly with `P4-12` (see that task's "What was built") - `is_structural_kind` (using the same `STRUCTURAL_ELEMENT_KINDS` set, which includes `stack`) on blast-radius/criticality/leaf-analysis signal entries.
5. **Direction 3 (subproject-count correction)**: already resolved as documentation in the previous round - `docs/ingestion-pipeline.md`'s "A note on cache-query and sandbox/checkout overhead visibility" states plainly that splitting into subprojects does not reduce per-element scheduler overhead, backed by real BuildStream scheduler-queue source reading. Nothing further needed this round beyond keeping that note accurate (updated alongside the new findings above).

## Verification Log
Real, mismatched-closure comparison (1500-element project, 5 individual leaf checkouts vs. the full-project stack) - the "negative savings" case:
```
$ python3 -m tools.bst_checkout_cost compare --individual checkout_00000.log ... checkout_00004.log --consolidated checkout_stack.log
Individual checkouts (5 invocations):
  Pipeline overhead (paid 5x): 0.000s
  Total: 0.000s

Consolidated checkout (1 invocation):
  Pipeline overhead (paid 1x): 6.000s
  Total: 6.000s

Savings: -6.000s
  Negative: the consolidated target's own resolved closure costs more pipeline overhead
  than the individual invocations paid in total - consolidating under this target is
  not a net win here.
```
Real, matched-closure comparison (same 5 elements individually vs. a 5-element `stack` covering exactly them) - no measurable difference at this scale:
```
$ python3 -m tools.bst_checkout_cost compare --individual ... --consolidated checkout_five.log --json
{"savings_us": 0, "savings_fraction_of_individual": null, ...}
```
Golden-snapshot diff (`tests/fixtures/golden/mixed_task_kinds/expected_output.json`) confirming the structural advisory is purely additive:
```
$ diff /tmp/expected_before2.json tests/fixtures/golden/mixed_task_kinds/expected_output.json
257c257,258
<         }
---
>         },
>         "consolidation_candidates": []
```
Added `tests/unit/test_bst_checkout_cost.py` (5 tests: synthetic-log arithmetic, the honest-negative-savings regression, and a real `bst`-gated end-to-end test against the extended `bst_show_project` fixture) and `tests/unit/test_stack_consolidation.py` (8 tests: candidate detection, existing-stack suppression, no-consumers exclusion, determinism, and analyzer/report wiring). Full suite: 387 passed with `bst` on `PATH` (379 passed + 8 skipped without it) - was 359/354+5 at the start of this round. `make lint` clean, `make check-clean` OK, `tests/test_e2e.py` 7/7.
