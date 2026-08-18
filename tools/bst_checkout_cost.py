#!/usr/bin/env python3
"""Real, measured checkout cost from a `bst source checkout` or `bst
artifact checkout` log - a deliberately standalone tool, separate from
bga's core `analyze` pipeline (P4-15's Background/user decision).

Why standalone: a checkout invocation is its own separate BuildStream
session with its own separate wall clock - it shares no horizon with a
build trace, so folding it into bga's TaskKind/attribution pipeline
(built around one invocation's horizon, I4's Sum(attribution)==H) would
conflate two unrelated timelines. This tool instead answers a narrower,
concrete question directly: given real checkout logs, what did checking
out N elements individually really cost, vs. checking out one `kind:
stack` element covering all of them - grounding P4-15's structural
"consider grouping these under a stack" advisory in real measured numbers
instead of pure topology speculation, for a user who wants to confirm
before investing in a project restructure.

Two real, confirmed-via-source (BuildStream 2.7.0 `_stream.py::checkout()`)
facts this tool relies on:
- Checking out N elements as N separate invocations pays BuildStream's
  own pipeline-level overhead (Loading elements/Resolving elements/Query
  cache - see docs/backlog/tasks/P4-14-cache-query-overhead-visibility.md) once
  *per invocation* - N times total.
- Checking out one `stack` element depending on all N collapses this to
  a single sandbox-setup/export ("Staging dependencies"/"Integrating
  sandbox"/"Checking out files in ...", all logged under the stack
  element's own hash) plus one payment of the pipeline-level overhead -
  see docs/backlog/tasks/P4-15-stack-consolidation-heuristic.md's Background.

Both `bst source checkout`'s "Staging sources" and `bst artifact
checkout`'s "Staging dependencies"/"Integrating sandbox"/"Checking out
files in ..." are logged under action="main" with the checked-out
element's own real hash (confirmed against a real build) - reusing
tools/bst_log_to_chrome_trace.py's WrapperTraceConverter (the same
dual wrapped/raw-mode line parser P4-05/P4-10 already rely on) to parse
them, but reading its `trace_events`/`pipeline_overhead` directly rather
than going through chrome_trace_to_bga_trace.py's TaskKind conversion at
all - that conversion deliberately drops action="main" events, and this
tool's whole reason to exist is to *not* drop them.
"""
import argparse
import json
import sys
from typing import Dict, List

from tools.bst_log_to_chrome_trace import WrapperTraceConverter, _resolve_start_time_us
from tools.chrome_trace_to_bga_trace import invocation_wall_clock


def _parse_log(log_path: str, log_format: str = "auto") -> WrapperTraceConverter:
    start_time_us = _resolve_start_time_us(None, log_path)
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
    return converter


def _per_element_checkout_costs(trace_events: List[dict]) -> Dict[str, int]:
    """Sum real per-element checkout-phase durations (Staging sources /
    Staging dependencies / Integrating sandbox / Checking out files in
    ...) - each a real B/E pair under action="main" with the checked-out
    element's own hash (never the blank pipeline-level hash - see
    WrapperTraceConverter's own handle_bst_event, which routes those
    separately into pipeline_overhead). These phases are confirmed
    non-overlapping per element (each fully closes before the next opens
    - see docs/backlog/tasks/P4-15-stack-consolidation-heuristic.md), so a
    simple per-tid stack is enough to pair them correctly.
    """
    costs: Dict[str, int] = {}
    open_by_tid: Dict[int, dict] = {}
    for ev in trace_events:
        if ev.get("cat") != "bst-builder":
            continue
        args = ev.get("args") or {}
        if args.get("action") != "main":
            continue
        tid = ev.get("tid")
        if ev.get("ph") == "B":
            open_by_tid[tid] = ev
            continue
        if ev.get("ph") == "E":
            begin_ev = open_by_tid.pop(tid, None)
            if begin_ev is None:
                continue
            element = args.get("element", "")
            costs[element] = costs.get(element, 0) + (ev["ts"] - begin_ev["ts"])
    return costs


def summarize(log_path: str, log_format: str = "auto") -> dict:
    """Real, measured cost breakdown for a single checkout-command log."""
    converter = _parse_log(log_path, log_format)
    element_costs = _per_element_checkout_costs(converter.trace_events)
    pipeline_overhead_us = sum(e["elapsed_us"] for e in converter.pipeline_overhead)
    wall_start_us, wall_end_us = invocation_wall_clock(converter.trace_events)
    wall_clock_us = (wall_end_us - wall_start_us) if wall_start_us is not None and wall_end_us is not None else None
    return {
        "log_path": log_path,
        "pipeline_overhead_us": pipeline_overhead_us,
        "pipeline_overhead_phases": converter.pipeline_overhead,
        "elements": element_costs,
        "elements_total_us": sum(element_costs.values()),
        "wall_clock_us": wall_clock_us,
    }


