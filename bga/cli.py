#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
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

from . import __version__, schemas
from .analyzer import (
    MODELLED_AXIS_CLAUSE, UNMODELED_AXIS_CLAUSE, BuildEfficiencyAnalyzer,
)
from .help_format import CompactHelp
from .compare import (
    _EFFICIENCY_DROP_PP, DEFAULT_BAND_K, DEFAULT_MAX_ADDITION_STRETCH,
    RunsNotComparableError,
    compare_runs,
    efficiency_below_floor,
    efficiency_regression_exceeds_threshold, efficiency_signal_status,
    regression_exceeds_threshold,
)
from .exceptions import AnalysisError, IngestionError
from .ingest.loader import load_historical_runs
from .logging_config import configure_logging
from .replay.scheduler import build_contention_calibration
from .run_store import (
    StoreError,
    resolve as resolve_run_alias,
    resolve_plane2 as resolve_plane2_alias,
    sibling_plane2,
)
from .report.ci_comment import render_ci_comment
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


def _attach_resource_blast(run_dir, analyzer, result) -> None:
    """UX-171: the resource blast table, when the run carries an inventory.

    `sources.json` is written by `bga extract`, which is the one moment
    the project directory and the run are both in hand. A run captured
    before UX-171 - or one extracted from a log without its project -
    simply has none, and the section is absent rather than empty.
    """
    from bga import sources as sources_module
    from bga.graph.edg import compute_reachability

    inventory = sources_module.load_inventory(Path(run_dir) / 'sources.json')
    if not inventory:
        return
    graph = getattr(analyzer, 'graph', None)
    if graph is None:
        return
    downstream, _upstream = compute_reachability(graph)
    element_kinds = {e.uid: (e.element_kind or 'unknown') for e in graph.elements}
    # UX-53's single per-element duration definition, in seconds. Summed
    # across a blast set this is *work*, not wall clock - the report
    # says so where it prints it.
    from bga.graph.edg import compute_element_durations
    durations = {
        uid: micros / 1e6
        for uid, micros in compute_element_durations(
            getattr(analyzer, 'normalized_tasks', []) or []).items()
    }
    rows = sources_module.resource_blast(
        inventory, downstream, element_kinds, durations)
    result.resource_blast = {
        'rows': rows,
        'element_count': len(graph.elements),
        'headline': sources_module.monorepo_headline(rows, len(graph.elements)),
        'unreadable': inventory.get('unreadable') or {},
    }


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
    # UX-202: how much of the build Plane 2 actually saw, published
    # rather than left in the native report. The evidence header states
    # what a capture can support before any number is believed, and
    # "813 processes, opens coverage 1.00" is the Plane 2 half of that
    # answer; without it the page would have to read a second document
    # or, worse, imply full coverage by saying nothing.
    result.plane2_coverage = native_report.get('stream_coverage') or None
    # UX-215: the report keeps the Plane 2 report itself, so the JSON
    # renderer can publish the per-element join from the same function
    # `bga correlate` calls. Held rather than joined here because the
    # join reads the finished analysis document, which does not exist
    # yet at this point in the pipeline.
    result.plane2_report = native_report
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
    # UX-116: and the sentence that intersects them. Every constraint on
    # the joint (builders x max-jobs) choice is now a measured number in
    # this one capture; what was missing was the intersection. Run only
    # here, because the knee costs a capacity sweep and the whole block
    # is gated on Plane 2 being in hand anyway.
    result.capacity_recommendation = _capacity_recommendation(
        analyzer, result, context)
    if result.capacity_recommendation:
        # UX-116 item 3: the "currently unmodeled axis" note is retired
        # *only* where the block ran. Elsewhere it stays, because
        # elsewhere it is still true - and the substitution is on a named
        # constant rather than a re-typed sentence, so the two cannot
        # drift into disagreeing about which clause is being retired.
        note = (result.floors or {}).get('capacity_model_note') or ''
        if UNMODELED_AXIS_CLAUSE in note:
            result.floors['capacity_model_note'] = note.replace(
                UNMODELED_AXIS_CLAUSE, MODELLED_AXIS_CLAUSE, 1)


