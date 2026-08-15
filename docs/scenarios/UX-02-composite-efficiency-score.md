# UX-02: No composite "how efficient is this build, is it good enough" signal

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** none (pairs naturally with `UX-01`, but is independently useful on a single run)

## Motivation

Filed while brainstorming `bga`'s main user scenarios, specifically the question the next work session will need answered repeatedly: "have we optimized this build enough to stop iterating?"

Confirmed directly (grep across `bga/` and `docs/`): no `efficiency_score`, `overall_score`, or equivalent composite metric exists anywhere. What exists today is real and correct but fragmented: `certified_headroom` (absolute microseconds, Part 16), `confidence.primary` (a 0-1 data-quality/trust score, Part 33 - deliberately *not* an efficiency measure), and a handful of per-element diagnostics (blast radius, criticality probability). A user has to mentally combine "24.00s of certified headroom out of 142.00s total" into a percentage themselves, and has no threshold to compare it against - there's no answer in the tool today to "is 17% headroom a lot or a little, and when do I stop."

## Required Fix

1. A new `efficiency_score` (0.0-1.0), computed alongside the existing floors (`bga/analyzer.py::_compute_floors` is the natural home, following the same `Certified`/`assemble_floors` discipline `P2-08` established for this dict). Candidate formula: `lb / total_duration_us` (equivalently `1 - certified_headroom_us / total_duration_us`) - the fraction of wall-clock time that's already at the certified floor. Pick and document the formula deliberately (this task must record *why*, not just pick one), and gate it the same way `certified_headroom` already is (only meaningful when floors are actually computed - `None` when they're not, never a fabricated number).
2. **A mandatory, explicit documentation of what this score does and doesn't measure**, in both the code and the report: `efficiency_score` measures *scheduling* efficiency relative to the observed work (how well-parallelized the current critical path already is) - it says nothing about whether the work itself is minimal. A build with one unnecessarily slow element on an otherwise perfectly-scheduled critical path can show `efficiency_score` near 1.0 while still having real room to improve by *shortening* that element's own work - this is exactly the distinction Critical Path already exists to surface, so the report must present the two together, not let a high efficiency score imply "nothing more to do."
3. A banding/threshold treatment reusing the existing confidence-band pattern and style (`_CONFIDENCE_HIGH = 0.8`/`_CONFIDENCE_MEDIUM = 0.5` in `bga/report/text.py`) - e.g. `>= 0.9` "very efficient - remaining gains are mostly in reducing the critical path's own work, not scheduling", `>= 0.7` "worth checking Certified Headroom", `< 0.7` "meaningful scheduling headroom available". Exact thresholds need real judgment, not just symmetry with confidence's - document the reasoning.
4. Surface in Key Findings (text report) and `--format json`'s `floors` dict. Gate on confidence: an `efficiency_score` computed from low-confidence/low-coverage data should carry the same caveat `UX-01`'s comparison verdict does - don't let a high score read as false precision on unreliable input.

## Out of Scope

- Any change to `certified_headroom`/`lb`/`t_infinity_observed`'s own existing values or computation - this is a new, additive, derived field.
- A single blended "overall quality" score combining efficiency *and* confidence into one number - keep them separate and clearly labeled (this codebase's existing "never mix measured/certified/advisory" discipline, `P2-08`, argues against conflating "how good" with "how sure").

## Acceptance Test

1. A run where `lb == total_duration_us` (no headroom at all) reports `efficiency_score == 1.0`.
2. A run with real certified headroom reports the correct fraction, exactly matching `lb / total_duration_us` computed independently in the test.
3. A run with `floors['lb'] is None` (e.g. no normalized tasks) reports `efficiency_score is None`, not a fabricated value or a crash.
4. The report's own text makes the "scheduling efficiency, not work-minimality" caveat visible somewhere a user reading Key Findings would actually see it - not just buried in a docstring.
5. Full suite green; existing floors/confidence tests unaffected (purely additive field).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
