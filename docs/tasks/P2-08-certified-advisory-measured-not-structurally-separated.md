# P2-08: "Measured / Certified / Advisory" is a naming/discipline convention, not a structural type distinction

**Priority:** P2 (architectural hardening - the current discipline has held up correctly through extensive testing, so this is about making future contamination *harder*, not fixing an observed bug) | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
The specification's own governing principle: "Measure what happened. Certify what cannot be improved. Label what is estimated. Never mix the three." This is a design philosophy stated once, enforced throughout the codebase by convention and caller discipline rather than by any type-level mechanism.

## Background
Raised by an external review; independently verified against the current code before filing.

`bga/floors/cold.py`'s own docstring already states the discipline explicitly and correctly: cold-floor computation is "Fully independent of LB/certified_headroom/primary confidence/measured attribution (I12)... its output is merged into floors under cold-prefixed keys only by the caller" (`bga/floors/cold.py:18-21`). This is real, correct, and already tested (`P3-06`). But the enforcement mechanism is entirely a naming convention (`cold_`-prefixed dict keys) plus reviewer/caller discipline - `result.floors` is a single flat `dict`, so nothing at the type level prevents a future change from accidentally reading a `cold_`-prefixed (advisory) value where a certified one was expected, or vice versa. The same pattern holds elsewhere: `AnalysisResult`'s fields (`attribution`, `floors`, `signals`, `utilisation`, etc., `bga/ingest/models.py:237-`) are all plain dicts with no structural tagging of measured-vs-certified-vs-advisory provenance.

## Required Fix
1. Introduce a lightweight structural distinction (e.g. dataclasses, `NamedTuple`s, or a small wrapper type per category - `Measured`/`Certified`/`Advisory`) for at least the floors/attribution values most at risk of conflation: `t_infinity_observed`/`lb`/`certified_headroom` (certified) vs. `t_infinity_cold` (advisory) vs. directly-observed attribution/occupancy numbers (measured).
2. This does not need to be a large refactor - even a thin marker (e.g. wrapping advisory values so accidentally treating one as certified requires an explicit unwrap, or a runtime assertion at the report-formatting boundary that advisory keys never appear where certified ones are expected) achieves the goal of making accidental contamination *loud* rather than silent.
3. Keep the existing JSON/text report output shape unchanged (`--format json`/`csv` byte-identical) - this is an internal hardening, not a wire-format change.

## Out of Scope
- Don't do a large-scale rewrite of `AnalysisResult`'s dict-based fields into a fully typed object graph - that's a much bigger architectural change with its own risk/cost tradeoff; this task is scoped to the specific measured/certified/advisory conflation risk the external review flagged, not general "add types everywhere."
- Don't change any currently-correct computation's actual values - this is purely a structural/type-safety hardening on top of already-correct behavior.

## Acceptance Test
1. A deliberate, test-only attempt to read an advisory (cold-prefixed) value into a code path expecting a certified one raises or is caught by the new structural mechanism, rather than silently succeeding.
2. Every existing test (especially `P3-06`'s cold-floor and confidence tests) passes unchanged - `--format json`/`csv` output byte-identical to before this change.
3. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