def _capacity_recommendation(analyzer, result, context) -> dict:
    """UX-116: the knee, the CPU draw, the memory ceiling and the host,
    intersected.

    The sweep is bounded rather than run to its default of one
    configuration per task: this question is about what is settable on
    this host, and a 1200-element project would otherwise pay 1200
    replays to answer it. `knee_range_top` is passed through so the
    recommendation can say "at least" when the knee lands at the ceiling
    of what was swept instead of asserting a number it did not reach.
    """
    from bga.correlate import (
        _RECOMMENDATION_SWEEP_CAP, _RECOMMENDATION_SWEEP_HEADROOM,
        compute_capacity_recommendation,
    )

    plane2 = getattr(result, 'plane2_capacity', None) or {}
    builders = getattr(context, 'max_jobs', None)
    host_cores = plane2.get('host_cpu_count')
    if not plane2.get('cores_busy') or not host_cores or not builders:
        return {}

    top = min(
        max(builders, host_cores) * _RECOMMENDATION_SWEEP_HEADROOM,
        _RECOMMENDATION_SWEEP_CAP,
    )
    try:
        sweep = analyzer.replay_scheduler.capacity_sweep(
            resource='PROCESS', min_capacity=1, max_capacity=top, step=1,
        )
    except (AttributeError, ValueError) as exc:
        logger.info("UX-116: no capacity sweep available (%s)", exc)
        return {}

    return compute_capacity_recommendation(
        plane2,
        getattr(result, 'memory_envelope', None) or {},
        knee=(sweep.knee_points or {}).get('PROCESS'),
        knee_range_top=top,
        builders=builders,
        native_max_jobs=getattr(context, 'native_max_jobs', None),
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
    _attach_resource_blast(run_dir, analyzer, result)
    by_kind = getattr(args, 'by_kind', False)

    if args.format == 'json':
        # UX-187: the caps are a *text-rendering* concern. The machine
        # format never truncates - a consumer that asked for JSON asked
        # for all of it, and there is a guard.
        return format_json(result, section=section, by_kind=by_kind)
    elif args.format == 'csv':
        return format_csv(result)
    return format_text(result, section=section, by_kind=by_kind,
                       full_sections=_full_sections(args),
                       explain=getattr(args, 'explain', False))


# UX-187: which long sections a `--full-*` flag un-caps, by the name the
# renderer keys on.
_FULL_SECTION_FLAGS = {
    "full_path": "path",
    "full_sources": "sources",
}


def _full_sections(args: argparse.Namespace) -> frozenset:
    return frozenset(
        name for attribute, name in _FULL_SECTION_FLAGS.items()
        if getattr(args, attribute, False)
    )


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
        output = json.dumps(schemas.stamp(comparison.to_dict(), schemas.COMPARE),
                            indent=2, default=str)
    elif args.format == 'ci-comment':
        # UX-115: render-only. Everything it prints was computed above;
        # the gate verdicts come from the same predicates
        # `_compare_exit_code` calls, so the comment and the exit code
        # cannot disagree.
        output = render_ci_comment(
            comparison, args,
            native_report=_load_native_report(getattr(args, 'native_report', None)),
        )
    else:
        output = format_compare_text(comparison)
    return output, comparison


def _load_native_report(path: Optional[str]) -> Optional[dict]:
    """The candidate run's Plane 2 report, when the caller has one.

    Absent is a first-class answer, not an error: most projects have no
    Plane 2 capture, and the comment says the never-read column is
    *missing* rather than printing an empty one (UX-115).
    """
    if not path:
        return None
    with open(path) as handle:
        return json.load(handle)


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
        # UX-156: exit 6, not 4. `UX-54` made this fail closed, which was
        # right, but it borrowed "your build got slower" to say it - and
        # a build that did not finish has not been measured at all, which
        # is exactly what `EXIT_CODE_MISMATCHED_RUNS` already means. A
        # pipeline that blocks on 4 and investigates 6 was being told the
        # wrong one.
        detail = comparison.failed_run_details or []
        named = "; ".join(
            f"{d['run']}: {', '.join(d['failed_elements'][:3]) or 'unnamed element'}"
            + (f" ({d['built']} of {d['scheduled']} scheduled elements built)"
               if d['scheduled'] is not None else "")
            for d in detail
        ) or " and ".join(comparison.failed_runs)
        print(
            f"Build failure gate FAILED: {named}. That build did not complete, "
            "so no scheduling verdict is meaningful for it - this is a refusal "
            "to compare, not a regression, and fails closed rather than open. "
            "See docs/backlog/scenarios/UX-0054-a-failed-build-scores-perfectly.md.",
            file=sys.stderr,
        )
        return EXIT_CODE_MISMATCHED_RUNS

    # UX-186: also before the low-confidence fail-open, and also failing
    # *closed*. Two machines' durations are not one measurement, and
    # unlike a noisy signal that is not a matter of degree - so this is a
    # refusal (exit 6, the not-comparable code) rather than a regression.
    # The comparison itself still printed, with its caveat: looking is
    # fine, gating is not.
    host_comparison = getattr(comparison, 'host_comparison', None) or {}
    if (host_comparison.get('status') == 'different'
            and not getattr(args, 'allow_cross_host', False)):
        differing = ", ".join(host_comparison.get('differing') or []) or "host"
        print(
            f"Cross-host gate FAILED: baseline and candidate were measured on "
            f"different machines ({differing}). Run-to-run noise on one machine "
            f"already reaches 33% (UX-92); across machines the difference between "
            f"the two runs is not evidence about the change. Pass "
            f"--allow-cross-host if your runners are uniform and you accept that.",
            file=sys.stderr,
        )
        return EXIT_CODE_MISMATCHED_RUNS

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
    except RunsNotComparableError as e:
        # UX-114: before the generic ValueError handler, because a band
        # that refused a run is the same verdict `--allow-mismatch`
        # guards above and must carry the same code.
        logger.error("Not comparable: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_CODE_MISMATCHED_RUNS
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


def cmd_blast(args: argparse.Namespace) -> int:
    """Execute `bga blast TARGET` (UX-172) - what rebuilds if I touch this.

    A question rather than a gate, so it exits 0 on an answer of zero
    just as it does on an answer of two hundred. The refusal grammar
    lives in `compare`, where a gate belongs.
    """
    from bga.blast import blast, format_blast_json, format_blast_text

    from bga.run_store import project_root

    try:
        run_dir = resolve_run_alias(args.run)
    except StoreError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    if not Path(run_dir).is_dir():
        print(f"Error: not a run directory: {run_dir}", file=sys.stderr)
        return 2
    project = args.project or project_root() or "."
    try:
        answer = blast(run_dir, args.target, project_dir=project,
                       measure=not getattr(args, 'no_cost', False))
    except (FileNotFoundError, ValueError) as error:
        # UX-178: an existing directory that is not a run - the likeliest
        # slip is `<snapshot>/` where `<snapshot>/run` was meant - used to
        # be a raw traceback, while `analyze` on the same directory prints
        # a sentence. Same treatment, and the exit code UX-172 documented.
        print(f"Error: {run_dir} is not a run directory ({error}). "
              f"A snapshot's run directory is `<snapshot>/run`.", file=sys.stderr)
        return 2
    output = (format_blast_json(answer) if args.format == 'json'
              else format_blast_text(answer))
    if getattr(args, 'output', None):
        with open(args.output, 'w', encoding='utf-8') as handle:
            handle.write(output + "\n")
    else:
        print(output)
    return 0


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

    if args.native_report is None:
        # UX-134: inferred from what is on disk, never from how the run
        # directory was spelled - so `@last` and the full path it
        # resolves to behave identically.
        args.native_report = sibling_plane2(args.directory)
        if args.native_report is None:
            print(
                f"Error: no Plane 2 report given, and none beside "
                f"{args.directory}. Pass one, or point this at a snapshot "
                f"(`bga correlate @last`), which keeps the run and its report "
                f"together.",
                file=sys.stderr,
            )
            return 2
        print(f"Plane 2: {args.native_report}", file=sys.stderr)

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
            # UX-215: stamped, so the document says what it is - the
            # same treatment the other four outputs have had since
            # UX-190, and what makes `bga view` able to serve it.
            return json.dumps(schemas.stamp(joined, schemas.CORRELATE),
                              indent=2)
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
        help='Path to the BuildStream run directory (e.g., ~/.buildstream/cache/artifacts/run-<uuid>).'
    )
    # UX-187: the long sections are folded in the middle by default. The
    # flags are on every analyze-shaped command because the sections are:
    # `bga graph` renders the critical path too.
    subparser.add_argument(
        '--full-path', action='store_true',
        help='Print every element of the critical path, not just its two ends.'
    )
    subparser.add_argument(
        '--full-sources', action='store_true',
        help='Print every shared-source row, not just the widest.'
    )
    # UX-229: the chain behind each claim, on demand. Off by default
    # because the report is a decision and the chain is what a reader
    # asks for after doubting one - the same reason `--diagnostics` is
    # opt-in.
    subparser.add_argument(
        '--explain', action='store_true',
        help='Under each claim, print its evidence fields, the rule that fired '
             'and the query that deepens it.'
    )

    subparser.add_argument(
        '-f', '--format',
        type=str,
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format: text (human-readable), json (machine-readable), csv (attribution data). Default: text.'
    )

    subparser.add_argument(
        '-o', '--output',
        type=str,
        help='Write output to PATH instead of stdout.'
    )

    subparser.add_argument(
        '-c', '--capacity',
        type=int,
        default=None,
        metavar='N',
        help='Override system resource capacity (affects LB and replay calculations). Default: auto-detect from run-context.'
    )

    if include_replay:
        subparser.add_argument(
            '-r', '--replay',
            action='store_true',
            help='Replay the run under the chosen heuristic for a feasible makespan (T_C). A counterfactual model, not a claim of optimality.'
        )

        subparser.add_argument(
            '--heuristic',
            type=str,
            choices=['lpt', 'spt', 'fifo', 'depth'],
            default='lpt',
            help='Scheduling heuristic for replay. Options: lpt (Longest Processing Time), spt (Shortest Processing Time), fifo (First In First Out), depth (Dependency Depth). Default: lpt.'
        )

    if include_diagnostics:
        subparser.add_argument(
            '--plane2',
            type=str,
            metavar='NATIVE_REPORT.json',
            help='Plane 2 report for this same run: capacity advice is then\n'
                 'conditioned on what the sandboxes actually measured.'
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
            help='With --cold: publish a partial, low-confidence cold floor when an element on the cold path has no historical duration, rather than none at all.'
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
        help='Verbose (DEBUG) logging.'
    )

    subparser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Errors only.'
    )

    subparser.add_argument(
        '--log-file',
        type=str,
        default=None,
        metavar='PATH',
        help='Also write logs to PATH.'
    )


