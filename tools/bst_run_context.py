#!/usr/bin/env python3
"""Produce run-context/v9 JSON (Part 32.1) from a real BuildStream
invocation's own log - the second of the two producer pieces P4-08 split
off (graph.json, from `bst show`, is done; this is the run-context.json
side). See docs/spec/ingestion-pipeline.md for the full design record.

Unlike graph.json, run-context.json has no `bst show` equivalent - `bst
show` is purely static project introspection with no notion of runtime
resource capacity, wall-clock bounds, or CPU accounting (confirmed while
building P4-08). This data has to come from the real invocation's own
log instead:

  max_jobs / resource_capacities - BuildStream prints its own already-
      resolved scheduler concurrency limits unconditionally in its
      summary header ("Maximum {Fetch,Build,Push} Tasks:") - this is
      more robust than re-parsing --builders/--fetchers/--pushers CLI
      flags ourselves, since it reflects whatever precedence BuildStream
      itself already applied (CLI flag, user config, or its own bundled
      default) without us needing to reproduce that logic. Falls back to
      BuildStream's own bundled defaults (buildstream/data/userconfig.yaml,
      confirmed against a real 2.7.0 install: fetchers=10, builders=4,
      pushers=4) only if those header lines aren't present in the log
      (e.g. a truncated CI log capture).
  wall_clock - reuses the same bst-invocation span bounds
      tools/chrome_trace_to_bga_trace.py's invocation_wall_clock already
      derives, whether the source log is wrapped (a real "Executing
      command:" line) or raw (a synthesized invocation span covering the
      whole log, see bst_log_to_chrome_trace.WrapperTraceConverter).
  cpu_accounting - deliberately omitted (P1-33). `builders` is
      BuildStream's own job-slot scheduling parameter, not a measured CPU
      core/thread count; populating cpu_accounting.effective_cpus from it
      (this file's own previous behavior) made bga's CPU reconciliation
      (Part 33.3) and Part 30.3's oversubscription check run against
      synthetic data tautologically derived from the same job-slot count
      on both sides, not a genuine independent measurement - bga now
      reports CPU accounting as honestly unavailable rather than compute
      against a fabricated capacity. No real CPU-measurement source
      (cgroup accounting, /proc sampling) exists in this ingestion
      pipeline yet. See
      docs/backlog/tasks/P1-33-cpu-accounting-conflates-capacity-with-measurement.md.
  native_max_jobs / host_cpu_count / cpu_budget - UX-12/UX-15 fields,
      shared with tools/bst_extract_run.py via
      tools/_run_context_common.py (UX-18, so this standalone producer
      path doesn't silently diverge from that one again): host_cpu_count
      is always auto-detected; cpu_budget is purely operator-supplied
      via --cpu-budget, since it is not visible in a BuildStream log at
      all. `native_max_jobs` is recovered
      automatically from a wrapped log's own recorded invocation
      (UX-29 - BuildStream's output never reports --max-jobs, but the
      wrapper's first line does); --native-max-jobs overrides it, and
      `native_max_jobs_source` records which of the two won.
  memory_budget_mb / estimated_job_memory_mb - UX-21 fields, same shared
      module: both purely operator-supplied via --memory-budget-mb/
      --estimated-job-memory-mb, no auto-detection tier (no real
      per-task memory measurement source exists in this pipeline).
"""
import argparse
import json
import sys

from .bst_log_to_chrome_trace import (
    WrapperTraceConverter,
    _resolve_start_time_us,
)
from .chrome_trace_to_bga_trace import invocation_wall_clock
from ._run_context_common import add_cpu_capacity_fields, add_memory_capacity_fields


