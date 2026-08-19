#!/usr/bin/env python3
"""
BuildStream Build Efficiency Analyzer (bga) - Command Line Interface

This module provides the CLI entry point for analyzing BuildStream build traces.
It implements all commands documented in docs/guides/cli.md.

Usage:
    bga analyze <run_directory> [options]
    bga --version
    bga --help

Examples:
    bga analyze /path/to/run-12345
    bga analyze /path/to/run-12345 --format json --output report.json
    bga analyze /path/to/run-12345 --capacity 16 --replay --heuristic lpt
    bga analyze /path/to/run-12345 --diagnostics --format json | jq '.floors'
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .analyzer import BuildEfficiencyAnalyzer
from .compare import (
    _EFFICIENCY_DROP_PP, DEFAULT_BAND_K, MIN_BASELINE_RUNS, compare_runs,
    efficiency_below_floor,
    efficiency_regression_exceeds_threshold, efficiency_signal_status,
    regression_exceeds_threshold,
)
from .exceptions import AnalysisError, IngestionError
from .ingest.loader import load_historical_runs
from .logging_config import configure_logging
from .replay.scheduler import build_contention_calibration
from .report import (
    SWEEP_CAPACITY_MODEL_CAVEAT,
    format_compare_text,
    format_csv,
    format_json,
    format_sweep_text,
    format_text,
)

logger = logging.getLogger(__name__)


def _make_analyzer(args: argparse.Namespace) -> BuildEfficiencyAnalyzer:
    """Build a BuildEfficiencyAnalyzer from parsed CLI args, shared by
    every subcommand that runs the full analysis pipeline (getattr
    defaults handle subcommands whose argparser doesn't define a given
    flag, e.g. `graph`/`utilisation` have no --cold)."""
    historical_runs = []
    if getattr(args, 'cold', False) and getattr(args, 'history_dir', None):
        historical_runs = load_historical_runs([Path(p) for p in args.history_dir])
        logger.info("Loaded %d historical run(s) for cold-floor analysis", len(historical_runs))

    return BuildEfficiencyAnalyzer(
        capacity=args.capacity,
        run_replay=getattr(args, 'replay', False),
        replay_heuristic=getattr(args, 'heuristic', 'lpt'),
        run_diagnostics=getattr(args, 'diagnostics', False),
        verbose=args.verbose,
        cold=getattr(args, 'cold', False),
        allow_partial_cold=getattr(args, 'allow_partial_cold', False),
        historical_runs=historical_runs,
    )


def _attach_plane2_capacity(args: argparse.Namespace, analyzer, result) -> None:
    """UX-83: let Plane 1's capacity advice consult Plane 2, when Plane 2
    is in hand for the same run.

    Measured on one dual-plane capture, `analyze` said *"31.9% of
    wall-clock is RESOURCE WAIT - try `--capacity N` with a higher N"*
    while `correlate` on the *same* capture named the real fix: an
    element pinned to `-j1`, worth -32.4% and costing no extra capacity.
    Both texts came from one tool reading one build.

    A missing or malformed Plane 2 report is a warning, not a failure:
    the analysis is complete without it and refusing to print it would
    be a worse outcome than printing today's hint.
    """
    path = getattr(args, 'plane2', None)
    if not path:
        return
    from bga.correlate import compute_memory_envelope, summarize_plane2_capacity

    try:
        with open(path, 'r', encoding='utf-8') as handle:
            native_report = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: --plane2 {path} could not be read ({exc}); "
              "continuing without it", file=sys.stderr)
        return
    context = getattr(analyzer, 'run_context', None)
    host_cpu_count = getattr(context, 'host_cpu_count', None) or getattr(
        context, 'cpu_budget', None
    )
    result.plane2_capacity = summarize_plane2_capacity(native_report, host_cpu_count)
    # UX-104: the memory half of the same question. `--builders` is the
    # knob both halves are about, and advice that clears the CPU check
    # and blows the memory one is advice to build into swap - the worst
    # build slowdown there is, and one no CPU-side signal predicts.
    result.memory_envelope = compute_memory_envelope(
        native_report,
        getattr(context, 'max_jobs', None),
        getattr(context, 'memory_budget_mb', None)
        or getattr(context, 'host_memory_mb', None),
    )


def _produce_analysis_output(args: argparse.Namespace, section: Optional[str]) -> str:
    """Run the full analysis pipeline and format one report section (or
    the full report when section is None). This is the single pipeline
    every hybrid subcommand alias (analyze/graph/floors/replay/
    diagnostics/utilisation, P1-14) shares - each just restricts which
    section of the same AnalysisResult gets shown, rather than
    re-deriving shared pipeline stages (ingestion, normalization, graph
    construction) once per subcommand.
    """
    run_dir = Path(args.directory)

    if getattr(args, 'allow_partial_cold', False) and not getattr(args, 'cold', False):
        logger.warning("--allow-partial-cold has no effect without --cold; ignoring")

    analyzer = _make_analyzer(args)
    # UX-47: tell the pipeline which section is going to be rendered so
    # it can skip stages this section does not consume. `analyze` passes
    # None and is unaffected.
    result = analyzer.analyze(run_dir, section=section)
    _attach_plane2_capacity(args, analyzer, result)
    by_kind = getattr(args, 'by_kind', False)

    if args.format == 'json':
        return format_json(result, section=section, by_kind=by_kind)
    elif args.format == 'csv':
        return format_csv(result)
    return format_text(result, section=section, by_kind=by_kind)


def _produce_sweep_output(args: argparse.Namespace) -> str:
    """Run a capacity sweep (Part 19) - genuinely different from the
    other subcommands: not a slice of one AnalysisResult, but a series
    of replay runs across a range of capacity values for one resource.
    Reuses ReplayScheduler.capacity_sweep directly (already implemented,
    previously unreachable from anywhere in the CLI or analyzer).
    """
    run_dir = Path(args.directory)

    analyzer = BuildEfficiencyAnalyzer(capacity=args.capacity, verbose=args.verbose)
    analyzer.load(run_dir)
    analyzer.normalize()

    contention_calibration = None
    calibration_capacities: List[int] = []
    if getattr(args, 'calibration_dir', None):
        calibration_runs = load_historical_runs([Path(p) for p in args.calibration_dir])
        logger.info("Loaded %d calibration run(s) for UX-14 tier 2 contention modeling", len(calibration_runs))
        contention_calibration = build_contention_calibration(calibration_runs, args.resource)
        raw_capacities = [
            (hist_context.resource_capacities or {}).get(args.resource)
            for hist_context, _g, _t in calibration_runs
        ]
        calibration_capacities = sorted({cap for cap in raw_capacities if cap is not None})

    sweep_result = analyzer.replay_scheduler.capacity_sweep(
        resource=args.resource,
        min_capacity=args.min_capacity,
        max_capacity=args.max_capacity,
        step=args.step,
        contention_calibration=contention_calibration,
    )

    if args.format == 'json':
        return json.dumps({
            'resource': args.resource,
            'sweeps': sweep_result.sweeps,
            'knee_points': sweep_result.knee_points,
            'monotonicity_violations': sweep_result.monotonicity_violations,
            'capacity_model_caveat': SWEEP_CAPACITY_MODEL_CAVEAT,
            'calibration_capacities': calibration_capacities,
        }, indent=2, default=str)
    # UX-83: the sweep is a replay-model answer and the replay model does
    # not know about CPU. When a Plane 2 report for the same run is
    # supplied, the knee line says what was actually measured.
    plane2_capacity = {}
    memory_envelope = {}
    if getattr(args, 'plane2', None):
        holder = type('_R', (), {})()
        _attach_plane2_capacity(args, analyzer, holder)
        plane2_capacity = getattr(holder, 'plane2_capacity', {})
        # UX-104: and the memory ceiling, for the same reason - a knee
        # above the memory-feasible capacity is a recommendation to swap.
        memory_envelope = getattr(holder, 'memory_envelope', {})
    return format_sweep_text(
        args.resource, sweep_result,
        calibration_capacities=calibration_capacities,
        plane2_capacity=plane2_capacity,
        memory_envelope=memory_envelope,
    )


def _memory_envelope_delta(args: argparse.Namespace) -> dict:
    """UX-104: the two runs' memory envelopes, and whether the
    candidate's grew.

    Needs a Plane 2 report per run, because peak RSS is measured inside
    the sandbox and a run directory does not carry it. Two flags rather
    than one: reusing the candidate's report for both would compare a
    run against itself and always report no growth, which is the kind of
    check that passes because it cannot fail.
    """
    baseline_path = getattr(args, 'baseline_plane2', None)
    candidate_path = getattr(args, 'candidate_plane2', None)
    if not baseline_path or not candidate_path:
        return {}
    from bga.correlate import compute_memory_envelope
    from bga.ingest.loader import load_all

    envelopes = {}
    for label, plane2_path, run_dir in (
        ('baseline', baseline_path, args.baseline),
        ('candidate', candidate_path, args.candidate),
    ):
        try:
            with open(plane2_path, 'r', encoding='utf-8') as handle:
                native_report = json.load(handle)
            run_context, _graph, _trace = load_all(Path(run_dir))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Warning: --{label}-plane2 {plane2_path} could not be used ({exc}); "
                  "continuing without the memory note", file=sys.stderr)
            return {}
        envelopes[label] = compute_memory_envelope(
            native_report,
            getattr(run_context, 'max_jobs', None),
            getattr(run_context, 'memory_budget_mb', None)
            or getattr(run_context, 'host_memory_mb', None),
        )

    baseline_at = (envelopes['baseline'] or {}).get('at_observed_builders')
    candidate_at = (envelopes['candidate'] or {}).get('at_observed_builders')
    if not baseline_at or not candidate_at:
        return {}
    delta_mb = candidate_at['envelope_mb'] - baseline_at['envelope_mb']
    return {
        'baseline_envelope_mb': baseline_at['envelope_mb'],
        'candidate_envelope_mb': candidate_at['envelope_mb'],
        'delta_mb': delta_mb,
        'delta_share': (
            delta_mb / baseline_at['envelope_mb'] if baseline_at['envelope_mb'] else None
        ),
        'candidate_fits': candidate_at['fits'],
        'host_memory_mb': envelopes['candidate'].get('host_memory_mb'),
        'note': (
            "A note, not a gate: peak RSS has no measured noise band, so a grown "
            "envelope is a fact to look at rather than a threshold to fail."
        ),
    }


def _produce_compare_output(args: argparse.Namespace):
    """Run bga compare BASELINE CANDIDATE (UX-01) - two independent
    single-run analyses (bga/analyzer.py, unchanged) plus a comparison/
    verdict layer (bga/compare.py). --capacity, if given, applies to
    both runs symmetrically. Returns (output_str, comparison) - the
    ComparisonResult itself is returned alongside the formatted string
    so _execute_compare_and_write's regression gate (UX-03) can inspect
    it without re-running the whole comparison a second time."""
    comparison = compare_runs(
        Path(args.baseline), Path(args.candidate),
        baseline_runs=[Path(p) for p in (getattr(args, 'baseline_run', None) or [])],
        band_k=getattr(args, 'band_k', None) or DEFAULT_BAND_K,
        capacity=args.capacity, verbose=args.verbose,
    )
    # UX-87: stamped before serialization so `--format json` carries it -
    # a CI consumer must be able to tell "the efficiency gate passed"
    # from "the efficiency gate did not run".
    signal = efficiency_signal_status(
        comparison,
        drop_gate_on=getattr(args, 'fail_on_efficiency_regression', False),
        floor_gate_on=getattr(args, 'min_efficiency', None) is not None,
    )
    comparison.efficiency_gate_evaluated = signal['evaluated']
    comparison.efficiency_gate_signal = signal

    # UX-104 item 2: did this change make the build need more memory?
    # A note, not a gate - there is no noise band for peak RSS, and this
    # codebase does not gate on a threshold it has not measured.
    comparison.memory_envelope_delta = _memory_envelope_delta(args)

    if args.format == 'json':
        output = json.dumps(comparison.to_dict(), indent=2, default=str)
    else:
        output = format_compare_text(comparison)
    return output, comparison


def _print_missing_input_hint(run_dir: Path) -> None:
    """Print an actionable hint for the specific "some but not all of
    run-context.json/graph.json/trace.json are present" case (P4-10) -
    the generic FileNotFoundError message is technically correct but
    doesn't tell a first-time user *how* to get the missing piece from a
    real BuildStream project/build. Only fires when the directory has at
    least one of the three real input files already (so a genuinely empty
    or unrelated directory doesn't get a BuildStream-specific hint that
    doesn't apply to it).
    """
    graph_present = (run_dir / 'graph.json').exists()
    trace_present = (run_dir / 'trace.json').exists()
    run_context_present = (
        (run_dir / 'run-context.json').exists() or (run_dir / 'run_context.json').exists()
    )
    if not (graph_present or trace_present or run_context_present):
        return

    # Every hint here has to be runnable as printed. They used to name
    # `tools/<script>.py` paths, which are not executable (no +x bit) and
    # not on PATH - a user who is already stuck was handed a command that
    # fails with "Permission denied". `bga` has had front-door aliases
    # for all of them since UX-67; those are what a reader can paste.
    missing = []
    if not graph_present:
        missing.append(("graph.json", "bga graph-from-show <project_dir> <targets...> graph.json"))
    if not trace_present:
        missing.append((
            "trace.json",
            "bga log-to-chrome <log> trace-chrome.json"
            " && bga chrome-to-trace trace-chrome.json trace.json",
        ))
    if not run_context_present:
        missing.append(("run-context.json", "bga run-context <log> run-context.json"))
    if not missing:
        return

    print(
        "Hint: this looks like a partially-populated run directory from a real "
        "BuildStream project. To produce the missing file(s) from a real "
        "BuildStream invocation's project directory and log, see:",
        file=sys.stderr,
    )
    for filename, tool_hint in missing:
        print(f"  {filename}: {tool_hint}", file=sys.stderr)
    print(
        "  (or run `bga extract <project_dir> <log> <run_dir>` to produce all three "
        "from one project + log in a single step - see "
        "docs/spec/ingestion-pipeline.md)",
        file=sys.stderr,
    )


def _execute_and_write(args: argparse.Namespace, produce_output) -> int:
    """Shared directory validation, logging setup, output writing, and
    exception-to-exit-code mapping for every subcommand. produce_output
    is a zero-arg callable that does the actual analysis work and
    returns the formatted output string, or raises.
    """
    configure_logging(verbose=args.verbose, quiet=args.quiet, log_file=args.log_file)

    run_dir = Path(args.directory)

    if not run_dir.exists():
        print(f"Error: Directory does not exist: {run_dir}", file=sys.stderr)
        return 1

    if not run_dir.is_dir():
        print(f"Error: Not a directory: {run_dir}", file=sys.stderr)
        return 1

    try:
        output = produce_output()

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output)
            if args.verbose:
                print(f"Report written to: {output_path}", file=sys.stderr)
        else:
            print(output)

        return 0

    except FileNotFoundError as e:
        # A required input file (run-context.json/graph.json/trace.json) is
        # missing from an otherwise-existing run directory - this is a
        # "missing files" precondition problem (docs/guides/cli.md exit code 1),
        # distinct from malformed *content* in a file that does exist
        # (exit code 2, handled below).
        logger.error("Required input file not found: %s", e)
        print(f"Error: Required input file not found - {e}", file=sys.stderr)
        _print_missing_input_hint(run_dir)
        return 1
    except AnalysisError as e:
        # Graph cycles and other analysis-pipeline failures - exit code 3
        # per docs/guides/cli.md. Checked by type, not by string-matching the
        # message, since AnalysisError is now raised specifically for this.
        logger.error("Analysis failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 3
    except (IngestionError, json.JSONDecodeError) as e:
        logger.error("Ingestion failed: %s", e)
        print(f"Error: Malformed input - {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        logger.error("Error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        logger.exception("Unexpected error")
        if not args.verbose:
            print(f"Error: {e}", file=sys.stderr)
        return 2


# Distinct from exit codes 1 (general error)/2 (ingestion failure)/3
# (analysis failure), all of which mean "bga itself broke" - this one
# means the opposite: bga ran successfully and is reporting that the
# *analyzed build* regressed (UX-03). A CI system needs to tell these
# apart to decide whether to re-run/investigate bga itself vs. block a
# PR for a real regression.
EXIT_CODE_REGRESSION = 4
# UX-39: deliberately distinct from EXIT_CODE_REGRESSION. "The build got
# slower" and "the build got less efficient" are different verdicts and
# often different teams' problems - a pipeline must be able to warn on
# the first and fail on the second, which one shared exit code makes
# impossible.
EXIT_CODE_EFFICIENCY_REGRESSION = 5
# UX-78: "these two runs are not comparable" is not a verdict about the
# build, so it must not share an exit code with one. README and the
# real-project guide both promised a refusal here while the code only
# warned; a golden fixture against a real run produced
# `Verdict: REGRESSED (+105668.8%)` and exit 4 under the gate, which in
# CI reads as "your build got slower" when the truth is "your job is
# comparing the wrong things".
EXIT_CODE_MISMATCHED_RUNS = 6
# UX-87: "the gate you asked for could not run" is not a verdict about
# the build either. Reusing 4 would put it in the same bucket as "your
# build got slower", which is the mis-triage `UX-88` already records
# against that code; reusing 5 would assert the build is less efficient,
# which is precisely what could not be determined. Only reachable with
# `--require-efficiency-signal`, which is opt-in: without it the gate
# still fails open, it just says so now.
#
# `--fail-on-low-confidence` (UX-40) keeps returning 4 despite being the
# same shape of flag - it shipped that way and a pipeline may key on it.
EXIT_CODE_SIGNAL_UNAVAILABLE = 7

# UX-79: the share of newly-added work that may land on the critical path
# before the marginal gate fires. Measured on fixtures at two scales: a
# well-added pair scores 0.00 and a serialized pair 1.00, at 11 elements
# and at 1201 - so the threshold sits in a wide, scale-invariant gap
# rather than being tuned to one project's size.
DEFAULT_MAX_ADDITION_STRETCH = 0.5


def _compare_exit_code(args: argparse.Namespace, comparison) -> int:
    """UX-03's CI regression gate: only active when --fail-on-regression
    is passed (bga compare's default behavior - matching UX-01's own
    design note - stays "always exit 0 regardless of verdict", since
    comparing is not itself a failure condition). A low-confidence
    comparison fails open (exits 0 with a visible warning) rather than
    block a pipeline on a possibly-noisy signal - the same reasoning
    _CONFIDENCE_HIGH already gates comparison.low_confidence on."""
    efficiency_gate_on = (
        getattr(args, 'fail_on_efficiency_regression', False)
        or getattr(args, 'min_efficiency', None) is not None
    )
    marginal_gate_on = getattr(args, 'fail_on_inefficient_additions', False)
    if (not getattr(args, 'fail_on_regression', False)
            and not efficiency_gate_on and not marginal_gate_on):
        return 0

    # UX-54: checked before the low-confidence fail-open, and failing
    # *closed*. Failing open exists so a noisy signal cannot block a
    # pipeline; a build that did not complete is not a noisy signal, and
    # a gate that waves it through on scheduling grounds is exactly the
    # hazard this project's CI story is meant to remove. Measured: a real
    # freedesktop-sdk capture in which all four attempted elements failed
    # scored an Efficiency Score of 1.00 at confidence 0.14, so the old
    # order would have failed open and reported green.
    if comparison.failed_runs:
        print(
            f"Build failure gate FAILED: the {' and '.join(comparison.failed_runs)} "
            "run describes a build that did not complete (one or more elements "
            "ended in FAILURE). No scheduling verdict is meaningful for it, so "
            "this is a failure rather than a fail-open. "
            "See docs/backlog/scenarios/UX-0054-a-failed-build-scores-perfectly.md.",
            file=sys.stderr,
        )
        return EXIT_CODE_REGRESSION

    if comparison.low_confidence:
        # UX-40: failing open is the right default (do not block a
        # pipeline on a signal you do not trust), but a gate that
        # silently stops gating reports green while checking nothing, so
        # a pipeline must be able to opt out of it.
        if getattr(args, 'fail_on_low_confidence', False):
            print(
                "Confidence gate FAILED: at least one run's confidence is below "
                "the 'high' band and --fail-on-low-confidence was requested, so "
                "this comparison is treated as a failure rather than failing open. "
                "See docs/backlog/scenarios/UX-0040-real-runs-systematically-fail-the-confidence-gate.md.",
                file=sys.stderr,
            )
            return EXIT_CODE_REGRESSION
        # UX-39: name the gates that were actually requested - the
        # efficiency gate inherits this same fail-open rule, and a
        # message hardcoding "--fail-on-regression" would be wrong for a
        # pipeline that only asked for the efficiency one.
        requested = [
            flag for flag, on in (
                ('--fail-on-regression', getattr(args, 'fail_on_regression', False)),
                ('--fail-on-efficiency-regression',
                 getattr(args, 'fail_on_efficiency_regression', False)),
                ('--min-efficiency', getattr(args, 'min_efficiency', None) is not None),
                ('--fail-on-inefficient-additions', marginal_gate_on),
            ) if on
        ]
        print(
            f"Warning: {'/'.join(requested)} not applied - at least one run's "
            "confidence is below the 'high' band, so this comparison is not "
            "reliable enough to gate a pipeline on (failing open, exit 0). "
            "Pass --fail-on-low-confidence to treat this as a failure instead. "
            "See docs/backlog/scenarios/UX-0003-ci-regression-gate.md.",
            file=sys.stderr,
        )
        return 0

    # UX-79: the marginal gate first, because it is the specific verdict
    # and the two whole-build gates are the general ones - a pipeline
    # that asked for both should be told what the *change* did before
    # being told what the repository looks like.
    if marginal_gate_on:
        marginal = getattr(comparison, 'marginal_efficiency', None)
        limit = getattr(args, 'max_addition_stretch', DEFAULT_MAX_ADDITION_STRETCH)
        if marginal is None:
            # UX-87's lesson applied before it is fixed: a gate that
            # silently stops gating reports green while checking nothing.
            print(
                "Marginal gate not applied: this change added no elements with "
                "measured work, so there is nothing to judge the efficiency of. "
                "(This is not a pass - it is an empty check.)",
                file=sys.stderr,
            )
        elif marginal['stretch'] > limit:
            on_path = ", ".join(marginal['on_critical_path'])
            print(
                f"Marginal efficiency gate FAILED: "
                f"{marginal['added_critical_path_us'] / 1e6:.1f}s of the "
                f"{marginal['added_work_us'] / 1e6:.1f}s this change added landed on "
                f"the critical path (stretch {marginal['stretch']:.2f} > {limit:.2f}) - "
                f"on the path: {on_path}. Adding work is allowed; adding it "
                f"serialized is what this gate exists to catch, and unlike the "
                f"whole-build efficiency gate it does not weaken as the project grows. "
                f"See docs/backlog/scenarios/UX-0079-efficiency-gate-dilutes-with-project-size.md.",
                file=sys.stderr,
            )
            return EXIT_CODE_EFFICIENCY_REGRESSION

    # UX-39: the efficiency gate is checked first and reported on its own
    # exit code. Order matters only for which code a pipeline sees when
    # both fire, and "less efficient" is the more actionable of the two -
    # a build that got slower *and* less efficient should be triaged as
    # the second.
    if efficiency_gate_on:
        # UX-87: a gate that stops gating must say so. Both efficiency
        # gates read `occupancy_ratio` and both return False - pass -
        # when a run lacks it, so a pipeline that asked for the gate
        # would see exit 0 and nothing on stderr while nothing was
        # checked. Fail-open stays the default (UX-40's precedent: do not
        # block a pipeline on a signal you do not have); it just stops
        # being silent, and `--require-efficiency-signal` turns it into a
        # failure for pipelines that would rather break than not gate.
        signal = getattr(comparison, 'efficiency_gate_signal', None) or efficiency_signal_status(
            comparison,
            drop_gate_on=getattr(args, 'fail_on_efficiency_regression', False),
            floor_gate_on=getattr(args, 'min_efficiency', None) is not None,
        )
        if signal['gates_not_applied']:
            runs = " and ".join(signal['missing_occupancy_in'])
            print(
                f"Efficiency gate NOT APPLIED: {'/'.join(signal['gates_not_applied'])} "
                f"was requested, but the {runs} run has no `occupancy_ratio` signal, "
                f"so there is nothing to gate on. This is not a pass - it is an "
                f"unevaluated check (`efficiency_gate_evaluated: false` in --format "
                f"json). Pass --require-efficiency-signal to treat this as a failure "
                f"instead. See docs/backlog/scenarios/"
                f"UX-0087-efficiency-gates-silently-no-op-when-occupancy-is-missing.md.",
                file=sys.stderr,
            )
            if getattr(args, 'require_efficiency_signal', False):
                return EXIT_CODE_SIGNAL_UNAVAILABLE

        if efficiency_below_floor(comparison, getattr(args, 'min_efficiency', None)):
            candidate = comparison.candidate_metrics.get('occupancy_ratio')
            print(
                f"Efficiency gate FAILED: dispatch occupancy {candidate * 100:.1f}% is below "
                f"the declared floor of {args.min_efficiency * 100:.1f}% "
                f"(--min-efficiency). This is a property of the candidate run alone - "
                f"no baseline comparison was needed.",
                file=sys.stderr,
            )
            return EXIT_CODE_EFFICIENCY_REGRESSION
        if getattr(args, 'fail_on_efficiency_regression', False) and \
                efficiency_regression_exceeds_threshold(comparison, args.max_efficiency_drop):
            baseline = comparison.baseline_metrics.get('occupancy_ratio')
            candidate = comparison.candidate_metrics.get('occupancy_ratio')
            threshold_desc = (
                f"{args.max_efficiency_drop}pp" if args.max_efficiency_drop is not None
                else f"the default {_EFFICIENCY_DROP_PP}pp"
            )
            print(
                f"Efficiency gate FAILED: dispatch occupancy fell "
                f"{(baseline - candidate) * 100:.1f}pp ({baseline * 100:.1f}% -> "
                f"{candidate * 100:.1f}%), beyond {threshold_desc}. The build may or may "
                f"not be slower - this gate is about whether the work it does is being "
                f"done efficiently (see UX-39).",
                file=sys.stderr,
            )
            return EXIT_CODE_EFFICIENCY_REGRESSION

    if not getattr(args, 'fail_on_regression', False):
        return 0

    if regression_exceeds_threshold(comparison, args.regression_threshold):
        threshold_desc = (
            f"{args.regression_threshold}%" if args.regression_threshold is not None
            else "the default significance threshold"
        )
        print(
            f"Regression gate FAILED: candidate run's total duration regressed "
            f"beyond {threshold_desc} (verdict: {comparison.verdict}).",
            file=sys.stderr,
        )
        return EXIT_CODE_REGRESSION

    return 0


def _execute_compare_and_write(args: argparse.Namespace) -> int:
    """Directory validation, logging setup, output writing, and
    exception-to-exit-code mapping for `bga compare` - a separate
    function from _execute_and_write because compare validates *two*
    directories (baseline/candidate), not the single `args.directory`
    every other subcommand has; the exception-handling shape is
    otherwise identical (same exit-code contract, docs/guides/cli.md)."""
    configure_logging(verbose=args.verbose, quiet=args.quiet, log_file=args.log_file)

    for label, raw_dir in (("baseline", args.baseline), ("candidate", args.candidate)):
        run_dir = Path(raw_dir)
        if not run_dir.exists():
            print(f"Error: {label} directory does not exist: {run_dir}", file=sys.stderr)
            return 1
        if not run_dir.is_dir():
            print(f"Error: {label} path is not a directory: {run_dir}", file=sys.stderr)
            return 1

    try:
        output, comparison = _produce_compare_output(args)

        # UX-78: refuse before the comparison is printed or written. A
        # mismatched pair produces numbers that are arithmetically
        # correct and meaningless, and printing them beside a refusal
        # would leave a reader to decide which to believe.
        if comparison.mismatches and not getattr(args, 'allow_mismatch', False):
            checks = ", ".join(m['check'] for m in comparison.mismatches)
            print(
                f"Refusing to compare these runs ({checks}):",
                file=sys.stderr,
            )
            for mismatch in comparison.mismatches:
                print(f"  - {mismatch['message']}", file=sys.stderr)
            print(
                "Pass --allow-mismatch to compare anyway (the comparison is then "
                "printed with the warning above, as it was before UX-78).",
                file=sys.stderr,
            )
            return EXIT_CODE_MISMATCHED_RUNS

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output)
            if args.verbose:
                print(f"Report written to: {output_path}", file=sys.stderr)
        else:
            print(output)

        return _compare_exit_code(args, comparison)

    except FileNotFoundError as e:
        logger.error("Required input file not found: %s", e)
        print(f"Error: Required input file not found - {e}", file=sys.stderr)
        return 1
    except AnalysisError as e:
        logger.error("Analysis failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 3
    except (IngestionError, json.JSONDecodeError) as e:
        logger.error("Ingestion failed: %s", e)
        print(f"Error: Malformed input - {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        logger.error("Error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        logger.exception("Unexpected error")
        if not args.verbose:
            print(f"Error: {e}", file=sys.stderr)
        return 2


def cmd_compare(args: argparse.Namespace) -> int:
    """Execute `bga compare BASELINE CANDIDATE` (UX-01) - compares two
    independently-analyzed runs and reports signed deltas plus a
    verdict (improved/regressed/no significant change), gated on
    confidence and graph comparability. By default exits 0 on a
    successful comparison regardless of verdict - comparing is not
    itself a failure condition. `--fail-on-regression` opts into a
    distinct exit code when the candidate genuinely regressed (UX-03's
    CI gate) - see _compare_exit_code."""
    return _execute_compare_and_write(args)


def cmd_cache_trend(args: argparse.Namespace) -> int:
    """Execute `bga cache-trend RUN...` (UX-103) - is the cache getting
    worse?

    Separate from `compare` for the same reason `correlate` is: it reads
    a *series*, not a pair, and the question it answers - "is the
    infrastructure degrading" - is about the cache rather than about any
    change to the project."""
    from bga.cache_trend import format_trend_text, trend_from_run_dirs

    for run_dir in args.run_dirs:
        if not Path(run_dir).is_dir():
            print(f"Error: not a run directory: {run_dir}", file=sys.stderr)
            return 1
    try:
        trend = trend_from_run_dirs(args.run_dirs)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    output = (
        json.dumps(trend, indent=2) if args.format == 'json'
        else format_trend_text(trend)
    )
    if getattr(args, 'output', None):
        with open(args.output, 'w', encoding='utf-8') as handle:
            handle.write(output + '\n')
    else:
        print(output)
    # UX-111: the rows still print - unlike `bga compare`, which refuses
    # before printing, because each row here is a real reading of its own
    # run and only the *band* is cross-run. But a CI job that pipes a
    # heterogeneous series must not read a clean exit as a healthy cache,
    # so the not-comparable code is the same one `compare` uses.
    if trend.get('heterogeneous'):
        print(
            f"Refusing a verdict: {trend['heterogeneous']['message']}",
            file=sys.stderr,
        )
        return EXIT_CODE_MISMATCHED_RUNS
    return 0


def cmd_correlate(args: argparse.Namespace) -> int:
    """Execute `bga correlate RUN NATIVE_REPORT` (UX-51) - joins a Plane
    1 analysis with a Plane 2 native trace report on element UID, the
    only contract between the two planes, and reports what neither can
    say alone: whether the elements that dominate the critical path are
    compute-bound or merely badly built.

    Deliberately a separate command rather than a section of `analyze`:
    the join reads two finished artifacts and neither plane knows about
    it, so both stay independently replaceable. See bga/correlate.py for
    the evidence behind that choice."""
    from bga.correlate import correlate, format_correlation

    try:
        with open(args.native_report, 'r', encoding='utf-8') as f:
            native_report = json.load(f)
    except FileNotFoundError:
        print(f"Error: native report not found: {args.native_report}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: {args.native_report} is not valid JSON - {e}", file=sys.stderr)
        return 2

    if not isinstance(native_report, dict) or 'by_element' not in native_report:
        print(
            f"Error: {args.native_report} does not look like a "
            "`bst_native_build_tracer.py run` report (no `by_element` key). "
            "Pass the JSON report that `run` writes, not a raw trace log.",
            file=sys.stderr,
        )
        return 2

    def produce() -> str:
        analyzer = _make_analyzer(args)
        result = analyzer.analyze(Path(args.directory))
        from bga.report.json import format_json
        analysis = json.loads(format_json(result))
        # UX-82: the tasks and run context let the join *replay* the
        # observed run with never-read gating edges removed, instead of
        # only reporting each edge separately and leaving the reader to
        # invent the restructuring themselves.
        # UX-100: Plane 3's toll, when a report for the same project is
        # supplied. Without it the merge half of the granularity findings
        # has no input and is silent, which is correct - the toll is the
        # whole basis for calling an element too small.
        cache_logs = None
        if getattr(args, 'cache_logs', None):
            try:
                with open(args.cache_logs, 'r', encoding='utf-8') as handle:
                    cache_logs = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                print(f"Warning: --cache-logs {args.cache_logs} could not be read "
                      f"({exc}); continuing without it", file=sys.stderr)
        joined = correlate(
            analysis, native_report,
            tasks=getattr(analyzer, 'normalized_tasks', None),
            run_context=getattr(analyzer, 'run_context', None),
            cache_logs=cache_logs,
            dependencies=getattr(getattr(analyzer, 'graph', None), 'dependencies', None),
        )
        if args.format == 'json':
            return json.dumps(joined, indent=2)
        return format_correlation(joined)

    return _execute_and_write(args, produce)


def cmd_analyze(args: argparse.Namespace) -> int:
    """
    Execute the analyze command - the full report (Parts 1-39), every
    section together. This is the primary command; the section-specific
    subcommands below (graph/floors/replay/diagnostics/utilisation) are
    thin aliases over the same pipeline (P1-14 hybrid resolution: keep
    `analyze` as the primary command per the current design, and add
    the spec's Part 37 command list as aliases rather than re-deriving
    shared pipeline stages per subcommand).
    """
    return _execute_and_write(args, lambda: _produce_analysis_output(args, section=None))


def cmd_graph(args: argparse.Namespace) -> int:
    """Execute `bga graph RUN` - static dependency graph (Part 5),
    critical path (Part 14.1), and structural metrics (M6) only."""
    return _execute_and_write(args, lambda: _produce_analysis_output(args, section='graph'))


def cmd_floors(args: argparse.Namespace) -> int:
    """Execute `bga floors RUN [--cold] [--allow-partial-cold]` -
    certified/advisory floors (Parts 14-17) only. Matches spec Part
    37.1's own literal examples (`bga floors RUN --cold`)."""
    return _execute_and_write(args, lambda: _produce_analysis_output(args, section='floors'))


def cmd_replay(args: argparse.Namespace) -> int:
    """Execute `bga replay RUN [--heuristic H]` - deterministic replay
    (Part 18) only. Forces replay on regardless of a bare -r/--replay
    flag, since running replay is the whole point of this subcommand."""
    args.replay = True
    return _execute_and_write(args, lambda: _produce_analysis_output(args, section='replay'))


def cmd_sweep(args: argparse.Namespace) -> int:
    """Execute `bga sweep RUN --resource NAME` - capacity sweep (Part
    19). Unlike the other subcommands, this isn't a slice of one
    AnalysisResult - it's a series of replay runs across a capacity
    range, so it has its own producer function rather than sharing
    _produce_analysis_output."""
    return _execute_and_write(args, lambda: _produce_sweep_output(args))


def cmd_utilisation(args: argparse.Namespace) -> int:
    """Execute `bga utilisation RUN` - CPU utilisation accounting (Part
    30, M4) only."""
    return _execute_and_write(args, lambda: _produce_analysis_output(args, section='utilisation'))


def cmd_diagnostics(args: argparse.Namespace) -> int:
    """Execute `bga diagnostics RUN` - advanced diagnostics (Parts
    20-29, M5) only. Forces diagnostics on regardless of a bare
    -d/--diagnostics flag, since running them is the whole point of
    this subcommand."""
    args.diagnostics = True
    return _execute_and_write(args, lambda: _produce_analysis_output(args, section='diagnostics'))


def _add_common_arguments(
    subparser: argparse.ArgumentParser,
    include_replay: bool = False,
    include_diagnostics: bool = False,
    include_cold: bool = False,
) -> None:
    """
    Add the argument set shared by every subcommand (directory, format,
    output, capacity, verbose/quiet/log-file), plus the optional groups
    each hybrid alias needs (P1-14): `--replay`/`--heuristic` for
    `analyze`/`replay`, `--diagnostics` for `analyze`/`diagnostics`,
    `--cold`/`--allow-partial-cold`/`--history-dir` for `analyze`/`floors`
    (the latter matching spec Part 37.1's own literal `bga floors RUN
    --cold` examples).
    """
    subparser.add_argument(
        'directory',
        type=str,
        help='Path to the BuildStream run directory (e.g., ~/.buildstream/cache/artifacts/run-<uuid>)'
    )

    subparser.add_argument(
        '-f', '--format',
        type=str,
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format: text (human-readable), json (machine-readable), csv (attribution data). Default: text'
    )

    subparser.add_argument(
        '-o', '--output',
        type=str,
        help='Write output to file instead of stdout'
    )

    subparser.add_argument(
        '-c', '--capacity',
        type=int,
        default=None,
        metavar='N',
        help='Override system resource capacity (affects LB and replay calculations). Default: auto-detect from run-context'
    )

    if include_replay:
        subparser.add_argument(
            '-r', '--replay',
            action='store_true',
            help='Run deterministic replay scheduler to compute a feasible makespan (T_C) under the chosen heuristic - a counterfactual model, not a claim of scheduling optimality (Part 18)'
        )

        subparser.add_argument(
            '--heuristic',
            type=str,
            choices=['lpt', 'spt', 'fifo', 'depth'],
            default='lpt',
            help='Scheduling heuristic for replay. Options: lpt (Longest Processing Time), spt (Shortest Processing Time), fifo (First In First Out), depth (Dependency Depth). Default: lpt'
        )

    if include_diagnostics:
        subparser.add_argument(
            '--plane2',
            type=str,
            metavar='NATIVE_REPORT.json',
            help='UX-83: a Plane 2 native trace report for THIS SAME run. When '
                 'given, capacity advice is conditioned on what was actually '
                 'measured inside the sandboxes - a RESOURCE WAIT hint will not '
                 'recommend more builders on a host Plane 2 measured as already '
                 'CPU-saturated, and will name an element pinned to -j1 first, '
                 'since that is capacity you already have. Without it every line '
                 'is byte-identical to before.'
        )
        subparser.add_argument(
            '-d', '--diagnostics',
            action='store_true',
            help='Enable advanced diagnostics (blast radius, criticality probability, wall-clock shares). Adds computation time.'
        )

    if include_cold:
        subparser.add_argument(
            '--cold',
            action='store_true',
            help='Enable the advisory cold structural floor (T-infinity,cold, Part 15). Requires --history-dir to produce anything but "unavailable".'
        )

        subparser.add_argument(
            '--allow-partial-cold',
            action='store_true',
            help='With --cold: publish T-infinity,cold as partial=true/confidence=low when some cold-critical-path element has no resolvable historical duration, instead of reporting unavailable. No effect without --cold.'
        )

        subparser.add_argument(
            '--history-dir',
            action='append',
            default=[],
            metavar='PATH',
            help='Path to a prior run directory to use as cold-floor duration history (Part 15.2). Repeatable. Only consulted with --cold.'
        )

    subparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG-level) logging for debugging'
    )

    subparser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress all log output except errors'
    )

    subparser.add_argument(
        '--log-file',
        type=str,
        default=None,
        metavar='PATH',
        help='Also write log output to PATH, independent of console verbosity'
    )