class _CompactSubParser(argparse.ArgumentParser):
    """A subparser that inherits the compact help layout without every
    `add_parser` call having to remember to pass it (`UX-158`)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", CompactHelp)
        super().__init__(*args, **kwargs)


def _tool_help() -> str:
    from .tools_dispatch import format_tool_help
    return format_tool_help()


def _snapshot_completer(prefix, parsed_args, **_kwargs):
    """`@last`, `@prev`, and this project's own snapshot stamps.

    The completion the feedback actually named: *"it will greatly
    improve UX on commands like bga cache-trend"*, where the argument is
    a run and the useful answers are the aliases plus what the store
    holds. Best-effort by construction - a completer that raises leaves
    the user with a dead TAB, so anything unreadable answers nothing.
    """
    try:
        from . import run_store

        project = run_store.project_root()
        if project is None:
            return [alias for alias in ("@last", "@prev")
                    if alias.startswith(prefix)]
        # `os.path.basename` via `Path`: this module does not import
        # `os`, and reaching for it here failed silently inside the
        # broad `except` below - the exact dead-TAB-with-no-explanation
        # this completer's own docstring warns about.
        stamps = ["@" + Path(snapshot).name
                  for snapshot in run_store.list_runs(project)]
        return [candidate for candidate in ["@last", "@prev"] + stamps
                if candidate.startswith(prefix)]
    except Exception:  # noqa: BLE001 - a dead TAB is worse than no answer
        return []


def _element_completer(prefix, parsed_args, **_kwargs):
    """Element names, for `bga blast`, from the project's own files."""
    try:
        from .tools_dispatch import TOOL_ALIASES  # noqa: F401  (import guard)
        from tools.bst_native_build_tracer import discover_element_names

        project = getattr(parsed_args, "project", None)
        if project is None:
            from . import run_store
            project = run_store.project_root()
        if project is None:
            return []
        return [name for name in discover_element_names(project)
                if name.startswith(prefix)]
    except Exception:  # noqa: BLE001
        return []


