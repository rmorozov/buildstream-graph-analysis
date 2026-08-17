# UX-49: `parallelism_efficiency` is `mean_width / max_width`, so a perfectly serial build scores 1.000

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-41 (done - which made the widths correct, and this visible)

## Motivation

`bga/structural/analyzer.py::compute_parallelism_profile`:

```python
# Parallelism efficiency (how close to max_parallelism we get on average)
max_width = max(widths) if widths else 0
mean_width = statistics.mean(widths) if widths else 0.0
efficiency = mean_width / max_width if max_width > 0 else 0.0
```

That is the *uniformity* of the level widths - how close each level is to the widest one - which is a different question from how parallel the build is, and it is maximized by the worst possible graph. Measured directly:

```
pure chain   a->b->c->d     widths=[1, 1, 1, 1]   parallelism_efficiency = 1.000
pure fan-out r->{x, y, z}   widths=[1, 3]         parallelism_efficiency = 0.667
```

**A build with no parallelism whatsoever scores a perfect 1.000**, because every level is exactly as wide as the widest. Adding parallelism to any graph can only lower the score, since it raises `max_width` faster than `mean_width`.

On real projects, after `UX-41` corrected the widths:

| run | `max_width` | `parallelism_efficiency` |
|---|---|---|
| `examples/06` baseline (six-deep chain) | 2 | **0.550** |
| `examples/06` optimized (six-wide fan-out) | 6 | **0.367** |

The `optimized/` variant differs from the baseline by exactly one deliberate macro improvement, and it scores *worse*. This is the same class of defect `UX-27` found in `efficiency_score` - a metric named for a property, moving against that property on the one real pair built to demonstrate it.

`UX-41` is what made this legible rather than what caused it: the formula was always this, but while the widths were the collapsed `[1, N, 1]` the score was meaningless in a way that did not obviously point at the formula. It is filed separately rather than folded into `UX-41` because redefining a published metric is a different act from fixing a wrong computation, and `parallelism_efficiency` is in `--format json` output that consumers may already read.

## Required Fix

Decide what the field is *for*, then either rename it or redefine it - both are acceptable, silently keeping it is not.

1. **If it should mean "how parallel is this build"**, the natural structural definition is work-per-level against the widest level, or more directly `num_elements / num_levels` normalized against `max_width` - i.e. how much of the available width the graph actually uses along its depth. A serial chain must score near 0 and a wide flat graph near 1. Note that `occupancy_ratio` (`UX-27`) already answers the *measured* version of this question; this one is structural and graph-only, and the two should at least not disagree in sign on the `examples/06` pair.
2. **If it should mean "how uniform are the level widths"**, keep the formula and rename it (`width_uniformity`), because that is a real and occasionally useful shape signal - a graph with one huge level and many thin ones has a different problem from an evenly-wide one. The comment above it ("how close to max_parallelism we get on average") is then accurate and only the field name is wrong.

Option 1 is the better fit for a build-optimization tool and is what the name promises today. Whichever is chosen, the field is currently unrendered in the text report - only `min`/`max` widths are shown - so the blast radius is `--format json` consumers plus any future report line, and this is the cheap moment to change it.

## Out of Scope

- `UX-41`'s level decomposition, now correct - this task consumes those widths and does not revisit them.
- `efficiency_score` / `occupancy_ratio` (`UX-27`), which are the *measured* efficiency signals and are separately settled. This is the structural, graph-only one.
- Rendering the field in the text report, which is a separate decision that should follow, not precede, deciding what it means.

## Acceptance Test

1. A pure serial chain scores near 0, not 1.000 (or the field is renamed and a chain scoring 1.000 is then correct and documented as such).
2. `examples/06-macro-micro-optimization`'s `optimized/` variant scores **better** than its baseline, not worse - the two differ by one deliberate macro improvement and the metric must be able to see it.
3. The 1202-element scale fixture, which is genuinely wide and genuinely deep, scores between those two extremes rather than at either.
4. Whatever ships, the field name, the adjacent comment, and the formula all say the same thing. Full suite green.

## Verification Log

Filed 2026-08-16, during `UX-41`'s implementation. The formula is quoted verbatim from `bga/structural/analyzer.py`. The chain and fan-out figures are from a direct call into `compute_parallelism_profile` on those two graphs, not reasoned from the formula. The `examples/06` figures are from real `bga graph -f json` runs against real BuildStream 2.7.0 captures (real `bwrap` sandbox, 4-core host), taken after `UX-41` landed - before it, both variants reported the same collapsed widths and the score was not meaningfully comparable. No fix attempted; the choice between renaming and redefining is a real product decision and is left to whoever picks this up.
