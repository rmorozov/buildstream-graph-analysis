# UX-33: the text report hides the critical path when it is longer than 5 elements, and never names choke points at all

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** —

## Motivation

`README.md` on the critical path: *"the one chain of elements that determines total build time... this is always where to look first"*. `bga/report/text.py`:

```python
lines.append(f"Critical Path Length: {len(critical_path)} elements")
if len(critical_path) <= 5:
    lines.append(f"  Path: {' → '.join(critical_path)}")
```

The path is printed only when it is short. Real run, `examples/06-macro-micro-optimization` baseline - a project whose entire problem is a ten-element artificial chain:

```
Critical Path Length: 10 elements
```

That is the whole section. Meanwhile the same analysis, in JSON:

```json
"critical_path": ["toolchain.bst","core.bst","lib-a.bst","lib-b.bst","lib-c.bst",
                  "lib-d.bst","lib-e.bst","lib-f.bst","app.bst","all.bst"]
```

The chain is computed, is correct, is the answer, and is suppressed precisely because it is long - which is precisely when a human cannot reconstruct it from memory. The same run's short-path counterpart (`examples/05`, 5 elements) does print its path, so the user's experience is that the feature works until the project gets big enough to need it.

The identical shape appears one section down:

```
Structural Analysis:
  Elements: 11, Edges: 34, Max Depth: 9
  Bottlenecks Identified: 5
```

with, in the JSON:

```json
"choke_points": ["lib-a.bst","lib-b.bst","lib-c.bst","lib-d.bst","lib-e.bst"]
```

Five bottlenecks were found. Which five is not printed. Those five *are* the artificial chain - the single most actionable output the tool produced on this run, reduced to the integer `5`.

Both of these are the same failure as `UX-25` (coverage violations reporting a bare ratio when the explaining fact was already computed), which was fixed by naming the elements. This is that fix, applied to the two places it was not.

## Required Fix

1. Always print the critical path. For genuinely long paths, print it in a readable form rather than truncating to nothing - one element per line with its own duration and share is more useful than an arrow chain anyway, and gives the user the "which link do I attack" answer directly. If a hard cap is still wanted, print the top N by duration and say how many were elided (`UX-26`'s omitted-groups line is the house pattern).
2. Print the choke-point element names, not just their count.
3. Audit `bga/report/text.py` for the same shape elsewhere. `Bottlenecks Identified` and the critical path are the two found by inspection during this session; a count-without-names is the signature.

## Out of Scope

- Changing what `compute_critical_path` or the M6 choke-point analysis compute. Both are correct; this is a rendering fix.
- The structural-element noise in those same lists (`all.bst`, `toolchain.bst` appearing on the critical path with no real compute work) - that is `UX-34`.

## Acceptance Test

1. `bga analyze` against `examples/06-macro-micro-optimization` prints all ten critical-path elements, or a documented, explicitly-counted subset.
2. The same run names `lib-a.bst`..`lib-e.bst` as its choke points.
3. Short-path runs render at least as well as they do today. Full suite green.

## Fix Implemented

Both halves are rendering-only; nothing in the analysis changed.

**Critical path.** `bga/analyzer.py` gained `_build_critical_path_detail`, which turns the already-computed `signals['critical_path']` into a per-element list carrying each element's real measured duration, its share of the summed path durations, and its `element_kind`/`is_structural_kind` (reusing the existing `_element_kind_lookup` and `STRUCTURAL_ELEMENT_KINDS`, exactly as `UX-25` does). It is published as an additive `signals['critical_path_detail']` - the existing `critical_path`/`critical_path_length` keys are untouched, so no consumer breaks - and added to `GRAPH_SIGNAL_KEYS` so it groups with the other graph signals rather than leaking into the diagnostics section.

`bga/report/text.py` now always prints the chain. At or below `_CRITICAL_PATH_INLINE_MAX` (5, the old cutoff, now a *rendering* choice rather than a suppression threshold) it keeps the familiar one-line `a → b → c` form; above it, one element per line with duration and share of path, which is what answers "which link do I attack first". Structural elements stay on the printed chain - they are real graph structure - but are tagged `[structural: stack, no build commands to speed up]`. A result with no `critical_path_detail` (an older run directory) falls back to the arrow form at any length rather than to a bare count.

**Choke points.** `Bottlenecks Identified: N` now names them, capped at `_CHOKE_POINTS_SHOWN_MAX` (8) with an explicit `(+K more, see --format json)` overflow line rather than a silent truncation.

Tests: 7 new (`tests/unit/test_critical_path_and_choke_point_naming.py`), hermetic against `format_text` directly - long path printed rather than withheld, per-element duration and share shown, structural elements tagged, short path keeping the arrow form, the no-detail fallback, choke points named, and the overflow line. The `mixed_task_kinds` golden snapshot gained the additive `critical_path_detail` key and was regenerated deliberately; that was the only diff.

## Verification Log

Filed 2026-08-16. Implemented the same day. Text output and JSON are from one real `bga analyze` / `bga analyze -f json` pair against a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/06-macro-micro-optimization` (BuildStream 2.7.0, 4-core host). The `len(critical_path) <= 5` condition was read directly from `bga/report/text.py`.

Real end-to-end re-verification against the exact case in this doc's Motivation - a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/06-macro-micro-optimization`:

```
Critical Path Length: 10 elements
  Path (chain order, with each element's real measured duration):
    toolchain.bst                               0.00s (  0.0% of path) [structural: import, no build commands to speed up]
    core.bst                                   14.00s ( 38.6% of path)
    lib-a.bst                                   3.00s (  8.3% of path)
    lib-b.bst                                   3.00s (  8.3% of path)
    lib-c.bst                                   3.00s (  8.3% of path)
    lib-d.bst                                   3.00s (  8.3% of path)
    lib-e.bst                                   3.05s (  8.4% of path)
    lib-f.bst                                   3.00s (  8.3% of path)
    app.bst                                     4.20s ( 11.6% of path)
    all.bst                                     0.00s (  0.0% of path) [structural: stack, no build commands to speed up]

Structural Analysis:
  Elements: 11, Edges: 34, Max Depth: 9
  Bottlenecks Identified: 5 - lib-a.bst, lib-b.bst, lib-c.bst, lib-d.bst, lib-e.bst
```

Both Acceptance Test items 1 and 2 confirmed with real data: the ten-element chain is printed in full, `core.bst`'s 38.6% share names the heaviest link outright (it is the `notparallel: True` element - see `UX-31`), and the five chained libraries are named rather than counted. Item 3 confirmed against the same session's real `examples/05-cmake-cpp-toolchain` capture, whose 5-element path still renders as `Path: toolchain.bst → core.bst → lib-a.bst → app.bst → all.bst`. Full suite green (658 passed, up from 651), `make lint` clean.