def _attach_run_completers(parser) -> None:
    """Give every run-shaped argument the `@`-alias completer.

    Driven off `_RUN_DIRECTORY_ARGS`/`_RUN_DIRECTORY_LIST_ARGS`/
    `_PLANE2_ARGS` - the same three lists `_resolve_run_aliases` uses -
    so an argument that learns to take an alias gets completion for it
    without a second edit, and the two cannot disagree about which
    arguments those are.
    """
    completable = set(_RUN_DIRECTORY_ARGS) | set(_RUN_DIRECTORY_LIST_ARGS) \
        | set(_PLANE2_ARGS) | {"run"}
    for action in parser._actions:
        if getattr(action, "choices", None) and hasattr(action.choices, "keys"):
            for subparser in action.choices.values():
                if subparser is not None:
                    _attach_run_completers(subparser)
        elif action.dest in completable:
            action.completer = _snapshot_completer
        elif action.dest == "target":
            # `bga blast TARGET` - a url, a path or an element name. The
            # first two have no source of truth to complete from; the
            # third does.
            action.completer = _element_completer


def _command_completer(prefix, parsed_args, **_kwargs):
    """Every name `bga` dispatches: subcommands *and* the aliases.

    The `UX-67` aliases are not argparse subparsers - registering them
    would import every tool to build the parser, on every `bga analyze`,
    which is the cost that design deliberately avoids. So completion
    reads `TOOL_ALIASES` directly and offers both sets, because a user
    types `bga wrap` exactly as often as `bga analyze` and a completion
    that omitted half the tool would be worse than none.
    """
    try:
        from .tools_dispatch import TOOL_ALIASES

        names = set(TOOL_ALIASES)
        for action in create_parser()._actions:
            if getattr(action, "choices", None) and hasattr(action.choices, "keys"):
                names |= set(action.choices)
        return sorted(name for name in names if name.startswith(prefix))
    except Exception:  # noqa: BLE001 - a dead TAB is worse than no answer
        return []


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

    subparsers = parser.add_subparsers(
        dest='command', metavar='COMMAND', help='Available commands',
        parser_class=_CompactSubParser)
    # UX-191: completion offers the aliases too - see
    # `_command_completer`. Attached rather than registered, so the
    # parser stays exactly as cheap to build as it was.
    subparsers.completer = _command_completer

    # analyze - primary command, full report (every section)
    analyze_parser = subparsers.add_parser(
        'analyze',
        usage='bga analyze [options] RUN_DIR',
        help='Full analysis report.',
        description='Analyze a directory containing BuildStream run artifacts (run-context/v9, graph/v9, trace/v9) and report every section.',
    )
    _add_common_arguments(analyze_parser, include_replay=True, include_diagnostics=True, include_cold=True)
    analyze_parser.set_defaults(func=cmd_analyze)

    # graph - static dependency graph + critical path + structural metrics
    graph_parser = subparsers.add_parser(
        'graph',
        help='Dependency graph, critical path, structural metrics.',
        description='Report the static dependency graph (Part 5), critical path (Part 14.1), and structural metrics (M6).',
    )
    _add_common_arguments(graph_parser)
    graph_parser.add_argument(
        '--by-kind',
        action='store_true',
        help='Also show per-kind aggregate stats (count, total and average\n'
             'observed duration), grouped by BuildStream element kind.'
    )
    graph_parser.set_defaults(func=cmd_graph)

    # floors - certified/advisory floors, matches spec's `bga floors RUN --cold` examples
    floors_parser = subparsers.add_parser(
        'floors',
        help='Certified and advisory floors only.',
        # UX-220: what a floor *is* comes from the schema, so `--help`
        # and the report cannot end up explaining it two ways.
        description='Report certified/advisory floors (Parts 14-17) - matches spec Part 37.1\'s "bga floors RUN [--cold] [--allow-partial-cold]". '
                    + schemas.description(schemas.ANALYZE, 'floors'),
    )
    _add_common_arguments(floors_parser, include_cold=True)
    floors_parser.set_defaults(func=cmd_floors)

    # replay - deterministic replay makespan (T_C)
    replay_parser = subparsers.add_parser(
        'replay',
        help='Replay makespan (T_C) only.',
        description='Run the deterministic replay scheduler (Part 18) and report T_C/model slack only.',
    )
    _add_common_arguments(replay_parser, include_replay=True)
    replay_parser.set_defaults(func=cmd_replay)

    # sweep - capacity sweep (Part 19)
    sweep_parser = subparsers.add_parser(
        'sweep',
        help='Capacity sweep for one resource.',
        description='Sweep capacity for one resource across a range and report predicted T_C, normalized improvement, and the knee point.',
    )
    sweep_parser.add_argument(
        'directory', type=str,
        help='Path to the BuildStream run directory.'
    )
    sweep_parser.add_argument(
        '--plane2', type=str, metavar='NATIVE_REPORT.json',
        help='Plane 2 report for this same run: the knee line then says how\n'
             'many cores were measured busy, not just how many were asked for.'
    )
    sweep_parser.add_argument(
        '--resource', type=str, default='PROCESS',
        help='Resource to sweep (e.g. PROCESS, DOWNLOAD, UPLOAD). Default: PROCESS.'
    )
    sweep_parser.add_argument(
        '--min-capacity', type=int, default=1, metavar='N',
        help='Minimum capacity to test. Default: 1.'
    )
    sweep_parser.add_argument(
        '--max-capacity', type=int, default=None, metavar='N',
        help='Maximum capacity to test. Default: number of tasks.'
    )
    sweep_parser.add_argument(
        '--step', type=int, default=1, metavar='N',
        help='Increment between tested capacities. Default: 1.'
    )
    sweep_parser.add_argument(
        '--calibration-dir', action='append', default=[], metavar='PATH',
        help='A run directory captured at a different value of the swept\n'
             'resource, for duration calibration. Repeatable; 2+ enables\n'
             'interpolation.'
    )
    sweep_parser.add_argument(
        '-f', '--format', type=str, choices=['text', 'json'], default='text',
        help='Output format: text (human-readable), json (machine-readable). Default: text.'
    )
    sweep_parser.add_argument('-o', '--output', type=str, help='Write output to PATH instead of stdout.')
    sweep_parser.add_argument(
        '-c', '--capacity', type=int, default=None, metavar='N',
        help='Override system resource capacity for resources not being swept. Default: auto-detect from run-context.'
    )
    sweep_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose (DEBUG) logging.')
    sweep_parser.add_argument('-q', '--quiet', action='store_true', help='Errors only.')
    sweep_parser.add_argument('--log-file', type=str, default=None, metavar='PATH', help='Also write logs to PATH.')
    sweep_parser.set_defaults(func=cmd_sweep)

    # utilisation - CPU utilisation accounting
    utilisation_parser = subparsers.add_parser(
        'utilisation',
        help='CPU utilisation accounting only.',
        description='Report CPU utilisation accounting (Part 30, M4) only.',
    )
    _add_common_arguments(utilisation_parser)
    utilisation_parser.set_defaults(func=cmd_utilisation)

    # diagnostics - advanced diagnostics
    diagnostics_parser = subparsers.add_parser(
        'diagnostics',
        help='Advanced diagnostics only.',
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
        help="A Plane 3 report (`bga cache-logs --format json`) for the same\n"
        "             project, supplying the per-element sandbox tax."
    )
    correlate_parser.add_argument(
        'native_report', type=str, nargs='?', default=None,
        help='Path to the JSON report written by `bga capture run` (Plane 2).'
    )
    correlate_parser.set_defaults(func=cmd_correlate)

    blast_parser = subparsers.add_parser(
        'blast',
        help="What rebuilds if I touch this repository, path or element?",
        description='Answer the blast-radius question from whichever end you have '
                    'it: a git url (every element sourcing that repository - the '
                    'monorepo case, where one ref decides them all), a file or '
                    'directory (the elements whose `local` sources stage it), or an '
                    'element name (its downstream closure). Reports the direct '
                    'elements, the closure split into kinds that build and kinds '
                    'that assemble, and the measured cost from the named run '
                    '(UX-172). A question, not a gate: always exits 0.',
    )
    blast_parser.add_argument(
        'target', metavar='TARGET',
        help='A git url, a path in the project, or an element name. Resolved in\n'
             'that order, and the answer says which reading it used.'
    )
    blast_parser.add_argument(
        'run', nargs='?', default='@last', metavar='RUN',
        help='The run to measure against; `@last` by default, same alias grammar\n'
             'as every other command.'
    )
    blast_parser.add_argument(
        '--project', default=None, metavar='PATH',
        help='The project a relative path is resolved against. Defaults to the\n'
             'enclosing BuildStream project.'
    )
    blast_parser.add_argument(
        '--no-cost', action='store_true',
        help='Skip the measured rebuild time. The rest of the answer comes from\n'
             'the graph and the source inventory alone, which on a large project\n'
             'is the difference between a lookup and a full analysis (UX-182).'
    )
    blast_parser.add_argument(
        '-f', '--format', choices=['text', 'json'], default='text',
        help='Output format: text (human-readable), json (machine-readable).'
    )
    blast_parser.add_argument(
        '-o', '--output', default=None, help='Write output to PATH instead of stdout.',
    )
    blast_parser.set_defaults(func=cmd_blast)

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
        help='Run directories, oldest first. Order is the caller\'s to know:\n'
             'nothing in a run records which build came before it.'
    )
    cache_trend_parser.add_argument(
        '-f', '--format', choices=['text', 'json'], default='text',
        help='Output format: text (human-readable), json (machine-readable).'
    )
    cache_trend_parser.add_argument(
        '-o', '--output', default=None, help='Write output to PATH instead of stdout.',
    )
    cache_trend_parser.set_defaults(func=cmd_cache_trend)

    compare_parser = subparsers.add_parser(
        'compare',
        usage='bga compare [options] BASELINE CANDIDATE',
        help='Compare two runs and report a verdict.',
        description='Compare a baseline run against a candidate run: signed deltas in certified floors, '
                    'efficiency score, and attribution, plus an improved/regressed/no-significant-change '
                    'verdict gated on confidence and graph comparability (docs/backlog/scenarios/UX-01 - not spec-mandated).',
    )
    compare_parser.add_argument('baseline', type=str, help='Path to the baseline (before) run directory.')
    compare_parser.add_argument('candidate', type=str, help='Path to the candidate (after) run directory.')
    compare_parser.add_argument(
        '-f', '--format', type=str, choices=['text', 'json', 'ci-comment'],
        default='text',
        help='Output format. Default: text.'
    )
    compare_parser.add_argument(
        '--native-report', type=str, default=None, metavar='PATH',
        help='Candidate Plane 2 report (adds unused-dependency detail).'
    )
    compare_parser.add_argument('-o', '--output', type=str, help='Write output to PATH instead of stdout.')
    compare_parser.add_argument(
        '-c', '--capacity', type=int, default=None, metavar='N',
        help='Override resource capacity for both runs.'
    )
    compare_parser.add_argument(
        '--fail-on-inefficient-additions', action='store_true',
        help='CI gate: fail on inefficiently added work.'
    )
    compare_parser.add_argument(
        '--max-addition-stretch', type=float, default=DEFAULT_MAX_ADDITION_STRETCH,
        metavar='RATIO',
        help='Threshold for the addition gate.'
    )
    compare_parser.add_argument(
        '--allow-mismatch', action='store_true',
        help='Compare even if the runs are not comparable.'
    )
    compare_parser.add_argument(
        '--allow-cross-host', action='store_true',
        help='UX-186: let the CI gates pass on runs measured on different '
             'machines. For a farm of uniform runners, opted into once.'
    )
    compare_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose (DEBUG) logging.')
    compare_parser.add_argument('-q', '--quiet', action='store_true', help='Errors only.')
    compare_parser.add_argument('--log-file', type=str, default=None, metavar='PATH', help='Also write logs to PATH.')
    compare_parser.add_argument(
        '--fail-on-regression', action='store_true',
        help=f'CI gate: exit {EXIT_CODE_REGRESSION} if slower.'
    )
    compare_parser.add_argument(
        '--fail-on-efficiency-regression', action='store_true',
        help=f'CI gate: exit {EXIT_CODE_EFFICIENCY_REGRESSION} if less efficient.'
    )
    compare_parser.add_argument(
        '--max-efficiency-drop', type=float, default=None, metavar='PP',
        help='Occupancy drop allowed, in percentage points.'
    )
    compare_parser.add_argument(
        '--min-efficiency', type=float, default=None, metavar='RATIO',
        help=f'CI gate: exit {EXIT_CODE_EFFICIENCY_REGRESSION} below RATIO occupancy.'
    )
    compare_parser.add_argument(
        '--require-efficiency-signal', action='store_true',
        help=f'Exit {EXIT_CODE_SIGNAL_UNAVAILABLE} if the signal is missing.'
    )
    compare_parser.add_argument(
        '--baseline-run', action='append', metavar='PATH',
        help='Extra baseline run; repeat to form a noise band.'
    )
    compare_parser.add_argument(
        '--band-k', type=float, default=DEFAULT_BAND_K, metavar='K',
        help='Noise-band width, in scaled-MAD units.'
    )
    # UX-104 item 2: a memory *note*, not a gate. Two flags rather than
    # one because the envelope is a fact about a run and the two runs are
    # independent captures - inferring the baseline's Plane 2 report from
    # the candidate's would be comparing a run against itself.
    compare_parser.add_argument(
        '--baseline-plane2', default=None, metavar='PATH',
        help='Baseline Plane 2 report (adds memory detail).'
    )
    compare_parser.add_argument(
        '--candidate-plane2', default=None, metavar='PATH',
        help='UX-104: the candidate run\'s Plane 2 report. See --baseline-plane2.',
    )
    compare_parser.add_argument(
        '--fail-on-low-confidence', action='store_true',
        help=f'CI gate: exit {EXIT_CODE_REGRESSION} on low confidence.'
    )
    compare_parser.add_argument(
        '--regression-threshold', type=float, default=None, metavar='PCT',
        help='Percentage-point threshold for --fail-on-regression (default: the\n'
             'same 1%% significance rule the verdict uses).'
    )
    compare_parser.set_defaults(func=cmd_compare)

    # UX-191: after every subparser exists, so the walk sees all of them.
    _attach_run_completers(parser)
    return parser


