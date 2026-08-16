# UX-20: single-critical-path framing forces many small iterations on large graphs

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** none

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
- Any change to how sensitivity itself is scored (Part 34's own formula) - this is about grouping/batching and simulating combined effect, not re-deriving per-element scores.

## Acceptance Test

1. The text report shows the top sensitivity opportunities (not just JSON-only).
2. Given a real fixture with two independent near-critical branches (no shared ancestor/descendant relationship), the new analysis correctly groups them as independently-fixable and reports a predicted combined makespan for fixing both at once, distinct from either one alone.
3. Given a fixture where two near-critical elements *are* on the same chain, they are correctly reported as serialized (not independently batchable).
4. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