def _tool_help() -> str:
    from .tools_dispatch import format_tool_help
    return format_tool_help()


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser with full inline documentation.

    Implements the full spec Part 37 command list as a hybrid (P1-14):
    `analyze` remains the primary command (full report, every section),
    and `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` are
    thin aliases sharing the same pipeline - each restricts output to
    its own section rather than re-deriving shared pipeline stages
    (ingestion, normalization, graph construction) per subcommand.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='bga',
        description='BuildStream Build Efficiency Analyzer - Analyze build traces for efficiency metrics',
        epilog=(
            # UX-67: the aliases are listed here rather than registered as
            # argparse subcommands, because registering them would import
            # every tool to build the parser - on every `bga analyze`.
            _tool_help() + "\n\n"
            "See docs/guides/cli.md for detailed usage examples and workflows."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
        help='Show program version and exit'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # analyze - primary command, full report (every section)
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Full analysis report (all sections)',
        description='Analyze a directory containing BuildStream run artifacts (run-context/v9, graph/v9, trace/v9) and report every section.',
    )
    _add_common_arguments(analyze_parser, include_replay=True, include_diagnostics=True, include_cold=True)
    analyze_parser.set_defaults(func=cmd_analyze)

    # graph - static dependency graph + critical path + structural metrics
    graph_parser = subparsers.add_parser(
        'graph',
        help='Static dependency graph, critical path, and structural metrics only',
        description='Report the static dependency graph (Part 5), critical path (Part 14.1), and structural metrics (M6).',
    )
    _add_common_arguments(graph_parser)
    graph_parser.add_argument(
        '--by-kind',
        action='store_true',
        help='Also show aggregate stats (count, total/avg observed duration) grouped by BuildStream '
             'element_kind (P4-12, non-spec additive signal - see docs/backlog/tasks/P4-12-element-kind-based-heuristics.md)'
    )
    graph_parser.set_defaults(func=cmd_graph)

    # floors - certified/advisory floors, matches spec's `bga floors RUN --cold` examples
    floors_parser = subparsers.add_parser(
        'floors',
        help='Certified and advisory floors only (T-infinity, LB, certified headroom, cold floor)',
        description='Report certified/advisory floors (Parts 14-17) - matches spec Part 37.1\'s "bga floors RUN [--cold] [--allow-partial-cold]".',
    )
    _add_common_arguments(floors_parser, include_cold=True)
    floors_parser.set_defaults(func=cmd_floors)

    # replay - deterministic replay makespan (T_C)
    replay_parser = subparsers.add_parser(
        'replay',
        help='Deterministic replay makespan (T_C) only',
        description='Run the deterministic replay scheduler (Part 18) and report T_C/model slack only.',
    )
    _add_common_arguments(replay_parser, include_replay=True)
    replay_parser.set_defaults(func=cmd_replay)

    # sweep - capacity sweep (Part 19)
    sweep_parser = subparsers.add_parser(
        'sweep',
        help='Capacity sweep for one resource (Part 19)',
        description='Sweep capacity for one resource across a range and report predicted T_C, normalized improvement, and the knee point.',
    )
    sweep_parser.add_argument(
        'directory', type=str,
        help='Path to the BuildStream run directory'
    )
    sweep_parser.add_argument(
        '--plane2', type=str, metavar='NATIVE_REPORT.json',
        help='UX-83: a Plane 2 native trace report for THIS SAME run. The knee '
             'point is a replay-model answer and the replay model does not know '
             'about CPU; with this, the knee line says how many cores Plane 2 '
             'actually measured busy, and names any element pinned to -j1 - which '
             'is capacity you already have. Without it the output is unchanged.'
    )
    sweep_parser.add_argument(
        '--resource', type=str, default='PROCESS',
        help='Resource to sweep (e.g. PROCESS, DOWNLOAD, UPLOAD). Default: PROCESS'
    )
    sweep_parser.add_argument(
        '--min-capacity', type=int, default=1, metavar='N',
        help='Minimum capacity to test. Default: 1'
    )
    sweep_parser.add_argument(
        '--max-capacity', type=int, default=None, metavar='N',
        help='Maximum capacity to test. Default: number of tasks'
    )
    sweep_parser.add_argument(
        '--step', type=int, default=1, metavar='N',
        help='Increment between tested capacities. Default: 1'
    )
    sweep_parser.add_argument(
        '--calibration-dir', action='append', default=[], metavar='PATH',
        help='UX-14 tier 2: path to a real run directory, captured at a real, different value of the '
             'swept --resource, to use as contention-aware duration calibration. Repeatable - give 2+ '
             'for any interpolation to be possible. Real per-task durations are interpolated (never '
             'extrapolated) between calibrated capacities; tasks with fewer than 2 calibration points '
             'keep their own fixed, tier-1 duration unchanged.'
    )
    sweep_parser.add_argument(
        '-f', '--format', type=str, choices=['text', 'json'], default='text',
        help='Output format: text (human-readable), json (machine-readable). Default: text'
    )
    sweep_parser.add_argument('-o', '--output', type=str, help='Write output to file instead of stdout')
    sweep_parser.add_argument(
        '-c', '--capacity', type=int, default=None, metavar='N',
        help='Override system resource capacity for resources not being swept. Default: auto-detect from run-context'
    )
    sweep_parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose (DEBUG-level) logging for debugging')
    sweep_parser.add_argument('-q', '--quiet', action='store_true', help='Suppress all log output except errors')
    sweep_parser.add_argument('--log-file', type=str, default=None, metavar='PATH', help='Also write log output to PATH, independent of console verbosity')
    sweep_parser.set_defaults(func=cmd_sweep)

    # utilisation - CPU utilisation accounting
    utilisation_parser = subparsers.add_parser(
        'utilisation',
        help='CPU utilisation accounting only',
        description='Report CPU utilisation accounting (Part 30, M4) only.',
    )
    _add_common_arguments(utilisation_parser)
    utilisation_parser.set_defaults(func=cmd_utilisation)

    # diagnostics - advanced diagnostics
    diagnostics_parser = subparsers.add_parser(
        'diagnostics',
        help='Advanced diagnostics only (blast radius, criticality probability, wall-clock shares)',
        description='Report advanced diagnostics (Parts 20-29, M5) only.',
    )
    _add_common_arguments(diagnostics_parser)
    diagnostics_parser.set_defaults(func=cmd_diagnostics)

    # compare - run-to-run comparison (UX-01, non-spec additive command)
    correlate_parser = subparsers.add_parser(
        'correlate',
        help="Join a Plane 1 run with a Plane 2 native trace report and say what to fix",
        description='Join this run\'s whole-project analysis with a native (Plane 2) trace report '
                    'of the same build, on element UID. Answers what neither plane can alone: '
                    'whether the elements dominating the critical path are genuinely compute-bound '
                    'or just badly parallelized (docs/backlog/scenarios/UX-51 - not spec-mandated).',
    )
    # `directory` (Plane 1) comes from _add_common_arguments; only the
    # Plane 2 artifact is specific to this command.
    _add_common_arguments(correlate_parser)
    # UX-88: `correlate` inherits `-f csv` from the shared argument set
    # and had no csv renderer, so it accepted the flag and silently
    # printed text. Narrowed to what it can actually produce - a
    # rejected flag is a better answer than a format that is not the one
    # asked for. (`analyze`'s csv, which is an attribution table, has no
    # meaning for a two-plane join.)
    correlate_parser.set_defaults(format='text')
    for action in correlate_parser._actions:
        if action.dest == 'format':
            action.choices = ['text', 'json']
            action.help = (
                'Output format: text (human-readable), json (machine-readable). '
                'Default: text. No csv - the join has no tabular form.'
            )
    correlate_parser.add_argument(
        '--cache-logs', default=None, metavar='PATH',
        help="A Plane 3 report (`bga cache-logs --format json`) for the same "
             "project. Supplies the per-element sandbox toll, which is what the "
             "merge half of the granularity findings is computed from (UX-100).",
    )
    correlate_parser.add_argument(
        'native_report', type=str,
        help='Path to the JSON report written by `tools/bst_native_build_tracer.py run` (Plane 2). '
             'Capture both from one build with `run --wrapped-log`.',
    )
    correlate_parser.set_defaults(func=cmd_correlate)

    cache_trend_parser = subparsers.add_parser(
        'cache-trend',
        help="Is the cache getting worse? A series of runs, not a pair",
        description='Read a chronological series of run directories and report the '
                    'cache reading of each - hit ratio, transfer seconds, churn '
                    'against its predecessor - plus a finding when the newest run '
                    'leaves the band its trailing window describes '
                    '(docs/backlog/scenarios/UX-0103 - not spec-mandated). In CI the '
                    'series comes from `bga baseline`. The noise model is the one '
                    '`bga compare --baseline-run` uses; there is deliberately not a '
                    'second one.',
    )
    cache_trend_parser.add_argument(
        'run_dirs', nargs='+', metavar='RUN',
        help='Run directories, oldest first. Order is the caller\'s to know: '
             'nothing in a run directory records which build came before it.',
    )
    cache_trend_parser.add_argument(
        '-f', '--format', choices=['text', 'json'], default='text',
        help='Output format: text (human-readable), json (machine-readable). '
             'Default: text',
    )
    cache_trend_parser.add_argument(
        '-o', '--output', default=None, help='Write output to file instead of stdout',
    )
    cache_trend_parser.set_defaults(func=cmd_cache_trend)

    compare_parser = subparsers.add_parser(
        'compare',
        help='Compare two runs (baseline vs. candidate) and report deltas plus a verdict',
        description='Compare a baseline run against a candidate run: signed deltas in certified floors, '
                    'efficiency score, and attribution, plus an improved/regressed/no-significant-change '
                    'verdict gated on confidence and graph comparability (docs/backlog/scenarios/UX-01 - not spec-mandated).',
    )
    compare_parser.add_argument('baseline', type=str, help='Path to the baseline (before) run directory')
    compare_parser.add_argument('candidate', type=str, help='Path to the candidate (after) run directory')
    compare_parser.add_argument(
        '-f', '--format', type=str, choices=['text', 'json'], default='text',
        help='Output format: text (human-readable), json (machine-readable). Default: text'
    )
    compare_parser.add_argument('-o', '--output', type=str, help='Write output to file instead of stdout')
    compare_parser.add_argument(
        '-c', '--capacity', type=int, default=None, metavar='N',
        help='Override system resource capacity for both runs (applied symmetrically). Default: auto-detect per run'
    )
    compare_parser.add_argument(
        '--fail-on-inefficient-additions', action='store_true',
        help=f'UX-79: CI gate on the efficiency of the *change*, not of the repository. '
        f'Exits {EXIT_CODE_EFFICIENCY_REGRESSION} when more than --max-addition-stretch '
        f'of the work this change added landed on the critical path. Unlike '
        f'--fail-on-efficiency-regression, which reads a whole-build average and so '
        f'gets weaker as the project grows, this mentions only the added elements: '
        f'measured on fixtures, two maximally-mis-added elements move whole-build '
        f'occupancy -14.6pp in an 11-element project and -0.5pp in a 1201-element one '
        f'(passing the 5.0pp default), while their stretch is 1.00 in both.'
    )
    compare_parser.add_argument(
        '--max-addition-stretch', type=float, default=DEFAULT_MAX_ADDITION_STRETCH,
        metavar='RATIO',
        help=f'UX-79: the share of added work that may land on the critical path '
        f'before --fail-on-inefficient-additions fires. 0.0 means the additions were '
        f'fully absorbed by existing parallelism; 1.0 means every second of added work '
        f'extended the chain. Default: {DEFAULT_MAX_ADDITION_STRETCH} - "at most half '
        f'of what you added may land on the chain", sitting in the measured gap between '
        f'a well-added set (0.00) and a serialized one (1.00).'
    )
    compare_parser.add_argument(
        '--allow-mismatch', action='store_true',
        help=f'UX-78: compare anyway when the two runs fail a comparability check '
        f'(they share less than half their element UIDs, or one is a caches-off run '
        f'and the other incremental). Without this, such a pair is refused with exit '
        f'{EXIT_CODE_MISMATCHED_RUNS} - distinct from the gates\' 4/5, so a CI job '
        f'cannot mistake a wrong-artifact-path bug for a regression. With it, the '
        f'warning and the comparison are both printed, which is what happened before.'
    )
    compare_parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose (DEBUG-level) logging for debugging')
    compare_parser.add_argument('-q', '--quiet', action='store_true', help='Suppress all log output except errors')
    compare_parser.add_argument('--log-file', type=str, default=None, metavar='PATH', help='Also write log output to PATH, independent of console verbosity')
    compare_parser.add_argument(
        '--fail-on-regression', action='store_true',
        help=f'CI gate (UX-03): exit {EXIT_CODE_REGRESSION} (distinct from 1/2/3, which mean bga itself '
        'failed) if the candidate run regressed in total duration beyond the threshold (see '
        '--regression-threshold). A low-confidence comparison fails open (exit 0 with a warning) '
        'rather than block a pipeline on a possibly-noisy signal (see --fail-on-low-confidence). '
        'Default: off (bga compare always exits 0 regardless of verdict).'
    )
    compare_parser.add_argument(
        '--fail-on-efficiency-regression', action='store_true',
        help=f'CI gate (UX-39): exit {EXIT_CODE_EFFICIENCY_REGRESSION} (distinct from '
        f'{EXIT_CODE_REGRESSION}, "the build got slower") if the candidate run\'s dispatch '
        'occupancy fell more than --max-efficiency-drop percentage points below the '
        'baseline\'s. Occupancy is invariant to how much work the build does, so this '
        'answers "was new work added efficiently", which wall-clock cannot: adding '
        'well-parallelized elements barely moves it, adding serialized ones moves it '
        'sharply. Default: off.'
    )
    compare_parser.add_argument(
        '--max-efficiency-drop', type=float, default=None, metavar='PP',
        help=f'With --fail-on-efficiency-regression: how many percentage points of dispatch '
        f'occupancy may be lost before failing. Default: {_EFFICIENCY_DROP_PP}pp, derived from '
        'three repeat captures of an unchanged project on one real runner (1.0pp of observed '
        'noise) - re-derive it the same way on your own runner rather than trusting it.'
    )
    compare_parser.add_argument(
        '--min-efficiency', type=float, default=None, metavar='RATIO',
        help=f'CI gate (UX-39): exit {EXIT_CODE_EFFICIENCY_REGRESSION} if the candidate run\'s '
        'dispatch occupancy is below this absolute floor (0.0-1.0, e.g. 0.45). Independent of '
        'any baseline - which makes it usable on a first run, and stops a slow drift that no '
        'single delta ever trips. No default: what counts as acceptable is a statement about '
        'your project, not a universal constant.'
    )
    compare_parser.add_argument(
        '--require-efficiency-signal', action='store_true',
        help=f'UX-87: with either efficiency gate, exit {EXIT_CODE_SIGNAL_UNAVAILABLE} if a run '
        'has no `occupancy_ratio` and the gate therefore could not be evaluated. Without this, '
        'the gate fails open (exit 0) but says so on stderr and publishes '
        '`efficiency_gate_evaluated: false` in --format json. For pipelines that would rather '
        'break than silently stop gating.'
    )
    compare_parser.add_argument(
        '--baseline-run', action='append', metavar='PATH',
        help='UX-59: an additional run directory forming the baseline *set*. '
             'Repeatable. With at least {} of them, the no-significant-change '
             'band is derived from their measured spread (median +- k*1.4826*MAD) '
             'instead of a fixed percentage. Seven repeated builds of one '
             'unchanged commit put 4 of 7 outside the fixed 1%% rule. All runs '
             'must share the candidate run_mode (UX-55).'.format(MIN_BASELINE_RUNS),
    )
    compare_parser.add_argument(
        '--band-k', type=float, default=DEFAULT_BAND_K, metavar='K',
        help='Width of the --baseline-run noise band in scaled-MAD units '
             '(default: {}).'.format(DEFAULT_BAND_K),
    )
    # UX-104 item 2: a memory *note*, not a gate. Two flags rather than
    # one because the envelope is a fact about a run and the two runs are
    # independent captures - inferring the baseline's Plane 2 report from
    # the candidate's would be comparing a run against itself.
    compare_parser.add_argument(
        '--baseline-plane2', default=None, metavar='PATH',
        help='UX-104: the baseline run\'s Plane 2 report (`bga capture run`\'s JSON). '
             'With --candidate-plane2, compare notes when the candidate\'s measured '
             'memory envelope grew. A note, never a gate: there is no noise band for '
             'peak RSS yet.',
    )
    compare_parser.add_argument(
        '--candidate-plane2', default=None, metavar='PATH',
        help='UX-104: the candidate run\'s Plane 2 report. See --baseline-plane2.',
    )
    compare_parser.add_argument(
        '--fail-on-low-confidence', action='store_true',
        help=f'CI gate (UX-40): with --fail-on-regression, exit {EXIT_CODE_REGRESSION} when a run\'s '
        'confidence is too low to gate on, instead of failing open. A gate that silently stops '
        'gating reports green while checking nothing; this makes that state a failure a pipeline '
        'can see. Default: off (fail open, with a warning on stderr).'
    )
    compare_parser.add_argument(
        '--regression-threshold', type=float, default=None, metavar='PCT',
        help='Percentage-point threshold for --fail-on-regression (default: the same significance '
        'band bga compare\'s own verdict already uses - i.e. gate on exactly what the report calls '
        'REGRESSED). Only relevant together with --fail-on-regression.'
    )
    compare_parser.set_defaults(func=cmd_compare)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """
    Main entry point for the bga CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code
    """
    # UX-67: one entry point for the whole workflow. Checked before
    # argparse, because a tool's own arguments are its business - `bga
    # extract . build.log run/ --format wrapped` must reach
    # `bst_extract_run` untouched, and letting this parser see them first
    # would mean teaching it every tool's flags.
    from .tools_dispatch import dispatch
    tool_exit = dispatch(list(sys.argv[1:] if argv is None else argv))
    if tool_exit is not None:
        return tool_exit

    parser = create_parser()
    args = parser.parse_args(argv)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
