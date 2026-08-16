# UX-22: per-element `max-jobs` variance and "large serialization point" detection

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-12`

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

## Verification Log
_(append real command + output here once run, before marking 🟢)_
