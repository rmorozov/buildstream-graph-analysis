# P4-12: Explore element-kind-based heuristics for analysis

**Priority:** P4 | **Status:** 🔴 Not Started (research/design task, not a bug fix) | **Depends on:** none (the `element_kind` field it would consume already exists, filed alongside `P4-08`'s follow-on work)

## Spec Reference
None directly - this is explicitly *not* spec-mandated (Part 32.2's graph/v9 schema has no `element_kind` field at all). Any heuristic built here must stay clearly labeled as bga's own added signal, not a spec requirement, per Part 43's terminology discipline ("do not claim optimality/certification for anything beyond what's actually proven").

## Background
While extracting `graph.json` from real BuildStream projects (`tools/bst_show_to_graph.py`, `P4-08`), confirmed `bst show --format` exposes `%{kind}` (Since: BuildStream 2.6) - the element's own plugin type (e.g. `import`, `manual`, `autotools`, `cmake`, `junction`, `filter`, `stack`, `compose`). This is now captured as `element_kind` on every `Element` (`bga/ingest/models.py`), populated by `bst_show_to_graph.py`, and loaded by `bga/ingest/loader.py::load_graph` - but **nothing in `bga/`'s analysis reads it**. It's inert metadata today.

The user's observation (raised while reviewing `P4-08`'s output): an element's kind is a real, structural signal that could inform several existing analysis questions beyond what pure timing/dependency data alone can say:
- A `junction` element does no build work of its own (it's a reference to another project) - its own "build" task, if one is even recorded, is not comparable to a real compile/link step.
- `import`/`filter`/`compose`/`stack` elements are typically thin structural/aggregation elements (no real compilation), often fast and rarely the actual bottleneck - a heuristic could weight or annotate them differently in bottleneck/criticality signals.
- `autotools`/`cmake`/`make`/`manual`-family elements are where genuine compute-heavy work usually happens - a "where is the real work" summary could lean on this.

## Why this is filed as research/design, not a direct implementation task
Unlike `P4-11` (`dependency_type`'s effect on ready-time gating), which has a single, spec-adjacent, well-defined fix (stop over-constraining on `runtime`-only edges), "what should an element's kind imply about analysis" has no single correct answer and several plausible directions, each with real tradeoffs:
- Should kind ever affect a *causal* invariant-bearing computation (ready time, critical path, LB) - or should it stay purely presentational/annotative (report-only signals, e.g. "N of the top-10 blast-radius elements are junctions - consider whether cross-project dependency structuring itself is a factor")? The former risks quietly encoding an assumption ("junctions never really block anything") that might not hold for every real project (a junction *could* still gate real work if it fails to resolve, for instance).
- BuildStream's plugin kind set is open-ended (custom/third-party plugins exist) - any heuristic needs a real fallback for unrecognized kinds, not a hardcoded closed list that silently misclassifies.
- This needs real project data with kind diversity to validate against (a `bst_show_project`-style single-kind fixture won't exercise it) - `P4-10`'s pipeline now makes that possible for the first time.

## Candidate Directions (to evaluate, not commit to yet)
1. **Presentational grouping only**: report sections (blast radius, criticality, leaf/deferrability) annotate each listed element with its `element_kind`, letting a human reader spot patterns (e.g. "every high-criticality element is `autotools`") - zero risk to any invariant, purely additive.
2. **Structural/junction-aware leaf analysis (Part 24)**: a `junction` element's own "work" (if recorded at all) might not belong in deferrability scoring the same way a real compiled element's does - needs real data to check whether this is a genuine gap or a non-issue.
3. **A `bga graph --by-kind` or similar summary view**: aggregate stats (total observed duration, count, average duration) grouped by `element_kind` - a genuinely new, additive report view rather than changing any existing computation.

## Related tasks
`P4-15` (structural consolidation heuristic - `stack`/checkout batching, element-count overhead advisory) shares this task's `element_kind` foundation and its Candidate Direction 2 overlaps directly with this task's Candidate Direction 2 (`junction`-aware leaf analysis extended to `stack`-aware weighting) - resolve both together rather than picking directions independently. `P4-14` (cache-query overhead visibility) is a separate, non-`element_kind` axis (BuildStream's own cache-check cost, not plugin-kind semantics) but its large-project measurement, if done, informs whether `P4-15`'s "more elements = slower" premise is even real.

## Out of Scope (for whichever direction is chosen)
- Don't let any kind-based heuristic silently override or replace a directly-observed timing/dependency fact - `element_kind` is metadata *about* an element, never a substitute for what was actually measured (same "no silent correction" philosophy the rest of this codebase follows).
- Don't hardcode assumptions about specific third-party/custom plugin kind strings beyond BuildStream's own built-in kinds - handle unrecognized kinds as an explicit `"unknown"`/`OTHER`-style bucket, not silently.

## Acceptance Test
Not yet defined - depends on which candidate direction (or another) is chosen. At minimum: a real, kind-diverse fixture (e.g. extend `tests/fixtures/bst_show_project/` with an `autotools` or `manual` element, or build a new one) demonstrating the chosen heuristic produces a real, verifiable difference in output, with no change to any existing invariant-bearing test's numeric result unless that's the explicit, documented point of the change.

## Verification Log
_(append real command + output here once run, before marking 🟢 - or record the design decision reached and its rationale if this is resolved as "presentational only, implemented as X")_
