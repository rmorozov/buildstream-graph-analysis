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
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .bst_log_to_chrome_trace import WrapperTraceConverter, _resolve_start_time_us
from .chrome_trace_to_bga_trace import (
    chrome_events_to_bga_spans,
    failed_elements,
    invocation_wall_clock,
)
from .bst_show_to_graph import extract_graph
from ._run_context_common import (add_cpu_capacity_fields, add_host_manifest,
                                  add_producer,
                                  add_memory_capacity_fields)


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
    interrupted: bool = False,
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
    # UX-186: which machine measured this. Every capture, so that two
    # runs can be told apart - or told to be the same - rather than
    # compared on the assumption that they are.
    add_host_manifest(run_context)
    add_producer(run_context)
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
        # UX-157: an interrupted build is incomplete for exactly the same
        # reason a failed one is - elements that never ran contribute no
        # time, so its duration is not a measurement. Recorded as its own
        # flag rather than as a fake failed element, because nothing
        # *failed*; the user stopped it.
        "interrupted": bool(interrupted),
    }
    # UX-185: whether the machine slept while this ran. Read from the
    # wrapper's own clock pair, so a log kept and extracted later still
    # carries the answer. Absent from every log written before UX-185,
    # and those extract exactly as they did - a capture too old to have
    # looked is not a capture that slept.
    from bga import suspend as _suspend
    from .bst_run_wrapped import read_clock_pairs

    pairs = read_clock_pairs(log_path) if log_format != "raw" else {}
    suspension = _suspend.slept(pairs.get("start"), pairs.get("end"))
    if suspension:
        run_context["build_outcome"]["suspended"] = suspension
    # UX-164 item 3: `scheduled = processed + skipped + failed` counted
    # cache hits as casualties - a run with 0 processed, 6 skipped and 1
    # failed read as "0 of 7 scheduled elements built", overstating the
    # damage seven-fold and sending a user hunting for six lost builds.
    # The three numbers mean different things, so carry all three.
    # UX-177 item 3: and carried in *one* place. These three were also
    # copied into `build_outcome`, where nothing read them - the
    # `build_failed` violation derives them from `queue_summary` below,
    # which is the recorded source. Two spellings of one number is how a
    # drift finding starts, so the copy is gone rather than wired up.
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
    # UX-177 item 4: an extraction into an existing snapshot overwrites
    # files in place, which moves no directory mtime - so `UX-168`'s size
    # memo, keyed on exactly that, would survive a re-extraction that
    # changed the snapshot's size. Dropped here rather than made
    # cleverer: the producer knows it just rewrote the run.
    _drop_size_memo(out_dir)
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
    # UX-171: which repository feeds which elements. Written here
    # because this is the one moment both the project and the run are in
    # hand - `bga analyze` reads a run directory and nothing else, and
    # keeping it that way is what makes a published capture analyzable
    # anywhere.
    inventory = build_source_inventory(
        project_dir, [element["uid"] for element in graph["elements"]])
    (out_dir / "sources.json").write_text(json.dumps(inventory, indent=2))

    return {
        "targets": targets,
        "elements": len(graph["elements"]),
        "dependencies": len(graph["dependencies"]),
        "spans": len(spans),
        "output_dir": str(out_dir),
        "warnings": warnings,
    }


def _drop_size_memo(run_dir: Path) -> None:
    """Invalidate `UX-168`'s snapshot size memo, if this run is in one.

    The memo lives at `<snapshot>/.size` and the run directory is
    `<snapshot>/run`, so this looks one level up - and does nothing at
    all for a run directory that is not inside a store, which is most
    of them.
    """
    from bga.run_store import SIZE_CACHE_NAME

    try:
        (run_dir.parent / SIZE_CACHE_NAME).unlink()
    except OSError:
        pass


