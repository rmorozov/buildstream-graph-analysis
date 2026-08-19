#!/usr/bin/env python3
"""Coordinate a real BuildStream project + a real BuildStream log into
one complete `bga`-ready run directory (run-context.json + graph.json +
trace.json) in a single step (P4-10). See docs/spec/ingestion-pipeline.md for
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

from .bst_log_to_chrome_trace import WrapperTraceConverter, _resolve_start_time_us
from .chrome_trace_to_bga_trace import (
    chrome_events_to_bga_spans,
    failed_elements,
    invocation_wall_clock,
)
from .bst_show_to_graph import extract_graph
from ._run_context_common import add_cpu_capacity_fields, add_memory_capacity_fields


def _parse_targets(targets_str: str):
    return [t.strip() for t in targets_str.split(",") if t.strip()]


def _git_consistency_note(project_dir: str):
    """Best-effort time-of-extraction consistency signal (see
    docs/spec/ingestion-pipeline.md's "time-of-extraction consistency" note):
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


def _git_commit(project_dir: str):
    """The project directory's current git HEAD commit, or None if it
    isn't a git repository. Real, best-effort provenance input for
    run-identity (P1-37) - same subprocess pattern as
    _git_consistency_note, a separate call since that one only needs
    dirty/clean, not the actual commit."""
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _project_identity(project_dir: str) -> str:
    """A stable identifier for *which project* a run-identity manifest is
    about (UX-07). `project_git_commit` alone conflates two different
    BuildStream projects that happen to live under the same git commit -
    a monorepo with multiple projects, or (the real case that surfaced
    this) a baseline project and an `optimized/` variant living side by
    side as sibling directories - since neither the commit nor (often)
    the target name differs between them.

    Prefers `project_dir`'s path relative to its git repository's own
    root (stable across different clones/checkouts of the same repo,
    unlike an absolute filesystem path); falls back to the resolved
    absolute path when `project_dir` isn't inside a git repository at
    all (matches `_git_commit`'s own None-for-non-repo behavior - still
    distinguishes different projects on this machine, just not
    clone-portable).
    """
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if result is not None and result.returncode == 0:
        repo_root = Path(result.stdout.strip()).resolve()
        try:
            return str(Path(project_dir).resolve().relative_to(repo_root))
        except ValueError:
            pass  # project_dir isn't actually under its own reported toplevel - fall through
    return str(Path(project_dir).resolve())


def _compute_run_identity(project_dir: str, targets, scheduler: dict, project_refs_provenance, native_max_jobs=None):
    """Real run-identity manifest (P1-37 - I8's own invariant, "all
    analysis inputs must belong to the same run identity", names no
    concrete field or mechanism anywhere in the spec).

    A stable hash over the real inputs that determine graph.json's and
    trace.json's content at extraction time: which project was built
    (UX-07 - the project's path relative to its git repo root, or its
    resolved absolute path outside a repo), the target list (what was
    requested), the scheduler configuration (affects real observed
    concurrency/scheduling - native_max_jobs included here for the same
    reason as builders/fetchers/pushers, UX-12), the project's git commit
    (if available), and project.refs' own content hash (if the project
    uses ref-storage: project.refs - P4-13's existing, real provenance
    input, reused here rather than duplicated). Embedded identically
    into run-context.json, graph.json, and trace.json (as
    run_identity/run_identity_hash) so bga's own loader (P1-37) can
    cross-check that all three inputs of a given `bga analyze` actually
    came from the same extraction, not e.g. a trace.json accidentally
    copied in from an unrelated run.

    This proves inputs are mutually consistent *at extraction time* - it
    does not, and cannot, prove the analyzed build (which already
    happened, potentially much earlier) itself ran against this exact
    state; see this task's own docs/backlog/tasks/P1-37 file for that honestly-
    named limitation.
    """
    manifest = {
        "project_identity": _project_identity(project_dir),
        "targets": sorted(targets),
        "scheduler": {
            "builders": scheduler.get("builders"),
            "fetchers": scheduler.get("fetchers"),
            "pushers": scheduler.get("pushers"),
            "native_max_jobs": native_max_jobs,
        },
        "project_git_commit": _git_commit(project_dir),
        "project_refs_sha256": project_refs_provenance["sha256"] if project_refs_provenance else None,
    }
    manifest_hash = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {"manifest_hash": manifest_hash, **manifest}


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
    top-level scalar - see docs/backlog/tasks/P4-13-strict-mode-project-refs-consistency.md),
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
    docs/backlog/tasks/P4-13-strict-mode-project-refs-consistency.md).

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
            "provide a real guarantee for it. See docs/backlog/tasks/P4-13-strict-mode-project-refs-consistency.md."
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
    native_max_jobs: int = None,
    cpu_budget: int = None,
    memory_budget_mb: int = None,
    estimated_job_memory_mb: int = None,
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
        # cpu_accounting deliberately omitted (P1-33): `builders` is
        # BuildStream's own job-slot scheduling parameter, not a measured
        # CPU core/thread count - populating cpu_accounting.effective_cpus
        # from it made bga's CPU reconciliation (I9) and Part 30.3's
        # oversubscription check run against synthetic data that was
        # tautologically derived from the same job-slot count on both
        # sides, not a genuine independent measurement. No real CPU-
        # measurement source (cgroup accounting, /proc sampling) exists in
        # this ingestion pipeline yet - omitting the field is the honest
        # "unavailable" rather than fabricating a number. See
        # docs/backlog/tasks/P1-33-cpu-accounting-conflates-capacity-with-measurement.md.
    }
    # native_max_jobs/host_cpu_count (UX-12), cpu_budget (UX-15) - see
    # tools/_run_context_common.py (UX-18: shared with
    # tools/bst_run_context.py, the other producer path, so the two
    # don't silently diverge again).
    add_cpu_capacity_fields(
        run_context, native_max_jobs=native_max_jobs, cpu_budget=cpu_budget,
        # UX-29: recovered from the wrapper's own recorded invocation
        # when this log has one - see get_scheduler_config. An explicit
        # --native-max-jobs still wins; `native_max_jobs_source` records
        # which of the two the published value came from.
        parsed_native_max_jobs=scheduler.get("native_max_jobs"),
    )
    # memory_budget_mb/estimated_job_memory_mb (UX-21) - same shared-
    # helper pattern, purely operator-declared, no auto-detection tier.
    add_memory_capacity_fields(
        run_context, memory_budget_mb=memory_budget_mb, estimated_job_memory_mb=estimated_job_memory_mb,
    )
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

    # UX-54: whether the build succeeded. Always written, even when
    # nothing failed - an absent field has to keep meaning "this producer
    # did not record it", so that captures taken before this existed are
    # never mistaken for known-good runs.
    failed = failed_elements(converter.trace_events)
    run_context["build_outcome"] = {
        "failed_elements": failed,
        "failed_count": len(failed),
    }
    # UX-55: BuildStream's own closing Pipeline Summary. This is what
    # separates the two CI scenarios `bga` has to serve - a nightly with
    # caches off, where every element runs and every signal is about the
    # whole project, from a pre-commit run where most elements are cached
    # and the analysis is only about the few that rebuilt. Nothing else
    # in the capture says which one happened.
    if converter.queue_summary:
        run_context["queue_summary"] = converter.queue_summary
    # UX-110: every task's duration, measured twice - the wrapper's own
    # timestamps against BuildStream's elapsed prefix. It is the
    # resolution of every duration this run reports, and a task the
    # wrapper timed as *shorter* than BuildStream did is provably short
    # rather than merely imprecise. Absent from a raw-format capture,
    # where the timestamps are reconstructed from that same elapsed and
    # the comparison would be a tautology.
    agreement = converter.get_timestamp_agreement()
    if agreement:
        run_context["timestamp_agreement"] = agreement
        if agreement["tasks_shorter_than_bst"]:
            worst = agreement["shorter_than_bst"][0]
            warnings.append(
                f"{agreement['tasks_shorter_than_bst']} of "
                f"{agreement['tasks_compared']} task(s) are reported shorter than "
                f"BuildStream's own timing of them - worst {worst['element']} at "
                f"{worst['span_s']:.3f}s against {worst['bst_elapsed_s']:.0f}s. A "
                f"wrapped log line is stamped when the wrapper read it, so both "
                f"ends of every span carry that lag (UX-110)"
            )
    if failed:
        warnings.append(
            f"{len(failed)} element(s) FAILED in this build "
            f"({', '.join(failed[:5])}{', ...' if len(failed) > 5 else ''}) - "
            "the analysis below describes a build that did not succeed"
        )

    # Run identity (P1-37): embedded identically into all three files so
    # bga's own loader can cross-check they belong to the same extraction.
    # UX-29: run identity records the real resolved value (whichever
    # source won above), not just an operator-typed one - two runs that
    # genuinely differed in native parallelism must not hash identically.
    run_identity = _compute_run_identity(
        project_dir, targets, scheduler, project_refs_provenance,
        native_max_jobs=run_context.get("native_max_jobs"),
    )
    run_context["run_identity"] = run_identity
    graph["run_identity_hash"] = run_identity["manifest_hash"]
    trace["run_identity_hash"] = run_identity["manifest_hash"]

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
        "trackable-ref source - see docs/backlog/tasks/P4-13-strict-mode-project-refs-consistency.md.",
    )
    parser.add_argument(
        "--native-max-jobs", type=int, default=None,
        help="Override the real --max-jobs value the build was invoked with (per-element "
        "internal build-system parallelism, e.g. `make -jN` - a different, unrelated "
        "concept from --builders/this tool's own resource_capacities.PROCESS). Usually "
        "unnecessary: a wrapped log records the real invocation on its own first line and "
        "this value is recovered from it automatically (UX-29). Pass it only to override "
        "that, or for a raw log, which has no invocation line (UX-12).",
    )
    parser.add_argument(
        "--cpu-budget", type=int, default=None,
        help="The number of CPU cores this build is *intended* to use - the operator's "
        "declared envelope, as opposed to the environment's real detected core count "
        "(host_cpu_count). Use this when the detected count doesn't reflect your real "
        "constraint: a cgroup CFS CPU quota (docker --cpus/Kubernetes cpu limits throttle "
        "CPU time, not core affinity, so os.sched_getaffinity can't see it), or simply "
        "wanting to reserve headroom on a shared machine. When set, bga's oversubscription "
        "check treats this as the governing ceiling instead of host_cpu_count (UX-15).",
    )
    parser.add_argument(
        "--memory-budget-mb", type=int, default=None,
        help="The amount of memory (MB) this build is *intended* to use - the operator's "
        "declared envelope. No auto-detection (unlike --cpu-budget's host_cpu_count "
        "counterpart) - purely operator-supplied. When set together with "
        "--estimated-job-memory-mb, bga's memory oversubscription check (UX-21) compares "
        "builders x native-max-jobs x --estimated-job-memory-mb against this budget.",
    )
    parser.add_argument(
        "--estimated-job-memory-mb", type=int, default=None,
        help="A rough, operator-supplied estimate of one concurrent build job's memory "
        "footprint (MB) - a single configurable constant, not a real per-task measurement "
        "(no such measurement source exists in this pipeline, see UX-21). Only meaningful "
        "together with --memory-budget-mb.",
    )
    args = parser.parse_args()

    try:
        summary = extract_run(
            args.project_dir, args.log_path, args.output_dir,
            log_format=args.format, start_time=args.start_time,
            trace_epsilon_us=args.trace_epsilon_us, bst_bin=args.bst_bin,
            strict=args.strict, native_max_jobs=args.native_max_jobs,
            cpu_budget=args.cpu_budget,
            memory_budget_mb=args.memory_budget_mb,
            estimated_job_memory_mb=args.estimated_job_memory_mb,
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