# UX-126: every positional that names a run directory, so `@last` and
# `@prev` work in all of them rather than in the two the store's author
# happened to think of. Attributes rather than commands, because that is
# what the resolution actually depends on - a new command that reuses
# `directory` gets aliases for free, and one that invents a new name
# does not silently half-work.
_RUN_DIRECTORY_ARGS = ('directory', 'baseline', 'candidate')
_RUN_DIRECTORY_LIST_ARGS = ('run_dirs', 'baseline_run', 'calibration_dir')

# UX-134: the store holds both halves of a capture, so both halves take
# its names. Kept as a separate tuple because they resolve to a
# different file inside the same snapshot, not because they are a
# different kind of argument.
_PLANE2_ARGS = ('native_report', 'plane2', 'baseline_plane2', 'candidate_plane2')


def _resolve_run_aliases(args: argparse.Namespace) -> None:
    """Turn snapshot aliases into paths, in place.

    Anything that is not an alias passes through untouched, so an
    explicit path means exactly what it meant before the store existed -
    including a directory that really is called `@last`, which is a path
    the store's grammar deliberately still reaches (`run_store._ALIAS`).
    """
    for name in _RUN_DIRECTORY_ARGS:
        value = getattr(args, name, None)
        if isinstance(value, str):
            setattr(args, name, resolve_run_alias(value))
    for name in _RUN_DIRECTORY_LIST_ARGS:
        values = getattr(args, name, None)
        if isinstance(values, list):
            setattr(args, name, [resolve_run_alias(v) for v in values])
    for name in _PLANE2_ARGS:
        value = getattr(args, name, None)
        if isinstance(value, str):
            setattr(args, name, resolve_plane2_alias(value))


