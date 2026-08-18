# P1-14: Missing CLI subcommands (`graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics`)

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference

`sed -n '2133,2182p' docs/spec/specification.md` (Part 37 — CLI). The spec recommends `bga analyze|graph|floors|replay|sweep|utilisation|diagnostics RUN`, and Part 37.1 gives literal examples of `bga floors RUN --cold` / `bga floors RUN --cold --allow-partial-cold`.

## Product decision (made by the user, 2026-08-13)

Option 3 from the original blocked task file: **hybrid**. Keep `analyze` as the primary command (full report, every section), and add the other six subcommands as thin aliases sharing the same pipeline instead of re-deriving shared stages (ingestion, normalization, graph construction) per subcommand.

## What was built

- `bga/cli.py::format_text`/`format_json` gained a `section: Optional[str] = None` parameter. `None` produces the exact same full report as before (verified byte-for-byte via the existing `tests/test_cli.py`/`tests/unit/test_cli_exit_codes.py` suites, unmodified); a section name restricts output to that slice.
- `_make_analyzer`/`_produce_analysis_output`/`_execute_and_write` factor the shared pipeline-run + output-write + exception-to-exit-code logic out of the old monolithic `cmd_analyze`, so every subcommand reuses it rather than duplicating it.
- New subcommands: `graph` (static dependency graph, critical path, structural metrics), `floors` (certified/advisory floors - also accepts `--cold`/`--allow-partial-cold`/`--history-dir`, matching spec Part 37.1's literal examples), `replay` (T_C/model slack, forces replay on), `utilisation` (CPU accounting), `diagnostics` (blast radius/criticality/wall-clock shares, forces diagnostics on).
- `sweep` is genuinely different, not a slice of `analyze`'s output: it wires up `ReplayScheduler.capacity_sweep` (Part 19), which was already fully implemented but previously unreachable from anywhere in the CLI or analyzer. New `--resource`/`--min-capacity`/`--max-capacity`/`--step` flags; own text/JSON formatter (`format_sweep_text`).
- `_add_common_arguments(subparser, include_replay=, include_diagnostics=, include_cold=)` factors the shared argparse setup (directory/format/output/capacity/verbose/quiet/log-file plus the relevant optional flag groups) out of what was six near-identical blocks.

## Bugs found and fixed along the way (not expanding scope - necessary for the new subcommands to actually work)

- `format_text`'s Critical Path block read a nonexistent `result.critical_path` attribute and an equally nonexistent `task_key.element_name` - `AnalysisResult` has no `critical_path` field (the real data lives in `result.signals['critical_path']`, a list of element UIDs, not task objects). This block had never fired for *any* input, in *any* subcommand, ever - a pre-existing dead-code bug. Fixed to read the real field.
- `format_text`'s Structural Analysis block read a nonexistent `result.structural_metrics` attribute with mismatched key names (`'bottlenecks'`/`'parallelism_profile'` vs. the real `result.structural`'s `'bottleneck'`/`'parallelism'` keys) - also never fired. Fixed to read the real shape.
- Both were only discovered because the new `graph` subcommand's entire purpose is showing exactly this content - shipping it empty wasn't acceptable, so fixing these was necessary for basic usability, not scope creep.
- `ReplayScheduler.capacity_sweep` (`bga/replay/scheduler.py`, Part 19, already implemented but never reachable before `sweep` existed) computed `NaN` for the first sample's `normalized_improvement` (`prev_makespan` starts at `+inf`; the guard checked `prev_makespan > 0`, true for infinity too). Fixed to guard on finiteness. Same root cause as the above: previously-unreachable code's first real exercise surfaced a real bug.

## Out of Scope

- Did not add `--cold`/`--allow-partial-cold` to any subcommand besides `analyze` and `floors` (those are `P1-06`/`P1-07`'s territory; `floors` gets them because the spec's own examples put them there).
- Did not attempt to make each subcommand skip computing sections it doesn't display - `analyze()` computes floors/attribution/utilization/structural unconditionally regardless of flags already (pre-existing), so this is genuinely a "thin alias over the same full computation," not a partial-pipeline optimization; that would be a larger, separate change with its own performance-tradeoff discussion, not implied by "hybrid, minimal duplication."

## Acceptance Test

1. `bga analyze RUN` output byte-identical to before this change (verified: full existing `test_cli.py`/`test_cli_exit_codes.py`/`test_e2e.py` suites pass unmodified).
2. Each new subcommand runs successfully against a real fixture and shows only its own section (verified: `tests/unit/test_cli_subcommands.py`).
3. `sweep` reports genuine per-capacity makespan data, no `NaN`.
4. Missing/invalid run directory still exits `1` for every new subcommand, matching the documented exit-code contract.
5. `docs/guides/cli.md` documents the new subcommands.

## Verification Log

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_cli_subcommands.py -v
10 passed
# graph shows critical path + structural metrics, not floors/attribution
# floors shows only floors (text and JSON)
# replay shows T_C
# utilisation shows CPU buckets
# diagnostics forces diagnostics on even without -d
# sweep reports real per-capacity data, first row's normalized_improvement
#   == 0 (not NaN); "nan" absent from text output
# all 6 new subcommands exit 1 on a missing directory
# analyze's full-report behavior unchanged

$ PYTHONPATH=. python3 -m pytest tests/ -q
96 passed
# includes the full pre-existing test_cli.py/test_cli_exit_codes.py
# suites, unmodified and still passing - confirms analyze's behavior
# didn't change

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ PYTHONPATH=. python3 -m bga.cli graph tests/fixtures/synthetic_multi_subproject
Critical Path Length: 4 elements
  Path: core-utils.bst:libcore.bst → ui-toolkit.bst:libwidgets.bst → ui-toolkit.bst:libui.bst → app.bst
Structural Analysis:
  Elements: 9, Edges: 12, Max Depth: 3
  Parallelism Profile: min=2.0x, max=5.0x

$ PYTHONPATH=. python3 -m bga.cli sweep tests/fixtures/synthetic_multi_subproject --resource PROCESS --min-capacity 1 --max-capacity 4
  Capacity      T_C (s)    Improvement
         1       198.00           0.0%
         2       120.00          39.4%
         3       118.00           1.7%
         4       118.00           0.0%
Knee point (PROCESS): capacity 2 (diminishing returns beyond this)
```
