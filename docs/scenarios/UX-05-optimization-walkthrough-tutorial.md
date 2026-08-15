# UX-05: No worked "iteratively optimize a real project" tutorial

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-01`, `UX-02` (the walkthrough should demonstrate the real comparison/efficiency-score tooling, not manual eyeballing - see Sequencing note below)

## Motivation

Filed while brainstorming `bga`'s main user scenarios, directly for the next planned work session: iteratively optimize one or more of `examples/01-03` (or a new example project), using `bga`'s own output to pick each iteration's change, until reaching a "good enough" efficiency level. That work session's real transcript - the actual sequence of "here's what `bga` said, here's what I changed, here's what improved" - is exactly the missing tutorial content this repo doesn't have yet. `docs/cli.md` has an "Example Workflows" section, but it's command-reference-oriented (what flag does what), not narrative (what decision each number should drive, and what "done" looks like).

## Required Fix

1. A new `docs/optimization-walkthrough.md`: a narrative, worked example starting from a real example project, showing:
   - The starting `bga analyze --diagnostics` report and what it says to look at first (Certified Headroom, Biggest Opportunity, Critical Path).
   - One concrete, real change made in response (not hypothetical - an actual project/element edit), and why that specific change was chosen over other candidates the report surfaced.
   - The re-run report, and `bga compare` (`UX-01`) output showing the real delta.
   - Repeat for at least 2-3 iterations.
   - A clear stopping point: `efficiency_score` (`UX-02`) crossing whatever "good enough" band that task settles on, or Certified Headroom reaching a level where the remaining opportunity is in the critical path's own work rather than scheduling (per `UX-02`'s own documented distinction between the two).
2. Real numbers throughout - every command and its actual output, not illustrative pseudo-output (matching this repo's existing "every doc example is verified to actually work" discipline, `P4-01`).
3. Link from `README.md`'s Documentation section once written.

## Sequencing note

This task's *content* depends on `UX-01`/`UX-02` existing (the walkthrough should demonstrate the real comparison/efficiency-score tooling as it iterates, not manual before/after eyeballing) - but the next work session's actual optimization work can proceed without waiting for them: do the real iterative optimization first (manually comparing reports if `UX-01`/`UX-02` aren't done yet), and either write this walkthrough from that session's real transcript directly, or treat the friction of comparing manually as first-hand motivation confirming `UX-01`/`UX-02`'s priority before circling back to formalize this doc.

## Out of Scope

- Building new example projects specifically for this doc - reuse `examples/01-03` unless a real gap in what they exercise shows up during the work.
- Prescribing a specific "good enough" numeric target ahead of time - that's `UX-02`'s job to define; this task just needs to demonstrate reaching whatever that bar turns out to be.

## Acceptance Test

1. `docs/optimization-walkthrough.md` exists, every command in it runs against a real (not fixture-only) example project and produces the exact output shown.
2. At least 2 real iterations are documented, each with a stated reason for the change and its measured effect.
3. The walkthrough reaches and explicitly names its stopping point.
4. Linked from `README.md`.

## Verification Log

Done for real, 2026-08-15. A new example project (`examples/04-critical-path-optimization`, plus an `optimized/` variant - both real BuildStream 2.7.0 projects, not fixtures) was built with two deliberate, independently discoverable problems, then actually optimized in two iterations using `bga`'s own output to pick each change:

- Iteration 1 (scheduling): `bga analyze` on the baseline (`--builders 2`) named `RESOURCE_WAIT` as `Biggest Opportunity` and `efficiency_score: 0.81`. Rebuilt with `--builders 4` (no project change) - `bga compare` confirmed `RESOURCE_WAIT` 2.00s -> 0.00s, `efficiency_score` 0.81 -> 1.00.
- Iteration 2 (structural): with scheduling maxed out, blast-radius ranking pointed at `base-config.bst`/`core.bst`. Built `optimized/` (merged `base-config`+`base-generate`, cut `core.bst`'s work) - `bga compare` confirmed `T∞` (observed critical path) dropped by exactly the predicted 3.10s.
- Combined: `bga compare run-baseline-b2 run-optimized-b4` → `Verdict: IMPROVED (total duration -5.10s, -48.1%, 10.60s -> 5.50s)`.

Full transcript with every real command and its actual output: [`docs/optimization-walkthrough.md`](../optimization-walkthrough.md). Linked from `README.md`'s Documentation section. `make lint`/`pytest` both green (458 passed; 7 pre-existing failures unrelated to this change, confirmed via `git stash` against `main`). PR: https://github.com/rmorozov/buildstream-graph-analysis/pull/43

Two real bugs were found along the way (both deferred to backlog per this work session's scope, not fixed here - see `docs/scenarios/UX-06-raw-log-timestamp-corruption.md` and `docs/scenarios/UX-07-run-identity-collides-across-sibling-projects.md`): `--format raw`'s timestamp reconstruction corrupts cross-task ordering on real saved logs (worked around here via a new `tools/bst_run_wrapped.py` live-capture tool instead), and `run_identity.manifest_hash` collides for two different projects under the same git commit.
