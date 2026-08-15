#!/usr/bin/env python3
"""
BuildStream Build Efficiency Analyzer (bga) - Command Line Interface

This module provides the CLI entry point for analyzing BuildStream build traces.
It implements all commands documented in docs/cli.md.

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
from typing import Optional

from . import __version__
from .analyzer import BuildEfficiencyAnalyzer
from .compare import compare_runs, regression_exceeds_threshold
from .exceptions import AnalysisError, IngestionError
from .ingest.loader import load_historical_runs
from .logging_config import configure_logging
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
    result = analyzer.analyze(run_dir)
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

    sweep_result = analyzer.replay_scheduler.capacity_sweep(
        resource=args.resource,
        min_capacity=args.min_capacity,
        max_capacity=args.max_capacity,
        step=args.step,
    )

    if args.format == 'json':
        return json.dumps({
            'resource': args.resource,
            'sweeps': sweep_result.sweeps,
            'knee_points': sweep_result.knee_points,
            'monotonicity_violations': sweep_result.monotonicity_violations,
            'capacity_model_caveat': SWEEP_CAPACITY_MODEL_CAVEAT,
        }, indent=2, default=str)
    return format_sweep_text(args.resource, sweep_result)


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
        capacity=args.capacity, verbose=args.verbose,
    )
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

    missing = []
    if not graph_present:
        missing.append(("graph.json", "tools/bst_show_to_graph.py <project_dir> <targets...> graph.json"))
    if not trace_present:
        missing.append(("trace.json", "tools/bst_log_to_chrome_trace.py + tools/chrome_trace_to_bga_trace.py <log>"))
    if not run_context_present:
        missing.append(("run-context.json", "tools/bst_run_context.py <log> run-context.json"))
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
        "  (or run tools/bst_extract_run.py to produce all three from one "
        "project + log in a single step - see docs/ingestion-pipeline.md)",
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
        # "missing files" precondition problem (docs/cli.md exit code 1),
        # distinct from malformed *content* in a file that does exist
        # (exit code 2, handled below).
        logger.error("Required input file not found: %s", e)
        print(f"Error: Required input file not found - {e}", file=sys.stderr)
        _print_missing_input_hint(run_dir)
        return 1
    except AnalysisError as e:
        # Graph cycles and other analysis-pipeline failures - exit code 3
        # per docs/cli.md. Checked by type, not by string-matching the
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


def _compare_exit_code(args: argparse.Namespace, comparison) -> int:
    """UX-03's CI regression gate: only active when --fail-on-regression
    is passed (bga compare's default behavior - matching UX-01's own
    design note - stays "always exit 0 regardless of verdict", since
    comparing is not itself a failure condition). A low-confidence
    comparison fails open (exits 0 with a visible warning) rather than
    block a pipeline on a possibly-noisy signal - the same reasoning
    _CONFIDENCE_HIGH already gates comparison.low_confidence on."""
    if not getattr(args, 'fail_on_regression', False):
        return 0

    if comparison.low_confidence:
        print(
            "Warning: --fail-on-regression not applied - at least one run's "
            "confidence is below the 'high' band, so this comparison is not "
            "reliable enough to gate a pipeline on (failing open, exit 0). "
            "See docs/scenarios/UX-03-ci-regression-gate.md.",
            file=sys.stderr,
        )
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
    otherwise identical (same exit-code contract, docs/cli.md)."""
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
        epilog='See docs/cli.md for detailed usage examples and workflows.',
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
             'element_kind (P4-12, non-spec additive signal - see docs/tasks/P4-12-element-kind-based-heuristics.md)'
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
    compare_parser = subparsers.add_parser(
        'compare',
        help='Compare two runs (baseline vs. candidate) and report deltas plus a verdict',
        description='Compare a baseline run against a candidate run: signed deltas in certified floors, '
                    'efficiency score, and attribution, plus an improved/regressed/no-significant-change '
                    'verdict gated on confidence and graph comparability (docs/scenarios/UX-01 - not spec-mandated).',
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
    compare_parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose (DEBUG-level) logging for debugging')
    compare_parser.add_argument('-q', '--quiet', action='store_true', help='Suppress all log output except errors')
    compare_parser.add_argument('--log-file', type=str, default=None, metavar='PATH', help='Also write log output to PATH, independent of console verbosity')
    compare_parser.add_argument(
        '--fail-on-regression', action='store_true',
        help=f'CI gate (UX-03): exit {EXIT_CODE_REGRESSION} (distinct from 1/2/3, which mean bga itself '
        'failed) if the candidate run regressed in total duration beyond the threshold (see '
        '--regression-threshold). A low-confidence comparison fails open (exit 0 with a warning) '
        'rather than block a pipeline on a possibly-noisy signal. Default: off (bga compare always '
        'exits 0 regardless of verdict).'
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
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
