# UX-51: nothing joins Plane 1's "which elements matter" to Plane 2's "what happened inside them"

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-23 (element tagging - the join key), UX-24 (single-invocation dual capture), UX-32/UX-45/UX-46 (the Plane 2 facts worth joining), UX-44 (the Plane 1 ranking worth joining to) | **Topic:** analysis | **Area:** bga

## Motivation

`docs/design/directions.md` named this as the biggest thing the tool cannot do, and observed that it got *sharper* rather than smaller as Plane 2 improved: every capability added to Plane 2 widened the set of answers a user has to assemble by hand.

The loop a user actually runs, from that doc:

> Plane 1 ranks elements by blast radius and critical-path membership → the user picks the top one → Plane 2 explains where *that element's* time went → the fix is either a graph change (back to Plane 1) or a native-build change (stay in Plane 2).

Every step of that is supported except the arrows. `docs/audits/case-study-06-macro-micro.md` records the consequence: the walkthrough's findings came out of two JSON files and an ad-hoc script, and its closing note still said the macro and micro halves "remain two tools and two captures".

Concretely, on a real build of `examples/06`, the two planes each hold half of one sentence:

- Plane 1: *`core.bst` holds 25% of the critical path.*
- Plane 2: *`core.bst` runs at 0.85 cores busy and asked for `-j1`.*

Neither is actionable. Together they are: **the element that dominates the critical path is not compute-bound, so fix how it is built, not what it builds.**

## Required Fix

Join the planes. The design question - explicit join versus merging the planes into one pipeline - was settled by measuring three things *before* choosing, rather than by argument:

1. **Is a merged capture needed?** No. `UX-24` already runs one real `bst build` and emits both artifacts: `bst_native_build_tracer.py run --wrapped-log`. Verified again for this task - one invocation produced `/tmp/seam-plane1.log` and `/tmp/seam-plane2.json`.
2. **Does a join key exist, and is it exact?** Yes, and yes. Plane 1 is keyed by element UID; `UX-23` tags every traced process with its owning element. On the real dual capture:

   ```text
   Plane 1 elements: 11
   Plane 2 elements: 9
   exact intersection: 9
   Plane 2 only: []
   Plane 1 only (no build commands): ['all.bst', 'toolchain.bst']
   ```

   Zero mismatches. The two Plane 1 elements missing from Plane 2 are a `stack` and an `import` - elements that run no build commands, so their absence is *correct* rather than a join failure.
3. **Could the horizons be merged even in principle?** No. `docs/design/architecture.md` argues this at length: Plane 2's timeline sits one level down inside a single element's sandbox and shares no horizon with an element-level trace, so attribution cannot be reconciled across them. Anything presented as a merge would be a join wearing a misleading name.

So the contract between the planes is **one string** - the element UID - and the join is a third consumer reading two finished artifacts that neither plane knows about. Each plane stays independently replaceable, which is the point of keeping the contract thin.

## Fix Implemented

`bga correlate RUN_DIR NATIVE_REPORT.json`, backed by `bga/correlate.py`. Deliberately a separate command rather than a section of `analyze`: `analyze` must keep working with no Plane 2 artifact at all, and folding the join in would couple the pipeline to a second capture that most runs do not have.

Real output, from one `bst --builders 4 --max-jobs 4 build all.bst` of `examples/06-macro-micro-optimization` captured with `--wrapped-log --trace-opens`:

```text
Joined 9 element(s) on element UID (11 in Plane 1, 9 traced in Plane 2)

What to do next (ranked by Plane 1 impact):
  core.bst:
    - holds 25% of the critical path but runs at only 0.85 cores busy - it is waiting,
      not computing, and its native build asked for -j1: remove `notparallel` / raise
      its job count before touching its sources
    (81% of this element's processes were measured)
  lib-a.bst:
    - holds 8% of the critical path and is already compute-bound at 1.56 cores busy -
      nothing to gain from its parallelism; shortening it means less work
    - declares 2 build dependencies it never read (codegen.bst, core.bst) - removing
      the edge is free and widens the graph
```

That first entry is the whole macro→micro loop in one line, and it is the project's deliberately-planted micro defect found *by the tool* rather than by knowing the project.

Three properties the implementation is careful about:

- **The negative result is as valuable as the positive one.** "Already compute-bound - nothing to gain from its parallelism" stops a reader spending time in the micro plane on an element that has nothing to give there. It is phrased as a conclusion, not a task.
- **Plane 2 explains Plane 1's ranking; it never reorders it.** The user arrived with "what should I optimize", and the answer to that is Plane 1's. Reordering by a Plane 2 finding would silently change the question.
- **Coverage survives the join.** `UX-45`'s per-element measurement coverage is carried through and printed, so a recommendation built on 81% of an element's processes says so. Elements Plane 1 says matter but Plane 2 never traced are listed explicitly rather than passed over - silence would read as "nothing to report inside it".

**One defect found and fixed during implementation**, worth recording because it is the failure mode this kind of synthesis invites: the first version gated its recommendations on critical-path *membership*, and rendered `app.bst: holds 0% of the critical path and is genuinely compute-bound`. An element can sit on the critical path and still have no measurable ability to move the finish - that is exactly what `UX-44` established - so the gate is now the measured saving. A confident sentence about an element that cannot help is worse than no sentence.

## Out of Scope

- Merging the two horizons, per point 3 above - not deferred, but ruled out.
- Folding this into `bga analyze`. It stays a separate command so `analyze` keeps working without a Plane 2 artifact.
- Automatically running the Plane 2 tracer from `bga`. The tracer needs a real `bst`, `bwrap` and a compiler; `bga` deliberately needs none of those.

## Acceptance Test

1. A real dual capture of `examples/06-macro-micro-optimization` joins with zero key mismatches, and the elements that fail to join are exactly the ones that run no build commands.
2. `core.bst` is the top-ranked entry, and its recommendation names both its critical-path share and its measured cores-busy.
3. An element whose Plane 1 saving is zero produces no share-based claim.
4. An element Plane 1 ranks but Plane 2 never traced is named rather than silently omitted. Full suite green.

## Verification Log

Filed and implemented 2026-08-17 (round 4). All three design measurements are from a real session: BuildStream 2.7.0, real `bwrap` sandbox, 4-core host, one `bst --builders 4 --max-jobs 4 build all.bst` of `examples/06-macro-micro-optimization` captured with `run --wrapped-log --trace-opens`, its Plane 1 log then extracted with `bst_extract_run --format wrapped`. The join-key intersection was computed directly over the two resulting artifacts, not asserted from the docs that claim it. The report block above is pasted from a real `bga correlate` run against those two artifacts.

Tests: 12 new (`tests/unit/test_correlate.py`), weighted toward the ways a synthesis like this misleads - a zero-saving element making a confident claim, an untraced element passing silently, partial CPU coverage being dropped, and Plane 2 reordering Plane 1's ranking. Full suite 898 passed (up from 886), `make lint` clean.
