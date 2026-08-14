#!/usr/bin/env python3
"""Coordinate a real BuildStream project + a real BuildStream log into
one complete `bga`-ready run directory (run-context.json + graph.json +
trace.json) in a single step (P4-10). See docs/ingestion-pipeline.md for
the full design record.

This does not invoke `bst build` itself - it only coordinates *extraction*
from a build that already happened (or is happening and has produced a
log so far). The three producer pieces it coordinates
(tools/bst_log_to_chrome_trace.py + tools/chrome_trace_to_bga_trace.py
for trace, tools/bst_show_to_graph.py for graph, tools/bst_run_context.py
for run-context) each stay independent, single-purpose scripts by design
- this is only the convenience wiring.

Target derivation: the target element list is read directly from the
log's own "Targets:" summary-header line (BuildStream prints this
unconditionally, in both wrapped and raw logs) - never a hardcoded
umbrella-target convention like "all.bst". This was flagged as the top
scenario risk when this design was discussed: a mismatch between what
graph.json declares as requested and what the trace shows was actually
built would silently corrupt leaf/deferrability analysis (Part 24) and
terminal-task selection (Part 6.2) with no error raised - deriving both
from the exact same log removes that whole class of mismatch.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from tools.bst_log_to_chrome_trace import WrapperTraceConverter, _resolve_start_time_us
from tools.chrome_trace_to_bga_trace import chrome_events_to_bga_spans, invocation_wall_clock
from tools.bst_show_to_graph import extract_graph


def _parse_targets(targets_str: str):
    return [t.strip() for t in targets_str.split(",") if t.strip()]


def _git_consistency_note(project_dir: str):
    """Best-effort time-of-extraction consistency signal (see
    docs/ingestion-pipeline.md's "time-of-extraction consistency" note):
    graph.json's cache keys reflect the project state *at the moment bst
    show runs*, which may not be the same state the analyzed build
    actually ran against. There's no commit hash embedded in a BuildStream
    log to compare against directly, so the strongest available signal is
    whether the project's own git checkout is currently dirty - a dirty
    tree is grounds to distrust the extracted graph.json's cache keys
    matching what was really built. Returns a warning string, or None if
    project_dir isn't a git repo (nothing to check) or the tree is clean.
    """
    try:
        status = subprocess.run(
            ["git", "-C", project_dir, "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if status.returncode != 0:
        return None  # not a git repo - nothing to check
    if status.stdout.strip():
        return (
            f"project directory {project_dir!r} has uncommitted changes - "
            "graph.json's cache keys reflect the CURRENT working tree, which may "
            "not match what the analyzed log actually built. Extract graph.json "
            "from the exact commit the build ran against for a reliable result."
        )
    return None


def extract_run(
    project_dir: str,
    log_path: str,
    output_dir: str,
    log_format: str = "auto",
    start_time: str = None,
    trace_epsilon_us: int = 50000,
    bst_bin: str = "bst",
):
    """Run the full extraction pipeline. Returns a dict summary (targets,
    span/element/dependency counts, warnings) - the CLI entry point below
    prints it; callers embedding this can use it directly.
    """
    warnings = []

    start_time_us = _resolve_start_time_us(start_time, log_path)
    converter = WrapperTraceConverter(raw_start_time_us=start_time_us)
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if log_format == "wrapped":
                converter.process_line_wrapped(line)
            elif log_format == "raw":
                converter.process_line_raw(line)
            else:
                converter.process_line(line)
    converter.end_current_command(converter.last_known_ts)

    if not converter.targets:
        raise RuntimeError(
            f"Could not find a 'Targets:' line in {log_path!r} - this log doesn't "
            "look like it came from a real `bst build`/`bst show` invocation "
            "(or the header was truncated before it was captured). Refusing to "
            "guess a target list from a hardcoded convention."
        )
    targets = _parse_targets(converter.targets)

    # trace.json
    spans, dropped = chrome_events_to_bga_spans(converter.trace_events)
    trace = {"spans": spans, "phases": []}
    if dropped:
        warnings.append(f"{len(dropped)} log event(s) could not be converted to spans (see --verbose)")

    # graph.json
    try:
        graph = extract_graph(project_dir, targets, bst_bin=bst_bin)
    except RuntimeError as e:
        raise RuntimeError(f"graph extraction failed: {e}") from e

    consistency_warning = _git_consistency_note(project_dir)
    if consistency_warning:
        warnings.append(consistency_warning)

    # run-context.json
    scheduler = converter.get_scheduler_config()
    wall_start_us, wall_end_us = invocation_wall_clock(converter.trace_events)
    run_context = {
        "trace_epsilon_us": trace_epsilon_us,
        "resource_capacities": {
            "PROCESS": scheduler["builders"],
            "DOWNLOAD": scheduler["fetchers"],
            "UPLOAD": scheduler["pushers"],
        },
        "max_jobs": scheduler["builders"],
        "cpu_accounting": {"effective_cpus": scheduler["builders"]},
    }
    if wall_start_us is not None and wall_end_us is not None:
        run_context["wall_clock"] = {"start_us": wall_start_us, "end_us": wall_end_us}
    else:
        warnings.append("no bst-invocation span found - wall_clock omitted from run-context.json")
    # BuildStream's own top-level pipeline overhead (Query cache,
    # Resolving elements, etc. - P4-14), if the log has any. A non-spec,
    # additive extension of run-context/v9 (Part 32.1), same precedent as
    # element_kind's addition to graph/v9 (P4-08).
    if converter.pipeline_overhead:
        run_context["pipeline_overhead"] = converter.pipeline_overhead

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "graph.json").write_text(json.dumps(graph, indent=2))
    (out_dir / "trace.json").write_text(json.dumps(trace, indent=2))
    (out_dir / "run-context.json").write_text(json.dumps(run_context, indent=2))
    # Also keep the intermediate Chrome Trace JSON - not part of bga's
    # input contract, but the same real, human-inspectable artifact the
    # user's own existing personal workflow (visualizing a real build
    # timeline in perfetto.dev) already relies on tools/bst_log_to_chrome_trace.py
    # for; producing it here for free means one extraction run serves
    # both purposes.
    (out_dir / "chrome_trace.json").write_text(
        json.dumps(converter.trace_events, indent=2)
    )

    return {
        "targets": targets,
        "elements": len(graph["elements"]),
        "dependencies": len(graph["dependencies"]),
        "spans": len(spans),
        "output_dir": str(out_dir),
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Produce a complete bga-ready run directory (run-context.json + "
        "graph.json + trace.json) from a real BuildStream project + log in one step.",
    )
    parser.add_argument("project_dir", help="Path to the BuildStream project directory")
    parser.add_argument("log_path", help="Path to the build log (wrapped or raw)")
    parser.add_argument("output_dir", help="Directory to write the run directory into")
    parser.add_argument(
        "--format", choices=("auto", "wrapped", "raw"), default="auto",
        help="Input log format - same semantics as bst_log_to_chrome_trace.py",
    )
    parser.add_argument(
        "--start-time", default=None,
        help="ISO-8601 timestamp anchor for raw-format elapsed timestamps; "
        "defaults to the log file's mtime.",
    )
    parser.add_argument(
        "--trace-epsilon-us", type=int, default=50000,
        help="Quantization epsilon in microseconds (Part 3.2 default: 50000)",
    )
    parser.add_argument(
        "--bst-bin", default="bst",
        help="Path to the bst executable (default: bst, resolved via PATH)",
    )
    args = parser.parse_args()

    try:
        summary = extract_run(
            args.project_dir, args.log_path, args.output_dir,
            log_format=args.format, start_time=args.start_time,
            trace_epsilon_us=args.trace_epsilon_us, bst_bin=args.bst_bin,
        )
    except (RuntimeError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(
        f"Wrote run directory to {summary['output_dir']} - "
        f"targets={summary['targets']}, {summary['elements']} elements, "
        f"{summary['dependencies']} dependencies, {summary['spans']} spans"
    )
    for warning in summary["warnings"]:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
