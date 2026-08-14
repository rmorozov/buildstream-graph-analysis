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
import hashlib
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


def _read_ref_storage(project_dir: str):
    """Reads `project.conf`'s top-level `ref-storage` key directly
    (`inline` when absent - BuildStream's own default). Deliberately a
    direct, minimal YAML read rather than asking `bst` - there's no `bst
    show`-style query for project-level config the way there is for
    element fields (P4-08's own reasoning for using `bst show` at all
    doesn't apply here, since `ref-storage` is a project.conf-level
    setting, not an element one). **Known limitation**: this reads the
    literal key in `project.conf` itself - an exotic project that sets
    `ref-storage` via a conditional/variable substitution rather than a
    plain scalar would not be read correctly. Not observed in practice
    (confirmed real BuildStream 2.7.0 projects set it as a plain
    top-level scalar - see docs/tasks/P4-13-strict-mode-project-refs-consistency.md),
    but worth naming plainly rather than silently assuming.
    """
    try:
        import yaml
    except ImportError as e:
        raise RuntimeError(
            "--strict requires PyYAML to read project.conf's ref-storage setting "
            "(pip install -e '.[bst]', which now includes pyyaml)"
        ) from e

    project_conf_path = Path(project_dir) / "project.conf"
    if not project_conf_path.exists():
        raise RuntimeError(f"no project.conf found at {project_conf_path}")
    try:
        data = yaml.safe_load(project_conf_path.read_text()) or {}
    except yaml.YAMLError as e:
        raise RuntimeError(f"could not parse {project_conf_path} as YAML: {e}") from e
    return data.get("ref-storage", "inline")


def _check_project_refs_strict(project_dir: str):
    """`--strict` mode's real, opt-in guarantee (P4-13) - hardens
    `_git_consistency_note`'s best-effort whole-tree dirty warning into
    an actual failure, using BuildStream's own `project.refs` mechanism
    (a real, content-addressable fingerprint of every trackable
    element's resolved source ref, confirmed against BuildStream 2.7.0 -
    see this task's own research in
    docs/tasks/P4-13-strict-mode-project-refs-consistency.md).

    Fails loudly (raises RuntimeError, never silently degrades) unless
    all of the following hold:
    - the project sets `ref-storage: project.refs` in `project.conf`
      (not the default `inline` - a project using inline refs has no
      single file this mechanism can hash/compare, a real, confirmed
      limitation, not a bug to work around here - see this task's Out
      of Scope);
    - `project.refs` actually exists (a project with `ref-storage:
      project.refs` but zero trackable-ref sources never gets one
      created at all - also confirmed real);
    - the project directory is a git repository;
    - `project.refs` itself has no uncommitted changes relative to the
      project's own git history (a more precise, actionable check than
      the whole-tree dirty warning, since `project.refs` is specifically
      the file whose content matters for reproducibility here).

    Returns the real, real file's bytes on success (so the caller can
    embed a provenance hash) - never returns on failure, always raises.
    """
    ref_storage = _read_ref_storage(project_dir)
    if ref_storage != "project.refs":
        raise RuntimeError(
            f"--strict requires ref-storage: project.refs in {project_dir}/project.conf "
            f"(found: {ref_storage!r}) - a project using the default inline ref-storage "
            "has no single file this mechanism can hash/compare, so --strict cannot "
            "provide a real guarantee for it. See docs/tasks/P4-13-strict-mode-project-refs-consistency.md."
        )

    project_refs_path = Path(project_dir) / "project.refs"
    if not project_refs_path.exists():
        raise RuntimeError(
            f"--strict: {project_dir}/project.conf sets ref-storage: project.refs, but no "
            f"project.refs file exists - the project may have no trackable-ref sources yet, "
            "or none have been tracked (run `bst source track` first). --strict refuses to "
            "silently pass without a real project.refs to check."
        )

    # Check "is this a git repo at all" first, with the same command
    # _git_consistency_note already relies on (confirmed real exit code
    # 128 for a non-repo directory) - `git diff`'s own exit code for a
    # non-repo is a *different*, easy-to-misread 129 (usage error, not
    # "not a repository"), confirmed empirically while writing this.
    try:
        status_check = subprocess.run(
            ["git", "-C", project_dir, "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"--strict: could not run git in {project_dir}: {e}") from e
    if status_check.returncode != 0:
        raise RuntimeError(
            f"--strict: {project_dir} is not a git repository - project.refs' consistency "
            "can't be verified against any history, so --strict refuses to pass."
        )

    try:
        git_check = subprocess.run(
            ["git", "-C", project_dir, "diff", "--exit-code", "--", "project.refs"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"--strict: could not run git to check project.refs: {e}") from e

    if git_check.returncode != 0:
        raise RuntimeError(
            f"--strict: {project_dir}/project.refs has uncommitted changes relative to git "
            "HEAD - the resolved source state this file records may not match what the "
            "analyzed build actually ran against. Commit project.refs (after confirming it "
            "reflects the build being analyzed) before extracting with --strict."
        )

    return project_refs_path.read_bytes()


def extract_run(
    project_dir: str,
    log_path: str,
    output_dir: str,
    log_format: str = "auto",
    start_time: str = None,
    trace_epsilon_us: int = 50000,
    bst_bin: str = "bst",
    strict: bool = False,
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

    # --strict (P4-13): a real, opt-in, fail-loud guarantee via
    # project.refs - see _check_project_refs_strict's own docstring.
    # Raises on failure; never silently degrades to the warning above.
    if strict:
        _check_project_refs_strict(project_dir)

    # Provenance record (P4-13 Required Fix item 2): regardless of
    # --strict, embed a stable hash of project.refs whenever it exists,
    # so a *later*, independent re-check can detect drift if graph.json
    # is ever re-extracted separately from this run. Deliberately
    # unconditional on --strict - a non-strict run still benefits from
    # having this recorded for later.
    project_refs_provenance = None
    project_refs_path = Path(project_dir) / "project.refs"
    if project_refs_path.exists():
        project_refs_provenance = {
            "path": "project.refs",
            "sha256": hashlib.sha256(project_refs_path.read_bytes()).hexdigest(),
        }

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
    # project.refs provenance (P4-13) - see the comment above computing
    # project_refs_provenance. Confirmed no collision with run-context/v9's
    # spec-mandated schema (Part 32.1).
    if project_refs_provenance:
        run_context["project_refs_provenance"] = project_refs_provenance

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
    parser.add_argument(
        "--strict", action="store_true",
        help="Fail loudly (instead of the default best-effort warning) unless the project "
        "uses ref-storage: project.refs and project.refs itself has no uncommitted changes "
        "(P4-13). Only usable for projects with ref-storage: project.refs and at least one "
        "trackable-ref source - see docs/tasks/P4-13-strict-mode-project-refs-consistency.md.",
    )
    args = parser.parse_args()

    try:
        summary = extract_run(
            args.project_dir, args.log_path, args.output_dir,
            log_format=args.format, start_time=args.start_time,
            trace_epsilon_us=args.trace_epsilon_us, bst_bin=args.bst_bin,
            strict=args.strict,
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
