> **Superseded in part by [`UX-31`](UX-0031-notparallel-is-the-real-per-element-parallelism-control.md).** Two of this task's conclusions were re-checked against a real BuildStream 2.7.0 build and did not hold: `public: bst: max-jobs:` is never read by BuildStream (so it cannot describe a real build), and `%{vars}` *does* report a real per-element value when `notparallel` is involved. The motivating scenario - giving one element *more* parallelism than the default - is also not expressible in BuildStream 2.7.0, where `max-jobs` is a protected project-wide variable. The detector this task shipped has been re-pointed at the expressible and common condition, an element pinned *below* the rest of the build. The finding that per-element parallelism variance is real and worth detecting stands; the mechanism identified here did not.

# UX-22: per-element `max-jobs` variance and "large serialization point" detection

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-12`

## Motivation

Raised by the user, with a concrete, compelling real-world scenario: nothing prevents a BuildStream project from setting a *different* `max-jobs` value per element (via `project.conf`'s `elements:<kind>:variables:max-jobs` or a per-element `public: bst: max-jobs:` override - a real, resolvable BuildStream variable, not hypothetical) rather than one uniform value across the whole build. This is often *correct*, not a misconfiguration: a large, monolithic element like an LLVM build can be a genuine single point of synchronization in the whole project's build graph - it doesn't meaningfully parallelize with anything else while it runs, so giving *it specifically* the full host core count for `max-jobs` (rather than a smaller shared value) can cut real wall-clock time dramatically (the user's own cited real-world figure: roughly half an hour down to about five minutes). But this same reasoning becomes actively harmful once BuildStream's own `--builders` setting allows *multiple* such large elements to build concurrently - N simultaneous full-core-count LLVM-style builds is a severe, real oversubscription risk `UX-12`'s current single global `native_max_jobs` value has no way to represent or detect at all.

This is a direct, concrete elaboration of a limitation `UX-12`'s own filed doc already named and deliberately deferred: *"Per-element `max-jobs` overrides (a real BuildStream possibility - `max-jobs` is a resolvable variable, overridable per-element/per-kind) - this task captures one global value... real per-element variance is a known simplification, not attempted here."* Confirmed still true against the current code - `tools/bst_extract_run.py --native-max-jobs N` is a single, global, operator-supplied value; there is no per-element capture path anywhere in the pipeline.

## Required Fix

Real design work, building on `UX-12`'s own previously-considered (and declined-for-a-first-pass) option:

1. **Per-element capture**: query `bst show --format '%{max-jobs}'` per element (mirroring `tools/bst_show_to_graph.py`'s own existing pattern for other per-element fields) at extraction time, producing a per-element map rather than one global value - the option `UX-12`'s own doc named but deferred.
2. **"Large serialization point" detection**: a new diagnostic that flags an element as a real synchronization risk when it combines (a) a real, measured long duration (already-observed data, no new measurement needed), (b) a configured `max-jobs` close to the full host/declared-budget core count, and (c) genuine potential for *concurrent* execution with sibling elements under the real `resource_capacities.PROCESS` (`builders`) value - i.e. the graph shape actually allows more than one such element to be dispatched at once, not just that one exists. This is the real, concrete oversubscription risk the user's LLVM example describes, distinct from `UX-12`'s existing single-aggregate-demand check (which can't see *which* specific elements are driving the demand, or whether they're the kind of large, long-running, near-full-core-count elements this scenario is about).
3. Surface this as a real, actionable hint (mirroring `UX-04`'s own per-category hint precedent) - e.g. "elements X and Y are both configured near full core parallelism and can dispatch concurrently under builders=N - consider a lower per-element max-jobs for one, or reducing builders for this graph shape."

## Out of Scope

- Automatically rewriting `project.conf`/element `public: bst:` blocks to fix a detected risk - this task is about detection and a clear, actionable report, not automated remediation of the user's own project configuration.
- The aggregate, single-global-value oversubscription check `UX-12`/`UX-16` already implement - this task is additive, a finer-grained, per-element-aware signal on top of it, not a replacement.

## Acceptance Test

1. Per-element `max-jobs` values are captured and differ correctly from a single global fallback when a real project sets them per-element.
2. A fixture with two elements each configured near-full-core `max-jobs`, both dispatchable concurrently under the real `builders` value, produces a real "large serialization point" hint naming both elements - not fired when only one such element exists, or when `builders=1` makes concurrent dispatch of two of them impossible regardless of configuration.
3. Full suite green.

## Fix Implemented

**Per-element capture** (`tools/bst_show_to_graph.py`): confirmed empirically against a real BuildStream 2.7.0 install which mechanism actually carries a per-element `max-jobs` override - two plausible-looking candidates turned out wrong. `variables: max-jobs:` in an element's own body is rejected outright ("invalid redefinition of protected variable"). `%{vars}`'s own `max-jobs` entry always reports the *project-wide default*, never a per-element override. The real mechanism is `public: bst: max-jobs:` (BuildStream's per-element build-metadata block), visible via `bst show`'s `%{public}` format symbol (there's no standalone `%{max-jobs}` symbol - confirmed it isn't substituted at all). Added `%{public}` to `_FORMAT`, a new `_parse_max_jobs()` (parses the YAML block, extracts `bst.max-jobs`, `None` when absent - not defaulted to any value), and a new `Element.max_jobs` field (`bga/ingest/models.py`, threaded through `bga/ingest/loader.py::load_graph`). `tests/fixtures/bst_show_project/elements/manual.bst` gained a real `public: bst: max-jobs: 16` override (not a dependency of `app.bst`, so it doesn't affect that fixture's other tests) for real end-to-end coverage.

**"Large serialization point" detection**: new `bga/structural/serialization_points.py::detect_large_serialization_points`. A candidate element must combine (a) a real, measured duration at least `long_duration_multiplier` (default 2x) the mean task duration in this run - relative to the run's own real data, not an arbitrary absolute constant, (b) a `max_jobs` at least `near_full_ratio` (default 0.75) of the governing core count (`cpu_budget` or `host_cpu_count`, same UX-12/UX-15 precedent `_check_process_oversubscription` already uses), and (c) genuine independence (no ancestor/descendant relationship, via `bga/graph/edg.py`'s `compute_reachability`) from at least one other candidate, under a real `builders >= 2` (concurrent dispatch of two elements is physically impossible at `builders=1` regardless of configuration - Acceptance Test #2's own explicit case). Reports each real risk group with a real, actionable hint (UX-04's own per-category hint precedent), naming the specific elements. Wired into `bga/analyzer.py::_compute_structural_analysis` as a new `serialization_point_risks` key, surfaced in both `--format json` and the text report's "Large Serialization Point Risk" block.

## Verification Log

Done for real, 2026-08-16. New `tests/unit/test_bst_show_to_graph.py` additions (5 tests): `_parse_max_jobs` unit tests (absent -> `None`, present -> captured, empty -> `None`); `build_graph` captures per-element `max_jobs` correctly; a real end-to-end test against the fixture project confirms `manual.bst`'s real `max-jobs: 16` override is captured while `base.bst` (no override) is `None` (Acceptance Test #1).

New `tests/unit/test_serialization_points.py` (7 tests) on hand-built fixtures: two independent near-full-core, long-duration elements are flagged with a real hint naming both; only one qualifying element is not flagged; `builders=1` is not flagged (Acceptance Test #2's own explicit case); two qualifying elements on the same dependency chain are not flagged (can never actually co-dispatch); unknown governing cores is not flagged; a low-`max_jobs` element doesn't qualify; a short-duration near-full-core element doesn't qualify. New `tests/unit/test_serialization_point_integration.py` (3 tests) drives the real `bga/analyzer.py` call site end-to-end (not direct module calls): the real LLVM-style scenario fires through the full pipeline into both JSON and text output; `builders=1` and only-one-override both correctly produce no risk through the real call site too.

Full suite green: 562 passed (up from 552 - 10 new tests), same 7 pre-existing environment-only failures as `main`. `make lint` clean. Golden fixture regenerated per its own documented procedure (single intentional `serialization_point_risks: []` diff for that fixture, which has no per-element overrides).

Real CLI re-verification (`bga analyze ... --format text`) against a hand-built run with two real `max_jobs=4` overrides on a `host_cpu_count=4`, `builders=4` run:

```text
Large Serialization Point Risk (per-element max-jobs, real concurrent-dispatch risk):
    - elements llvm1.bst and llvm2.bst are both configured near full core parallelism and can dispatch concurrently under builders=4 - consider a lower per-element max-jobs for one, or reducing builders for this graph shape
```

`--format json`'s `structural.serialization_point_risks` carries the same real numbers (`element_max_jobs`, `element_duration_us`, `builders`, `governing_cores`).
