# UX-33: the text report hides the critical path when it is longer than 5 elements, and never names choke points at all

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** —

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

## Verification Log

Filed 2026-08-16. Text output and JSON are from one real `bga analyze` / `bga analyze -f json` pair against a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/06-macro-micro-optimization` (BuildStream 2.7.0, 4-core host). The `len(critical_path) <= 5` condition was read directly from `bga/report/text.py`.
