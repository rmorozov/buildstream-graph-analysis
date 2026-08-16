# UX-20: single-critical-path framing forces many small iterations on large graphs

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** none

## Motivation

Raised by the user: `bga`'s report concentrates on *one* critical path per run. On a large graph, fixing the single reported bottleneck, re-running `bga analyze`, discovering the *next* bottleneck (which may have been sitting at nearly the same criticality all along, on a different branch), and repeating, could mean many slow iterations - when several independent bottlenecks could often be identified and fixed together in one batch (a "map" over independent findings, then a "reduce" - one combined re-analysis) rather than serially.

Checked directly against the real code, not assumed: `bga` already computes more than the single critical path - `_compute_structural_analysis` (`bga/structural/analyzer.py`'s `compute_sensitivity`, Part 34) produces a real `top_opportunities` list (top 10 elements ranked by a sensitivity score, `total_improvable_time_us`, `best_case_speedup`) that's broader than just critical-path membership. But two real gaps confirmed directly:

1. **It's invisible in the text report.** `bga/report/text.py` never renders `structural.sensitivity` at all - only a comment naming the shape (`# return shape: metrics/bottleneck/parallelism/sensitivity/...`). It's only reachable via `--format json`'s `structural.sensitivity` key, and even there only as a flat list, not surfaced in the Key Findings block a user actually reads first.
2. **`top_opportunities` is a per-element proxy score, not a batch simulation.** Each entry is computed independently (`1.0 / (1.0 + slack_seconds)` for critical-path elements, a smaller proxy for others) - there is no code path anywhere in `bga/replay/scheduler.py` (`replay`/`capacity_sweep`, the only two "what-if" simulations that exist) that reduces *multiple* task durations simultaneously and reports the resulting makespan. A user has no way to ask "if I fix these 5 independent bottlenecks together, what's the predicted new critical path/wall-clock time" - only "what's the single current critical path" and "what if capacity changes."

## Required Fix

Two tiers, matching this session's own "cheap win first, harder design work separately" discipline:

1. **Minimum**: surface the already-computed `sensitivity.top_opportunities`/`total_improvable_time_us`/`best_case_speedup` in the text report's Key Findings block (or its own section), instead of leaving it JSON-only and effectively undiscoverable.
2. **Real map-reduce capability** (the harder, more valuable part): a new analysis that partitions near-critical/high-sensitivity elements into independent groups - elements with no ancestor/descendant relationship to each other, so fixing them doesn't require sequencing the work - versus elements that are serialized with each other (fixing one doesn't help until the other is also fixed, since they're on the same chain). For each independent group, simulate the *combined* effect of fixing every element in that group at once (extend `ReplayScheduler` or add a new sibling analysis that accepts a set of `{task_key: reduced_duration_us}` overrides, not just a capacity override) and report the resulting predicted makespan/critical-path change per batch - the "map" (find independent groups) plus "reduce" (predicted combined effect) framing this task is named for.

## Out of Scope

- Automatically deciding *which* elements are "worth" batching (a threshold/heuristic question) - report the independent-group structure and let the user choose which groups to act on.
- Any change to how sensitivity itself is scored (its own existing formula) - this is about grouping/batching and simulating combined effect, not re-deriving per-element scores.

## Housekeeping note found while scoping this task

`bga/structural/analyzer.py::compute_sensitivity`'s own docstring cites "Part 34" of the specification. Checked directly: `docs/specification.md` Part 34 is "Core Invariants" (I1-I13) - unrelated to sensitivity/optimization-opportunity ranking. Grepping the whole spec for "sensitivity" finds exactly one match (Part 20's wall-clock-share, a real but different, already-implemented mechanism). `compute_sensitivity`/`SensitivityResult` is therefore not actually a precisely spec-defined M6 mechanism - it's a `bga`-specific additive heuristic (same category as `element_kind`, `P4-12`'s own precedent), just mislabeled with a stale/wrong citation. Worth fixing the docstring (a one-line change) while this task is touching the same function - not itself a reason to delay or block this task, and confirms `UX-20` has real design freedom here without contradicting a real spec invariant.

## Acceptance Test

1. The text report shows the top sensitivity opportunities (not just JSON-only).
2. Given a real fixture with two independent near-critical branches (no shared ancestor/descendant relationship), the new analysis correctly groups them as independently-fixable and reports a predicted combined makespan for fixing both at once, distinct from either one alone.
3. Given a fixture where two near-critical elements *are* on the same chain, they are correctly reported as serialized (not independently batchable).
4. Full suite green.