def _junction_subproject(project_dir: str, junction_uid: str) -> Optional[str]:
    """Where a junction's subproject is checked out, if it is on disk.

    `UX-182`. Only a `local` source can be resolved without fetching -
    which is the common case for a project being actively built, since
    the subproject is right there in the tree. A junction sourced from
    git that has not been fetched genuinely is not readable, and is
    reported as such rather than guessed at.
    """
    from .bst_native_build_tracer import elements_dir_for, read_element_yaml

    data = read_element_yaml(os.path.join(elements_dir_for(project_dir), junction_uid))
    if not data or data.get("kind") != "junction":
        return None
    for source in data.get("sources") or []:
        if isinstance(source, dict) and source.get("kind") == "local":
            path = source.get("path")
            if path:
                candidate = os.path.join(project_dir, path)
                if os.path.isdir(candidate):
                    return candidate
    return None


def _resolve_junctioned(project_dir: str, uid: str) -> Tuple[Optional[str], Optional[str], str]:
    """`(subproject_dir, element_name, junction_prefix)` for a uid.

    A uid may nest (`a.bst:b.bst:c.bst`), so this walks left to right,
    resolving each junction in the project the previous step landed in.
    Returns `(None, None, prefix)` for the first junction it cannot
    reach, so the caller can name it.
    """
    parts = uid.split(":")
    current = project_dir
    prefix_parts: List[str] = []
    for junction in parts[:-1]:
        subproject = _junction_subproject(current, junction)
        if subproject is None:
            return None, None, ":".join(prefix_parts + [junction])
        current = subproject
        prefix_parts.append(junction)
    return current, parts[-1], ":".join(prefix_parts)


def build_source_inventory(project_dir: str, element_uids) -> dict:
    """`sources/v1` for the elements this run built (`UX-171`).

    Read from the `.bst` files, with the census's own memoised reader,
    for the reason the census reads them: this must work against a
    project directory without invoking BuildStream, and `bst show` has
    no symbol for a source's url.

    `UX-182`: a uid carrying a junction prefix
    (`junction.bst:element.bst`) is a *subproject's* element, and its
    file lives in that subproject - which is on disk whenever the
    junction is sourced locally, the common case for a project being
    actively built. Those are walked into and read. A junction that is
    genuinely not there (sourced from a git the tree has not fetched)
    stays `unreadable`, named, per `UX-171`'s own no-silent-skips rule.

    **Identities cross the boundary differently by keying.** A
    ref-keyed resource - a repository url - means the same repository
    whichever project names it, so it is left global and two
    subprojects sourcing one monorepo group together, which is the
    whole question this axis answers. A content-keyed resource is a
    path relative to *its own* project, so it is prefixed with the
    junction it came from; without that, `files/src` in two
    subprojects would report as one shared directory that does not
    exist.
    """
    from bga import sources as sources_module
    from .bst_native_build_tracer import elements_dir_for, read_element_yaml

    per_element = {}
    complaints = {}
    for uid in element_uids:
        subproject, name, prefix = _resolve_junctioned(project_dir, uid)
        if subproject is None:
            complaints[uid] = [
                f"junction {prefix} is not checked out here - its subproject's "
                f"sources cannot be read without fetching it"
            ]
            continue
        data = read_element_yaml(os.path.join(elements_dir_for(subproject), name))
        resources, notes = sources_module.resources_from_element(data)
        resources, symlink_notes = _resolve_symlinked(subproject, resources)
        notes = list(notes) + symlink_notes
        if prefix:
            resources = [_qualify(resource, prefix) for resource in resources]
        if resources:
            per_element[uid] = resources
        if notes:
            complaints[uid] = notes
    return sources_module.build_inventory(per_element, complaints)


