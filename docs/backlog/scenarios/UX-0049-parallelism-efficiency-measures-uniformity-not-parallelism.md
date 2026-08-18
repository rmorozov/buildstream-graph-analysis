# UX-49: `parallelism_efficiency` is `mean_width / max_width`, so a perfectly serial build scores 1.000

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-41 (done - which made the widths correct, and this visible)

## Motivation

`bga/structural/analyzer.py::compute_parallelism_profile`:

```python
# Parallelism efficiency (how close to max_parallelism we get on average)
max_width = max(widths) if widths else 0
mean_width = statistics.mean(widths) if widths else 0.0
efficiency = mean_width / max_width if max_width > 0 else 0.0
```

That is the *uniformity* of the level widths - how close each level is to the widest one - which is a different question from how parallel the build is, and it is maximized by the worst possible graph. Measured directly:

```text
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

## Fix Implemented

**Option 2 - renamed, not redefined.** `parallelism_efficiency` is now `width_uniformity`, with the formula unchanged.

This doc's Required Fix said *"Option 1 is the better fit for a build-optimization tool and is what the name promises today"*, and that recommendation is overturned here, with a reason found by measuring rather than by re-arguing: **the parallelism question already has a published answer.** `mean_width` - equivalently `StructuralMetrics.avg_parallelism`, the classic work-over-depth average parallelism - discriminates correctly on the very pair this doc used as its evidence:

| run | `mean_width` (parallelism) | `width_uniformity` |
|---|---|---|
| `examples/06` baseline (six-deep chain) | **1.1** | 0.550 |
| `examples/06` optimized (six-wide fan-out) | **2.2** | 0.367 |

Redefining `parallelism_efficiency` to mean parallelism would have produced two published names for one number. The formula that was there computes a real, distinct shape signal - *how much of the peak width is sustained across the build's depth* - and only its name was wrong. Renaming keeps a useful signal and removes a misleading one, which is strictly better than replacing a useful signal with a duplicate.

Read `width_uniformity` as: low means the graph has a narrow waist somewhere, so peak parallelism is not sustained. A wide-then-single-choke-point-then-wide graph scores below 0.7 while a chain scores 1.000, and both are correct statements about uniformity.

**One thing the rename alone would have left broken.** The text report's `Parallelism Profile` line printed only `min` and `max`, so the one number that separates the two graphs was invisible to anyone reading the report rather than the JSON. It now reads:

```text
run-06-baseline    Parallelism Profile: min=1.0x, avg=1.1x, max=2.0x
run-06-optimized   Parallelism Profile: min=1.0x, avg=2.2x, max=6.0x
```

That is the macro optimization `examples/06` exists to demonstrate, visible in the report for the first time.

### Acceptance tests, and the one that does not apply

1. ✅ A pure serial chain no longer scores 1.000 *under a parallelism name* - it scores 1.000 under a uniformity name, which is the explicitly-sanctioned alternative in this doc's own criterion 1, and is documented as correct in both the field's docstring and its tests.
2. **Does not apply as written.** It asked for `optimized/` to score better than baseline *on this field*; under the rename the field is not a quality score, and the requirement it was really expressing - that some published number moves the right way across the macro fix - is met by `mean_width` (1.1 → 2.2) and now shown in the report.
3. ✅ The 1202-element scale fixture sits between the extremes at 0.859, being genuinely wide but not perfectly uniform.
4. ✅ Field name, docstring, adjacent comment and formula all say uniformity.

Blast radius was as this doc predicted - one `--format json` key, one dataclass field, one serialization site - so the golden snapshot's diff is exactly the rename with the value unchanged.

Tests: 8 new (`tests/unit/test_width_uniformity.py`), pinning both halves of the decision: that the renamed field keeps uniformity semantics, and that `mean_width`/`avg_parallelism` really do answer the parallelism question and agree with each other. Full suite 871 passed, `make lint` clean.

## Verification Log

Filed 2026-08-16, during `UX-41`'s implementation. The formula is quoted verbatim from `bga/structural/analyzer.py`. The chain and fan-out figures are from a direct call into `compute_parallelism_profile` on those two graphs, not reasoned from the formula. The `examples/06` figures are from real `bga graph -f json` runs against real BuildStream 2.7.0 captures (real `bwrap` sandbox, 4-core host), taken after `UX-41` landed - before it, both variants reported the same collapsed widths and the score was not meaningfully comparable. No fix attempted; the choice between renaming and redefining is a real product decision and is left to whoever picks this up.
