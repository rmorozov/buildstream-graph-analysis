# P4-02: Refactor report output to lead with what's actionable, not a flat metric dump

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Not spec-mandated in its exact form (the spec defines *what* metrics exist, Parts 11/14-30, not their presentation priority) - this is a usability improvement on top of an already spec-compliant `analysis/v9` payload (`bga/report/text.py`/`json.py` stay the source of truth for every field; this task is about what the *default text report* leads with).

## Current State (confirmed by reading `bga/report/text.py::format_text`)
The full `analyze` text report prints, in a fixed flat order: Certified Floors, Attribution Breakdown (all 8 categories, unweighted), Critical Path, Occupancy Stats, CPU Utilisation (all buckets), Advanced Diagnostics, Structural Analysis. Every metric gets equal visual weight regardless of whether it's normal/expected or a genuine problem worth acting on. Two concrete gaps:
1. **`confidence` and `violations` are never printed in text output at all** - `format_text` has no block for either field, even though `AnalysisResult.confidence`/`.violations` are fully populated (Part 33's hard/soft gates, `P1-13`). A user running the default `bga analyze` has no way to see "was this analysis actually trustworthy" without switching to `--format json` and reading raw fields.
2. There's no synthesized "here's what to look at first" framing anywhere - a user has to mentally combine the Attribution Breakdown's percentages, the blast-radius/criticality diagnostics, and the certified-headroom number themselves to answer "what's actually worth optimizing."

## Required Fix
1. Add a `confidence`/`violations` block to `format_text` (all sections, not diagnostics-only) - at minimum: primary confidence score, which hard/soft gates failed (if any), and a one-line-per-violation summary. This is a straightforward gap-fill, not a design question.
2. Design and add a short "Key Findings" (or similar) block, shown first (before Certified Floors), synthesizing across the already-computed data - no new computation needed, this is presentation-layer only:
   - Confidence headline (e.g. "Confidence: 0.87 (high)" or "Confidence: 0.42 - see N violations below") - surfaces (1) above prominently instead of burying it.
   - The single largest non-`EXECUTION_ON_CHAIN` attribution category, phrased as an opportunity (e.g. "Biggest opportunity: 34% of wall-clock time is DEPENDENCY_WAIT").
   - The top 1-3 elements by blast radius / criticality probability (already computed by `--diagnostics`, Part 25/26) as "elements most worth optimizing first," when diagnostics were run.
   - Certified headroom framed in plain language ("up to Xs of certified headroom available" rather than just a bare number next to LB/T∞).
3. Keep every existing detailed block - this is additive (a synthesized summary on top), not a removal of detail; `--format json`/`csv` are unaffected (machine consumers need the full flat data, not a prose summary).

## Out of Scope
- Don't change any computed value, any JSON/CSV field, or any exit code - this is presentation-only, on top of already-correct data.
- Don't build an interactive/HTML report format - stay within the existing text/json/csv formats unless a follow-up task is explicitly scoped for that.

## Acceptance Test
1. `bga analyze <fixture>` (default text format) shows confidence and any violations without needing `--format json`.
2. A "Key Findings"-style block appears before the detailed sections and correctly reflects a deliberately-constructed fixture with a known dominant wait category and a known worst-blast-radius element (assert the block names the right category/element, not just that it exists).
3. `--format json`/`--format csv` output is byte-identical to before this change (this is presentation-only for the text formatter).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