def compare(individual_log_paths: List[str], consolidated_log_path: str, log_format: str = "auto") -> dict:
    """Real measured comparison: N separate checkout invocations vs. one
    consolidated (typically `kind: stack`-based) invocation covering the
    same elements. Each individual invocation pays its own
    pipeline-level overhead once; the consolidated invocation pays it
    only once total - that's the concrete mechanism this reports on, not
    an estimate.
    """
    individual_summaries = [summarize(p, log_format) for p in individual_log_paths]
    consolidated_summary = summarize(consolidated_log_path, log_format)

    individual_pipeline_us = sum(s["pipeline_overhead_us"] for s in individual_summaries)
    individual_elements_us = sum(s["elements_total_us"] for s in individual_summaries)
    individual_total_us = individual_pipeline_us + individual_elements_us

    consolidated_total_us = consolidated_summary["pipeline_overhead_us"] + consolidated_summary["elements_total_us"]

    savings_us = individual_total_us - consolidated_total_us
    return {
        "individual": {
            # Deliberately factual, not "payments avoided": whether N
            # separate pipeline-overhead payments (vs. the consolidated
            # invocation's 1) is actually a net win depends entirely on
            # how large *each* invocation's own resolved closure is -
            # confirmed by real measurement (see
            # docs/backlog/tasks/P4-15-stack-consolidation-heuristic.md's
            # Verification Log): consolidating under a `stack` that pulls
            # in a much larger closure than any individual element needed
            # can easily cost *more* pipeline overhead overall, not less.
            # `savings_us`/`savings_fraction_of_individual` below are the
            # real answer for a given real pair of logs - never assume
            # the sign from the invocation counts alone.
            "invocation_count": len(individual_summaries),
            "pipeline_overhead_us": individual_pipeline_us,
            "elements_total_us": individual_elements_us,
            "total_us": individual_total_us,
            "logs": individual_summaries,
        },
        "consolidated": consolidated_summary,
        "consolidated_total_us": consolidated_total_us,
        "savings_us": savings_us,
        "savings_fraction_of_individual": (savings_us / individual_total_us) if individual_total_us else None,
    }


def _format_summary_text(summary: dict) -> str:
    lines = [f"Checkout cost summary: {summary['log_path']}"]
    lines.append(f"  Pipeline overhead: {summary['pipeline_overhead_us'] / 1e6:.3f}s")
    for entry in summary["pipeline_overhead_phases"]:
        lines.append(f"    {entry['phase']:25s} {entry['elapsed_us'] / 1e6:8.3f}s")
    lines.append(f"  Per-element checkout cost ({len(summary['elements'])} element(s)):")
    for element, us in summary["elements"].items():
        lines.append(f"    {element:25s} {us / 1e6:8.3f}s")
    lines.append(f"  Elements total: {summary['elements_total_us'] / 1e6:.3f}s")
    if summary["wall_clock_us"] is not None:
        lines.append(f"  Wall clock: {summary['wall_clock_us'] / 1e6:.3f}s")
    return "\n".join(lines)


def _format_compare_text(result: dict) -> str:
    ind = result["individual"]
    lines = [
        f"Individual checkouts ({ind['invocation_count']} invocations):",
        f"  Pipeline overhead (paid {ind['invocation_count']}x): {ind['pipeline_overhead_us'] / 1e6:.3f}s",
        f"  Elements total: {ind['elements_total_us'] / 1e6:.3f}s",
        f"  Total: {ind['total_us'] / 1e6:.3f}s",
        "",
        "Consolidated checkout (1 invocation):",
        f"  Pipeline overhead (paid 1x): {result['consolidated']['pipeline_overhead_us'] / 1e6:.3f}s",
        f"  Elements total: {result['consolidated']['elements_total_us'] / 1e6:.3f}s",
        f"  Total: {result['consolidated_total_us'] / 1e6:.3f}s",
        "",
        f"Savings: {result['savings_us'] / 1e6:.3f}s",
    ]
    if result["savings_fraction_of_individual"] is not None:
        lines.append(f"  ({result['savings_fraction_of_individual'] * 100:.1f}% of the individual total)")
    if result["savings_us"] < 0:
        lines.append(
            "  Negative: the consolidated target's own resolved closure costs more "
            "pipeline overhead than the individual invocations paid in total - "
            "consolidating under this target is not a net win here."
        )
    return "\n".join(lines)


def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--format", choices=("auto", "wrapped", "raw"), default="auto",
        help="Input log format - same semantics as bst_log_to_chrome_trace.py",
    )
    common.add_argument(
        "--json", action="store_true", help="Emit JSON instead of a human-readable summary",
    )

    parser = argparse.ArgumentParser(
        description="Real, measured cost from bst source-checkout/artifact-checkout logs - "
        "individually or compared against a consolidated (e.g. kind: stack) checkout.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize_parser = subparsers.add_parser("summarize", parents=[common], help="Cost breakdown for one checkout log")
    summarize_parser.add_argument("log_path")

    compare_parser = subparsers.add_parser(
        "compare", parents=[common], help="Compare N individual checkout logs against one consolidated checkout log",
    )
    compare_parser.add_argument("--individual", nargs="+", required=True, metavar="LOG")
    compare_parser.add_argument("--consolidated", required=True, metavar="LOG")

    args = parser.parse_args()

    try:
        if args.command == "summarize":
            result = summarize(args.log_path, args.format)
            print(json.dumps(result, indent=2) if args.json else _format_summary_text(result))
        else:
            result = compare(args.individual, args.consolidated, args.format)
            print(json.dumps(result, indent=2) if args.json else _format_compare_text(result))
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
