# UX-34: `Top Improvement Opportunities` ranks `stack`/`import` elements at sensitivity 1.00, above every element that does real work

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-20 (done - this is a ranking/filtering fix to the list it added), P4-12 (`STRUCTURAL_ELEMENT_KINDS`), UX-25 (the same tagging, already applied elsewhere)

## Motivation

Real run, `examples/06-macro-micro-optimization` baseline:

```
  Top Improvement Opportunities (best-case speedup 1.05x if all 2.00s of improvable time were eliminated):
    - toolchain.bst: sensitivity 1.00 (100.0% impact)
    - all.bst: sensitivity 1.00 (100.0% impact)
    - lib-a.bst: sensitivity 0.40 (40.0% impact)
    - lib-b.bst: sensitivity 0.40 (40.0% impact)
    - lib-c.bst: sensitivity 0.40 (40.0% impact)
```

and on `examples/05-cmake-cpp-toolchain`:

```
    - all.bst: sensitivity 1.00 (100.0% impact)
    - toolchain.bst: sensitivity 1.00 (100.0% impact)
    - app.bst: sensitivity 0.82 (81.6% impact)
```

The two elements the tool ranks first, on both projects, are a `stack` (`all.bst` - pure grouping, no build commands) and an `import` (`toolchain.bst` - file staging, `total=0.00s` in the same report's own by-kind table). Neither has any work to remove. "Optimize `all.bst`" is not an action.

The tool already knows this. The same report's Key Findings block tags them:

```
    1. toolchain.bst (10 downstream elements) [structural: import, may not reflect real compute work]
    1. all.bst (100% probability of being on critical path) [structural: stack, may not reflect real compute work]
```

`STRUCTURAL_ELEMENT_KINDS` exists (P4-12) and `UX-25` already applies exactly this tagging to coverage violations. The `UX-20` sensitivity list was added later and never picked it up. The result is that the one list explicitly titled *what to fix first* is the one list that does not filter.

The same noise reaches the adjacent line:

```
  Serialized (same dependency chain, not independently batchable): toolchain.bst -> all.bst; toolchain.bst -> lib-a.bst; all.bst -> lib-a.bst
```

Every pair here is anchored on a structural element. The genuinely interesting serialized pairs on this run - the `lib-a → lib-b → ... → lib-f` chain - are crowded out.

## Required Fix

1. Apply the existing `STRUCTURAL_ELEMENT_KINDS` treatment to `sensitivity.top_opportunities` and to the `serialized_pairs` line: either drop structural elements from the ranked text list, or keep them and tag them exactly as Key Findings already does. Dropping is probably right for a list titled *improvement opportunities* - a `stack` element has nothing to improve - but keep them in the JSON either way, per this repo's "no silent gaps" discipline.
2. When a structural element is dropped, the ranked list should surface the next real candidate rather than shortening, so the user still gets five actionable names.
3. Check the same filter against blast-radius ranking. There, `toolchain.bst (10 downstream)` is *correct and useful* - an `import` element's staging cost is real and its blast radius is real - so it should keep its tag rather than be dropped. The two lists want different treatment and that difference should be deliberate.

## Out of Scope

- Changing how sensitivity is computed. A structural element on the critical path genuinely does have sensitivity 1.00 by the metric's own definition; the problem is that it is presented as an action.
- `UX-33` (path/choke-point names being withheld), which is the adjacent but separate rendering gap in the same report section.

## Acceptance Test

1. `examples/06-macro-micro-optimization`'s top-5 opportunity list contains five elements that have real build commands, or tags the structural ones inline.
2. `examples/05-cmake-cpp-toolchain` likewise no longer leads with `all.bst`/`toolchain.bst` untagged.
3. Blast-radius ranking still shows `toolchain.bst`, tagged. Full suite green.

## Verification Log

Filed 2026-08-16. Both report excerpts are pasted from real `bga analyze -d` runs against real `bst --builders 4 --max-jobs 4 build all.bst` captures (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host) of `examples/06-macro-micro-optimization` and `examples/05-cmake-cpp-toolchain` respectively. The existence of `STRUCTURAL_ELEMENT_KINDS` and its use by `UX-25` was confirmed in the source, not assumed from the report text.
