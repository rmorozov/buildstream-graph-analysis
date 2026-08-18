# UX-01: No built-in way to compare two runs (baseline vs. after-a-change)

**Priority:** High | **Status:** 🟢 Done | **Depends on:** none

## Motivation

Filed while brainstorming `bga`'s main user scenarios against its current documentation and CLI, specifically the "iterative optimization loop" scenario the project is about to exercise for real: build a project, run `bga analyze`, make one change intended to improve efficiency, rebuild, run `bga analyze` again, and decide whether it actually helped.

Confirmed directly against `bga/cli.py` (grep for `add_parser`): the only subcommands are `analyze`/`graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` - every one of them reports on a *single* run. There is no `compare`/`diff` command and no `--baseline` flag anywhere. Today, comparing two runs means running `bga analyze` twice and eyeballing two separate text reports, or writing your own `jq` diff against two `--format json` outputs - real friction for exactly the workflow this tool exists to support, and the specific friction the next work session (iteratively optimizing example projects using `bga`'s own output to guide each step) is about to hit immediately.

## Required Fix

1. A new `bga compare RUN_A RUN_B` subcommand (baseline first, candidate second - matches the natural "before, after" reading order). Reuses the existing `analyze_run`/`BuildEfficiencyAnalyzer` pipeline for each run independently - this is a reporting/comparison layer on top of two already-correct single-run analyses, not a new analysis algorithm.
2. Report, for each run and as a signed delta (candidate minus baseline): `total_duration_us`, `t_infinity_observed`, `lb`, `certified_headroom`, `t_c`, `confidence.primary`, and every attribution category (absolute microseconds and percentage-point change).
3. A verdict line - "improved" / "regressed" / "no significant change" - based on a real, documented rule, not a bare `delta != 0`:
   - Must account for confidence: if either run's confidence is below the existing "high" band (`_CONFIDENCE_HIGH = 0.8`, `bga/report/text.py`), the verdict must say so explicitly rather than asserting a confident comparison off potentially-unreliable data.
   - Must account for run identity/comparability: if the two runs' `graph.json` structures are unrelated (wildly different element counts, no overlapping element UIDs), flag that the comparison may not be meaningful rather than reporting a misleading percentage.
4. Both `--format text` (default, human-readable) and `--format json` (machine-readable, for the CI-gating use case `UX-03` will build on).
5. Exit code 0 regardless of verdict (comparing is not itself a failure condition) - `UX-03` is where a "fail the pipeline on regression" exit-code contract belongs, kept separate so `compare` itself stays a pure reporting command.

## Out of Scope

- CI gating / exit-code-on-regression behavior - that's `UX-03`, which depends on this.
- Comparing more than two runs at once (a trend-over-N-runs view) - a real, separate feature if wanted later, not needed for the immediate two-run "did this change help" question.
- Any change to single-run `analyze` output - this is purely additive.

## Acceptance Test

1. Two real, hand-built run directories sharing the same topology (e.g. the golden fixture's shape) where the candidate has one element's duration shortened - `bga compare` reports a correct signed delta in `t_infinity_observed`/attribution and a correct "improved" verdict.
2. The reverse (candidate slower) reports "regressed".
3. Two byte-identical run directories report "no significant change" (not a false "improved"/"regressed" from floating-point noise, if any survives the fix's own arithmetic - prefer exact integer deltas, matching this codebase's general "no float in invariant-adjacent arithmetic" discipline).
4. A run with `confidence.primary < 0.8` triggers an explicit low-confidence caveat in the verdict, not a silently confident comparison.
5. `--format json` output round-trips through `jq` for both the per-field deltas and the verdict string.
6. Full suite green.

## Verification Log
New module `bga/compare.py`: `compare_runs(baseline_dir, candidate_dir, **analyzer_kwargs)` loads and analyzes each run independently via its own `BuildEfficiencyAnalyzer` (no shared state), then computes signed deltas for `total_duration_us`/`t_infinity_observed`/`lb`/`certified_headroom`/`t_c`/`efficiency_score` (UX-02) and every attribution category (absolute + percentage-point). Verdict (`improved`/`regressed`/`no significant change`) is driven by `total_duration_us`'s delta against a 1%-of-baseline significance threshold, computed via exact integer comparison (`abs(delta_us) * 100 >= baseline_total * 1`), not float division. `low_confidence` flags when either run's `confidence.primary` is below `_CONFIDENCE_HIGH` (reused from `bga/report/text.py`). `comparability_warning` flags when the two runs' `graph.elements` share fewer than half their UIDs.

New `bga compare BASELINE CANDIDATE` subcommand (`bga/cli.py`), `--format text|json`, `--capacity` (applied symmetrically to both runs), same `-o`/`-v`/`-q`/`--log-file` flags as every other subcommand. Always exits 0 on a successful comparison regardless of verdict (1 for a missing directory, 2/3 for ingestion/analysis failures, matching the existing exit-code contract). New `format_compare_text` in `bga/report/text.py`; `--format json` serializes `ComparisonResult.to_dict()` directly. Documented in `docs/guides/cli.md` with both example commands verified to actually run.

New test file (`tests/unit/test_compare.py`, 9 tests, matching all 6 acceptance-test items): a shortened candidate reports the correct signed delta and "improved"; the reverse reports "regressed"; byte-identical run dirs report "no significant change" with an exact zero delta; a low-confidence run (no `run_identity`, P1-37's reduced-provenance path) flags `low_confidence=True`; mismatched topologies (few shared element UIDs) trigger the comparability warning; attribution deltas cover every category present in either run; 3 CLI-level subprocess tests confirm exit code 0 regardless of verdict, exit code 1 on a missing directory, and `--format json` round-trips through a real `jq` subprocess for both `.verdict` and `.deltas.total_duration_us`.

```
$ python3 -m pytest tests/unit/test_compare.py -v
9 passed
$ python3 -m pytest -q   # full suite
454 passed, 11 skipped
$ make lint
All checks passed!
$ bga compare tests/fixtures/golden/mixed_task_kinds tests/fixtures/synthetic_multi_subproject
Verdict: REGRESSED  (total duration +141.99s, +1014185.7%, 0.01s -> 142.00s)
  Warning: baseline has 4 element(s), candidate has 9 - only 1 shared element UID(s) (less than half) - these runs may not be the same project; treat any comparison below with real skepticism
```