## Fix Implemented

**Housekeeping first**: fixed the stale "Part 34" citation on `SensitivityResult`/`compute_sensitivity` (`bga/structural/models.py`, `bga/structural/analyzer.py`) - now documents plainly that this is a `bga`-specific additive heuristic (same category as `element_kind`, `P4-12`'s own precedent), not a spec-defined mechanism.

**Tier 1 (minimum)**: `bga/report/text.py`'s "Structural Analysis" section now renders `sensitivity.top_opportunities`/`best_case_speedup`/`total_improvable_time_us` as a "Top Improvement Opportunities" block - previously reachable only via `--format json`.

**Tier 2 (map-reduce)**: new `bga/structural/batching.py` module:
- `_partition_into_independent_groups`: a greedy antichain partition over candidate elements (using `bga/graph/edg.py`'s existing `compute_reachability` - no new reachability logic duplicated) - each candidate joins the first group it has no ancestor/descendant relationship with every current member of, else starts a new group. Also records every genuinely serialized pair among the candidates (informational, so a reader can see *why* two elements weren't grouped).
- `compute_batch_opportunities`: for each group with >=2 real, resolvable tasks, simulates the *combined* effect of eliminating every member's duration at once via `ReplayScheduler`'s new `duration_overrides` param (added to `bga/replay/scheduler.py`'s `replay()`/`_compute_priority()` - `{task_key: duration_us}` overrides, used by both the scheduling-order priority and the actual finish-time math), and separately simulates each member fixed *alone* for comparison - "fixing" defined as eliminating duration entirely, the same "if all slack/improvable time were eliminated" framing `best_case_speedup` already uses.
- Wired into `bga/analyzer.py::_compute_structural_analysis` as a new `batch_opportunities` key (candidates = sensitivity's own top-5 `top_opportunities`, reusing the already-constructed `self.replay_scheduler`) and surfaced in both `--format json` (`structural.batch_opportunities.{groups,serialized_pairs}`) and the text report ("Batch Opportunities"/"Serialized" lines).

## Verification Log

Done for real, 2026-08-16. New `tests/unit/test_batch_opportunities.py` (4 tests) drives `bga/structural/batching.py` directly on small hand-built fixtures (same pattern `tests/unit/test_replay.py` already uses): two independent branches are grouped and the combined simulation shows a real, distinct improvement (5200us -> 200us) neither branch achieves alone (Acceptance Test #2); a real dependency chain (`a.bst -> b.bst`) is correctly reported as a serialized pair, never grouped (Acceptance Test #3); a lone candidate produces no groups; three mutually-independent elements form one group. New `tests/unit/test_report_sensitivity.py` additions (5 tests total in that file) cover the text-report surfacing for both tiers (Acceptance Test #1) plus JSON shape stability.

`tests/fixtures/golden/mixed_task_kinds/expected_output.json` regenerated per its own documented procedure - diffed to confirm the *only* change was the new `batch_opportunities` key with real, non-empty `groups`/`serialized_pairs` data for that fixture.

Full suite green: 547 passed (up from 538 - 9 new tests), same 7 pre-existing environment-only failures as `main`. `make lint` clean.

Real CLI re-verification against `tests/fixtures/golden/mixed_task_kinds` (`bga analyze ... --format text`):

```
Structural Analysis:
  ...
  Top Improvement Opportunities (best-case speedup 1.12x if all 0.00s of improvable time were eliminated):
    - app.bst: sensitivity 1.00 (99.9% impact)
    - lib.bst: sensitivity 1.00 (99.8% impact)
    - base.bst: sensitivity 1.00 (99.7% impact)
    - extra.bst: sensitivity 0.10 (10.0% impact)
  Batch Opportunities (independent elements, simulated combined effect):
    - app.bst, extra.bst: fixing all together -> makespan 0.01s -> 0.01s (saves 0.00s combined, vs. app.bst=0.00s, extra.bst=0.00s fixed alone)
  Serialized (same dependency chain, not independently batchable): app.bst -> lib.bst; app.bst -> base.bst; lib.bst -> base.bst
```

Confirms all three acceptance-test behaviors on a real analyzed run: top opportunities visible in text (was JSON-only before), `app.bst`/`extra.bst` (no ancestor/descendant relationship in this fixture's graph) grouped and combined-simulated, and `app.bst`/`lib.bst`/`base.bst` (a real dependency chain in this fixture) correctly reported as serialized pairs rather than batched together.