def build_run_context(
    log_path: str,
    log_format: str = "auto",
    start_time: str = None,
    trace_epsilon_us: int = 50000,
    host: str = None,
    native_max_jobs: int = None,
    cpu_budget: int = None,
    memory_budget_mb: int = None,
    estimated_job_memory_mb: int = None,
) -> dict:
    """Run the real log converter against `log_path` and derive a
    run-context/v9 dict from its output - the same converter
    tools/bst_log_to_chrome_trace.py uses for the trace side, so scheduler
    config and wall-clock bounds are read from a single real parse of the
    log, not a second, possibly-diverging one.
    """
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
        # cpu_accounting deliberately omitted - see module docstring (P1-33).
    }
    if wall_start_us is not None and wall_end_us is not None:
        run_context["wall_clock"] = {"start_us": wall_start_us, "end_us": wall_end_us}
    if host:
        run_context["host"] = host
    # native_max_jobs/host_cpu_count (UX-12), cpu_budget (UX-15) - see
    # tools/_run_context_common.py; UX-18 brought this standalone
    # producer path up to parity with tools/bst_extract_run.py's own,
    # which had these fields already.
    add_cpu_capacity_fields(
        run_context, native_max_jobs=native_max_jobs, cpu_budget=cpu_budget,
        # UX-29: same auto-recovery as bst_extract_run.py - kept at
        # parity deliberately, since UX-18 exists precisely because these
        # two producers had silently diverged once already.
        parsed_native_max_jobs=scheduler.get("native_max_jobs"),
    )
    # memory_budget_mb/estimated_job_memory_mb (UX-21) - same shared-
    # helper pattern.
    add_memory_capacity_fields(
        run_context, memory_budget_mb=memory_budget_mb, estimated_job_memory_mb=estimated_job_memory_mb,
    )

    return run_context


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Produce run-context.json from a real BuildStream invocation's log."
    )
    parser.add_argument("input_log", help="Path to the log file (wrapped or raw).")
    parser.add_argument("output_json", help="Path to write run-context.json to.")
    parser.add_argument(
        "--format", choices=("auto", "wrapped", "raw"), default="auto",
        help="Input log format - same semantics as bst_log_to_chrome_trace.py.",
    )
    parser.add_argument(
        "--start-time", default=None,
        help="ISO-8601 anchor for a raw log's elapsed timestamps; defaults "
        "to the input file's mtime.",
    )
    parser.add_argument(
        "--trace-epsilon-us", type=int, default=50000,
        help="Quantization epsilon in microseconds (Part 3.2 default: 50000).",
    )
    parser.add_argument("--host", default=None,
                        help="Optional host identifier to record.")
    parser.add_argument(
        "--native-max-jobs", type=int, default=None,
        help="Override the per-element `make -jN` parallelism (not --builders). "
        "A wrapped log records it; pass this for a raw log (UX-29).",
    )
    parser.add_argument(
        "--cpu-budget", type=int, default=None,
        help="The cores this build is *intended* to use, when the detected count is "
        "not the real constraint - a cgroup CPU quota, or reserved headroom on a "
        "shared machine. Governs the oversubscription check (UX-15).",
    )
    parser.add_argument(
        "--memory-budget-mb", type=int, default=None,
        help="The memory (MB) this build is *intended* to use. Operator-supplied; "
        "with --estimated-job-memory-mb it drives the memory oversubscription "
        "check (UX-21).",
    )
    parser.add_argument(
        "--estimated-job-memory-mb", type=int, default=None,
        help="A rough estimate of one concurrent build job's memory footprint (MB) - "
        "a constant, not a measurement. Only meaningful with --memory-budget-mb "
        "(UX-21).",
    )
    args = parser.parse_args()

    try:
        run_context = build_run_context(
            args.input_log,
            log_format=args.format,
            start_time=args.start_time,
            trace_epsilon_us=args.trace_epsilon_us,
            host=args.host,
            native_max_jobs=args.native_max_jobs,
            cpu_budget=args.cpu_budget,
            memory_budget_mb=args.memory_budget_mb,
            estimated_job_memory_mb=args.estimated_job_memory_mb,
        )
    except FileNotFoundError:
        print(f"Error: Could not find input file '{args.input_log}'", file=sys.stderr)
        return 1

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(run_context, f, indent=2)

    print(f"Wrote run-context.json to {args.output_json}")
    if "wall_clock" not in run_context:
        print(
            "Warning: no bst-invocation span found in the log - wall_clock omitted "
            "(untracked_head_us/untracked_tail_us will not be computable)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
