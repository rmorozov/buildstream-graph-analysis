"""Shared run-context/v9 assembly pieces used by both real producer tools
(tools/bst_run_context.py, tools/bst_extract_run.py) - UX-18.

Split out because the two tools' capabilities had silently diverged:
tools/bst_extract_run.py picked up native_max_jobs/host_cpu_count
(UX-12) and cpu_budget (UX-15), but tools/bst_run_context.py - the other
of the two producer paths docs/ingestion-pipeline.md documents as
equally valid - never did, even though both build the exact same
run-context/v9 shape from a real BuildStream log. Centralizing the
shared piece here means a future addition to one reaches both instead of
requiring a second, easy-to-forget edit.
"""
import os


def host_cpu_count():
    """The real number of CPU cores available to this process (UX-12) -
    `os.sched_getaffinity` where available (Linux only, but correct
    under a cgroup/container CPU-share limit, exactly the kind of
    environment `bga`'s own CI runs in - a plain `os.cpu_count()` would
    report the host's full core count even when this process is
    actually confined to fewer), falling back to `os.cpu_count()`
    elsewhere. Returns None if neither is available (unlikely, but
    honest rather than fabricating a number)."""
    if hasattr(os, "sched_getaffinity"):
        try:
            return len(os.sched_getaffinity(0))
        except OSError:
            pass
    return os.cpu_count()


def add_cpu_capacity_fields(run_context: dict, native_max_jobs: int = None, cpu_budget: int = None) -> None:
    """Mutates `run_context` in place, adding `native_max_jobs` (UX-12),
    `host_cpu_count` (UX-12, always auto-detected), and `cpu_budget`
    (UX-15) - all optional fields distinct from run-context/v9's own
    spec-mandated `max_jobs` (which actually means `builders`, see
    tools/bst_log_to_chrome_trace.py's get_scheduler_config docstring).

    `native_max_jobs`/`cpu_budget` are purely operator-supplied (neither
    is visible in a BuildStream log itself) - omitted when not given,
    never defaulted to a guessed value. `host_cpu_count` is always
    queried directly from the extraction environment; omitted only if
    detection itself is unavailable.
    """
    if native_max_jobs is not None:
        run_context["native_max_jobs"] = native_max_jobs
    detected_host_cpu_count = host_cpu_count()
    if detected_host_cpu_count is not None:
        run_context["host_cpu_count"] = detected_host_cpu_count
    if cpu_budget is not None:
        run_context["cpu_budget"] = cpu_budget


def add_memory_capacity_fields(
    run_context: dict, memory_budget_mb: int = None, estimated_job_memory_mb: int = None,
) -> None:
    """Mutates `run_context` in place, adding `memory_budget_mb`/
    `estimated_job_memory_mb` (UX-21) - both purely operator-supplied,
    same pattern as `native_max_jobs`/`cpu_budget` above: omitted when
    not given, never defaulted to a guessed value. Unlike `host_cpu_count`,
    there is no auto-detection tier here at all (UX-21's own doc scopes
    that out deliberately) - real per-task memory measurement has no
    source in this ingestion pipeline, so both fields stay a purely
    config-driven, explicitly-labeled estimate.
    """
    if memory_budget_mb is not None:
        run_context["memory_budget_mb"] = memory_budget_mb
    if estimated_job_memory_mb is not None:
        run_context["estimated_job_memory_mb"] = estimated_job_memory_mb
