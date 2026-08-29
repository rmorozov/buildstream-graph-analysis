"""Shared run-context/v9 assembly pieces used by both real producer tools
(tools/bst_run_context.py, tools/bst_extract_run.py) - UX-18.

Split out because the two tools' capabilities had silently diverged:
tools/bst_extract_run.py picked up native_max_jobs/host_cpu_count
(UX-12) and cpu_budget (UX-15), but tools/bst_run_context.py - the other
of the two producer paths docs/spec/ingestion-pipeline.md documents as
equally valid - never did, even though both build the exact same
run-context/v9 shape from a real BuildStream log. Centralizing the
shared piece here means a future addition to one reaches both instead of
requiring a second, easy-to-forget edit.
"""
import os
from typing import Optional


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


# UX-29 provenance values for `native_max_jobs_source`. `bga`'s own
# capacity guards certify against this number, so where it came from is
# part of the claim - the same reasoning behind UX-17's
# `effective_cpus_source`.
NATIVE_MAX_JOBS_OPERATOR_DECLARED = "operator_declared"
NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION = "parsed_from_invocation"
# `UX-377`: the third route, and the one every default capture takes.
# `--max-jobs` is a *top-level* `bst` option; it is also settable in
# `$XDG_CONFIG_HOME/buildstream.conf` as `build: max-jobs:`, and its
# default of 0 means the host's core count. Only the first of those
# three reaches a command line, so `parsed_from_invocation` recovered
# the value on exactly the route nobody uses and `None` on the two that
# people do - while `graph.json`, in the same snapshot, held the
# resolved value for every element.
NATIVE_MAX_JOBS_RESOLVED_FROM_GRAPH = "resolved_from_graph"


def typical_resolved_max_jobs(graph: dict) -> Optional[int]:
    """The run's own native `max-jobs`, from the resolved per-element
    values `bst show` reported (`UX-31`).

    **The maximum, not the mean or the mode**, and the same rule
    `bga/structural/serialization_points.py` uses for `typical_max_jobs`
    - deliberately, because the two are the same quantity and having
    them disagree would be the defect. An element carrying
    `notparallel: True` resolves to 1 while its siblings resolve to the
    project value; the run-level figure is what the run *generally*
    gave, and the pinned element is a finding against it rather than a
    reason to lower it.

    `None` where no element reports one, which is a graph extracted from
    a `bst` too old to have `max-jobs` in `%{vars}` - reported as absent
    rather than guessed, as everything in this module is.
    """
    values = [element.get("max_jobs") for element in (graph or {}).get(
        "elements", [])]
    resolved = [value for value in values if isinstance(value, int)]
    return max(resolved) if resolved else None


def add_cpu_capacity_fields(
    run_context: dict,
    native_max_jobs: int = None,
    cpu_budget: int = None,
    parsed_native_max_jobs: int = None,
    graph_native_max_jobs: int = None,
) -> None:
    """Mutates `run_context` in place, adding `native_max_jobs` (UX-12),
    `native_max_jobs_source` (UX-29), `host_cpu_count` (UX-12, always
    auto-detected), and `cpu_budget` (UX-15) - all optional fields
    distinct from run-context/v9's own spec-mandated `max_jobs` (which
    actually means `builders`, see
    tools/bst_log_to_chrome_trace.py's get_scheduler_config docstring).

    `native_max_jobs` was originally documented as purely operator-
    supplied, on the grounds that it is not visible in a BuildStream log.
    That is true of BuildStream's own output but not of a *wrapped* log,
    whose very first line records the real invocation
    (`Executing command: bst --builders 4 --max-jobs 4 build all.bst`) -
    UX-29, filed after finding that the entire UX-12/15/16/17/21 capacity-
    guard chain sat inert on every run the documented pipeline produced,
    because nobody passes a flag to re-declare a value the tool already
    had. `parsed_native_max_jobs` carries that recovered value.

    An explicit operator-supplied `native_max_jobs` always wins over the
    parsed one (an operator overriding what the command line said is
    making a deliberate statement, e.g. correcting for a wrapper script
    that rewrites flags), and the winner is recorded in
    `native_max_jobs_source` so a consumer can tell the two apart.
    `graph_native_max_jobs` (`UX-377`) is the third and last tier: the
    typical resolved `max-jobs` from the graph beside this run context,
    used when the invocation carried no flag - which is every default
    capture and every capture whose value came from a user config.

    None of the three present -> both fields omitted, never a guessed
    default.

    `cpu_budget` stays purely operator-supplied. `host_cpu_count` is
    always queried directly from the extraction environment; omitted only
    if detection itself is unavailable.
    """
    if native_max_jobs is not None:
        run_context["native_max_jobs"] = native_max_jobs
        run_context["native_max_jobs_source"] = NATIVE_MAX_JOBS_OPERATOR_DECLARED
    elif parsed_native_max_jobs is not None:
        run_context["native_max_jobs"] = parsed_native_max_jobs
        run_context["native_max_jobs_source"] = NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION
    elif graph_native_max_jobs is not None:
        # `UX-377`: last, so a value on the command line still wins and
        # `native_max_jobs_source` keeps saying which of the three the
        # published number came from. This is the branch a default
        # `bga snapshot` takes, and before it the whole
        # `UX-12`/`15`/`16`/`17`/`21` capacity chain reported
        # "missing: native_max_jobs" with the number in the next file.
        run_context["native_max_jobs"] = graph_native_max_jobs
        run_context["native_max_jobs_source"] = NATIVE_MAX_JOBS_RESOLVED_FROM_GRAPH
    detected_host_cpu_count = host_cpu_count()
    if detected_host_cpu_count is not None:
        run_context["host_cpu_count"] = detected_host_cpu_count
    if cpu_budget is not None:
        run_context["cpu_budget"] = cpu_budget