# UX-190: which command publishes which output schema.
_SCHEMA_BY_COMMAND = {
    "analyze": schemas.ANALYZE,
    "graph": schemas.ANALYZE,
    "floors": schemas.ANALYZE,
    "replay": schemas.ANALYZE,
    "sweep": schemas.ANALYZE,
    "utilisation": schemas.ANALYZE,
    "diagnostics": schemas.ANALYZE,
    "compare": schemas.COMPARE,
    "blast": schemas.BLAST,
    # UX-215: the join has emitted this JSON since UX-51 and answered
    # "correlate produces no versioned JSON output" when asked what
    # shape it was.
    "correlate": schemas.CORRELATE,
}


def _maybe_complete() -> None:
    """Hand the parser to `argcomplete`, when the shell asked for it.

    Costs one failed import when completion is not installed, and
    nothing at all when the shell hook is not active: `argcomplete`
    returns immediately unless `_ARGCOMPLETE` is in the environment.
    """
    try:
        import argcomplete
    except ImportError:
        return
    argcomplete.autocomplete(create_parser())


def _maybe_print_schema(argv: list) -> Optional[int]:
    """`bga <command> --schema` -> the JSON Schema of its output, exit 0.

    Returns None when this invocation is not a schema request, so the
    normal parse runs.
    """
    if "--schema" not in argv:
        return None
    command = next((arg for arg in argv if not arg.startswith("-")), None)
    name = _SCHEMA_BY_COMMAND.get(command)
    if name is None:
        print(
            f"Error: `--schema` is available on "
            f"{', '.join(sorted(_SCHEMA_BY_COMMAND))}; "
            f"{command or 'no command'} produces no versioned JSON output.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(schemas.schema(name), indent=2))
    return 0


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
    raw_argv = list(sys.argv[1:] if argv is None else argv)

    # UX-190: `--schema` answers about the *shape* of an output, not
    # about a run, so it is checked before argparse insists on the run
    # directory the command would otherwise need - and before the alias
    # dispatch below, which would hand `bga doctor --schema` to a tool
    # that has never heard of the flag. A pre-parse hook rather than a
    # `nargs="?"` positional, because weakening three commands' argument
    # checking to add one switch is the wrong trade.
    # UX-191: shell completion for the argparse program as it stands, via
    # `argcomplete`. Inert without the shell hook - the marker line at the
    # top of this file and this call are the whole integration, and an
    # environment without `argcomplete` installed simply skips it.
    #
    # A `click` migration was considered and declined: it would touch
    # every subcommand, re-render `UX-158`'s help from scratch, and buy
    # nothing argcomplete does not already give. Recorded in UX-191.
    _maybe_complete()

    schema_exit = _maybe_print_schema(raw_argv)
    if schema_exit is not None:
        return schema_exit

    from .tools_dispatch import dispatch
    tool_exit = dispatch(raw_argv)
    if tool_exit is not None:
        return tool_exit

    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        _resolve_run_aliases(args)
    except StoreError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