def _resolve_symlinked(project_dir: str, resources):
    """UX-184 item 2: one directory, one identity, however it is spelled.

    A project that stages `vendor/lib` where `vendor/lib` is a symlink
    to `files/lib` is staging the same bytes as an element that names
    `files/lib` directly - and reported them as two resources, so the
    blast the table exists to show was halved for exactly the projects
    that use a checkout layout.

    Resolved at inventory time, because that is the one moment the
    project is on disk. `declared` keeps what the recipe wrote; the
    identity becomes the real directory. A link pointing *out* of the
    project has no project-relative identity at all, so it is a
    complaint rather than an identity outside the tree - the same
    reasoning as `UX-184`'s absolute-path case.
    """
    resolved = []
    notes = []
    root = os.path.realpath(project_dir)
    for resource in resources:
        if resource.get("keying") != "content":
            resolved.append(resource)
            continue
        identity = resource.get("identity") or ""
        real = os.path.realpath(os.path.join(project_dir, identity))
        if real == os.path.join(root, identity) or not os.path.exists(real):
            # Not a link, or not on disk to check - either way the
            # declared path is the best identity available.
            resolved.append(resource)
            continue
        try:
            relative = os.path.relpath(real, root)
        except ValueError:
            relative = ".."
        if relative.split(os.sep)[0] == "..":
            notes.append(
                f"`{resource.get('kind')}` source {identity!r} resolves to "
                f"{real!r}, outside the project - it has no project-relative "
                f"identity, so its blast cannot be grouped with anything")
            continue
        linked = dict(resource)
        linked["identity"] = relative
        resolved.append(linked)
    return resolved, notes


def _qualify(resource: dict, prefix: str) -> dict:
    """Namespace a content-keyed identity to the junction it came from."""
    if resource.get("keying") != "content":
        return resource
    qualified = dict(resource)
    qualified["identity"] = f"{prefix}:{resource['identity']}"
    return qualified


def _CompactRawHelp(prog):
    """UX-158: one shared compact help layout, imported lazily so this
    module stays runnable on its own."""
    from bga.help_format import CompactRawHelp
    return CompactRawHelp(prog)

def main() -> int:
    parser = argparse.ArgumentParser(
        formatter_class=_CompactRawHelp,
        description="Produce a complete bga-ready run directory (run-context.json + "
        "graph.json + trace.json) from a real BuildStream project + log in one step.",
    )
    parser.add_argument("project_dir", help="Path to the BuildStream project directory.")
    parser.add_argument("log_path", help="Path to the build log (wrapped or raw).")
    parser.add_argument("output_dir", help="Where to write the run directory.")
    parser.add_argument(
        "--format", choices=("auto", "wrapped", "raw"), default="auto",
        help="Input log format - same semantics as bst_log_to_chrome_trace.py.",
    )
    parser.add_argument(
        "--start-time", default=None,
        help='ISO-8601 timestamp anchor for raw-format elapsed timestamps; defaults to the log file\'s mtime.'
    )
    parser.add_argument(
        "--trace-epsilon-us", type=int, default=50000,
        help="Quantization epsilon in microseconds (Part 3.2 default: 50000).",
    )
    parser.add_argument(
        "--bst-bin", default="bst",
        help="Path to the bst executable.",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help='Fail loudly (instead of the default best-effort warning) unless the project uses ref-storage: project.refs and project.refs itself has no uncommitted changes (P4-13).'
    )
    parser.add_argument(
        "--native-max-jobs", type=int, default=None,
        help='Override the real --max-jobs the build ran with - `make -jN`\n'
             'inside each sandbox, which is a different thing from\n'
             '--builders. Usually recovered from a wrapped log (UX-29).'
    )
    parser.add_argument(
        "--cpu-budget", type=int, default=None,
        help='The number of CPU cores this build is *intended* to use - the operator\'s declared envelope, as opposed to the environment\'s real detected core count (host_cpu_count).'
    )
    parser.add_argument(
        "--memory-budget-mb", type=int, default=None,
        help='The amount of memory (MB) this build is *intended* to use - the operator\'s declared envelope.'
    )
    parser.add_argument(
        "--estimated-job-memory-mb", type=int, default=None,
        help='A rough, operator-supplied estimate of one concurrent build job\'s memory footprint (MB) - a single configurable constant, not a real per-task measurement (no such measurement source exists in this pipeline, see UX-21).'
    )
    parser.add_argument(
        "--interrupted", action="store_true",
        help="Record that this log's build was interrupted, so the run declares "
        "itself unfinished. Needed when re-running this command from the hint an "
        "interrupted capture printed; `bga snapshot` sets it for you."
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
            # UX-175: `extract_run` has taken this since UX-157 and no
            # command line could set it, so the recovery path UX-163
            # printed produced a run that had forgotten it was partial.
            interrupted=args.interrupted,
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