def host_memory_mb():
    """The machine's total RAM in MB, or None where it cannot be read.

    `UX-21` scoped memory auto-detection out on the grounds that "real
    per-task memory measurement has no source in this ingestion
    pipeline". `UX-63` gave it one - Plane 2 records each process's peak
    RSS from `getrusage` - so the reason for that scoping no longer
    holds, and `UX-104` needs the *denominator* to turn measured peaks
    into a builders answer.

    Read from `/proc/meminfo`, which is the machine's own figure. Not
    `os.sysconf`, which reports the host's pages even inside a container
    with a lower cgroup limit - the same class of mistake
    `host_cpu_count` avoids by preferring `sched_getaffinity`. A cgroup
    *memory* limit is a further refinement this does not yet read, and
    the field is named `host_memory_mb` rather than `memory_budget_mb`
    so the two never get confused: the operator's declared budget stays
    separate and still wins where it is set.
    """
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def add_host_manifest(run_context: dict) -> None:
    """UX-186: which machine measured this run.

    `host_cpu_count` and `host_memory_mb` above already described the
    machine in two numbers, which call a laptop and a build runner with
    the same core count the same host. The manifest is the rest of that
    description, under one versioned key, so `bga compare` can say
    whether two runs are even about the same machine - it performed no
    host check of any kind before this.

    Best-effort by construction: every field degrades to `None`, and a
    failure to collect never fails an extraction. A capture that could
    not read its own `/proc` still has a run directory.

    **Not** `host`. `UX-186` asked for the manifest under that key, and
    `--host` has published an operator-supplied *identifier* there since
    `UX-12`; taking it would silently redefine a field consumers already
    read, which is the exact drift `UX-190` was filed about. The two
    coexist: `host` names the machine, `host_manifest` describes it.
    """
    from bga import hostinfo

    try:
        run_context["host_manifest"] = hostinfo.collect()
    except Exception:  # noqa: BLE001 - provenance must not break a capture
        pass


def add_producer(run_context: dict) -> None:
    """UX-249: which build of `bga` wrote this run directory.

    The same shape and the same best-effort rule as
    `add_host_manifest` above, for the same reason: a run directory is
    re-read months later by a different build, and until this landed
    nothing in it said which build that was.

    It records the whole contract set rather than the subset a run
    directory depends on - see `bga/producer.py` for why - and it makes
    no refusal. `UX-250` owns what to refuse on; this only has to make
    the answer available, and a recording that arrives after the policy
    that reads it is a policy with nothing to read.
    """
    from bga import producer

    producer.add(run_context)


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
    # UX-104: the host's own total RAM, always auto-detected, so a
    # capture carries the denominator its measured peaks need. Distinct
    # from `memory_budget_mb` above, which is what the operator *intends*
    # to use and still governs UX-21's oversubscription check.
    detected_host_memory_mb = host_memory_mb()
    if detected_host_memory_mb is not None:
        run_context["host_memory_mb"] = detected_host_memory_mb
    if memory_budget_mb is not None:
        run_context["memory_budget_mb"] = memory_budget_mb
    if estimated_job_memory_mb is not None:
        run_context["estimated_job_memory_mb"] = estimated_job_memory_mb
