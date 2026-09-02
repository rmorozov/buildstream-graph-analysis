"""
Timestamp normalization module.

Implements Part 3: Time Representation and Trace Normalization.

Key principles:
- All timestamps use int64 microseconds
- Timestamps are quantized to epsilon grid during ingestion
- Finish times are immutable; duration absorbs corrections
"""

import logging
from typing import List, Dict, Tuple

from ..ingest.models import (
    Graph,
    NormalizedTask,
    TaskKind,
    TaskSpan,
    Trace,
    DependencyEdge,
)

logger = logging.getLogger(__name__)


#: `UX-481`: the task kinds that put an element's artifact on this
#: machine, in the order they win when an element has both.
#:
#: A `depends:` edge means the downstream element's work needs the
#: upstream element's artifact to *exist locally*, and there are two
#: ways that happens: BuildStream built it, or BuildStream pulled it
#: from a remote cache. A cache hit produces a `PULL` and **no**
#: `BUILD` at all, so a map keyed on `BUILD` alone silently drops the
#: edge for every pulled dependency - which is the common case in CI
#: and the shape `run-mode-incremental` exists to name.
#:
#: BUILD wins where both exist: a pull that was followed by a build did
#: not produce the artifact the dependent consumed.
#:
#: Every other kind stays out, for the reason `P1-27` recorded: a
#: trailing `PUSH` finishes after the artifact exists and gating on it
#: over-constrains ready times, and `TRACK`/`FETCH` are about sources
#: rather than artifacts.
_ARTIFACT_TASK_KINDS = (TaskKind.BUILD, TaskKind.PULL)


def _element_artifact_task(
    normalized_spans: List[Tuple[TaskSpan, int, int]],
) -> Dict[str, Tuple[TaskSpan, int]]:
    """Map element_uid -> the span that put its artifact here, and its
    quantized finish.

    One source of truth for both questions the module asks about an
    upstream element - *when* was its artifact ready
    (`_element_build_finish`, for ready times) and *which task key*
    should a dependent wait on (`clamp_task_starts`, for replay). They
    were two maps built from one `if` each, and `UX-481` found them
    wrong in the same way at the same time.
    """
    best: Dict[str, Tuple[TaskSpan, int]] = {}
    for span, _q_start, q_finish in normalized_spans:
        kind = span.task_key.task_kind
        if kind not in _ARTIFACT_TASK_KINDS:
            continue
        uid = span.task_key.element_uid
        held = best.get(uid)
        if held is None or _ARTIFACT_TASK_KINDS.index(kind) < \
                _ARTIFACT_TASK_KINDS.index(held[0].task_key.task_kind):
            best[uid] = (span, q_finish)
    return best


def _element_build_finish(normalized_spans: List[Tuple[TaskSpan, int, int]]) -> Dict[str, int]:
    """
    Map element_uid -> the (quantized) finish of the task that produced
    its artifact here (Part 32.2's `depends:` semantics: a downstream
    element's work needs the upstream element's artifact to exist, not
    any of its other task kinds - the same real-world semantics
    bga/analyzer.py::_compute_attribution's explicit_predecessors
    (P1-03) and this module's own clamp_task_starts (P1-26) already
    use). An element with no such task contributes no entry, rather
    than a wrong one - shared by compute_ready_times and
    validate_ordering so both apply the identical predecessor source
    (P1-27: they previously each independently computed a max-across-
    every-task-kind finish, which could be later than the element's
    own BUILD finish - e.g. a trailing PUSH - over-constraining
    ready times for tasks that don't actually depend on it).

    `UX-481` widened "its own BUILD" to "the task that produced its
    artifact" - see `_ARTIFACT_TASK_KINDS`. The name is kept because
    every caller reads it as "when could a dependent start", which is
    what it has always meant and now answers on a cache hit too.
    """
    return {uid: finish
            for uid, (_span, finish) in _element_artifact_task(normalized_spans).items()}


def quantize_timestamp(ts_us: int, epsilon_us: int) -> int:
    """
    Quantize a timestamp to the epsilon grid (Part 3.2).

    Rounds to the nearest multiple of epsilon using pure integer
    arithmetic (P2-07) - the previous implementation did
    `round(ts_us / epsilon_us) * epsilon_us`, a real (if practically
    harmless for realistic microsecond-range timestamps) floating-point
    division ahead of `round()`, in a code path Part 3.1 explicitly says
    must have none ("No floating-point arithmetic is used for timeline
    accounting").

    Documented deterministic tie rule (Part 3.2's own requirement -
    "the implementation must use a documented deterministic rounding
    rule", not merely the conceptual round(ts/epsilon)*epsilon formula):
    exact ties (`ts_us` precisely halfway between two grid points) round
    up (away from zero for the non-negative timestamps this codebase
    always operates on). This is a deliberate choice, not an implicit
    inheritance of Python float `round()`'s default behavior (round-
    half-to-even / "banker's rounding", which the previous docstring
    here incorrectly described as "round toward zero" - it does neither
    consistently). No currently-tested case in this codebase depends on
    exact-tie behavior; this only changes what an exact tie resolves to,
    not any already-tested boundary.

    Derivation: round-half-up of ts_us/epsilon_us is
    floor(ts_us/epsilon_us + 1/2) = floor((2*ts_us + epsilon_us) /
    (2*epsilon_us)) - exact integer floor division, no float involved,
    correct for any epsilon_us (odd or even).

    Args:
        ts_us: Timestamp in microseconds
        epsilon_us: Quantization epsilon in microseconds

    Returns:
        Quantized timestamp in microseconds
    """
    return ((2 * ts_us + epsilon_us) // (2 * epsilon_us)) * epsilon_us


def normalize_timestamps(
    spans: List[TaskSpan],
    epsilon_us: int = 50000,
) -> List[Tuple[TaskSpan, int, int]]:
    """
    Normalize timestamps for all task spans (Part 3.2).
    
    Applies quantization to start and finish timestamps.
    
    Args:
        spans: List of task spans
        epsilon_us: Quantization epsilon in microseconds (default 50ms)
        
    Returns:
        List of tuples: (original_span, quantized_start, quantized_finish)
    """
    normalized = []
    
    for span in spans:
        # Quantize start and finish independently
        q_start = quantize_timestamp(span.ts_us, epsilon_us)
        q_finish = quantize_timestamp(span.finish_us, epsilon_us)
        
        normalized.append((span, q_start, q_finish))
    
    return normalized


def compute_ready_times(
    normalized_spans: List[Tuple[TaskSpan, int, int]],
    dependencies: List[DependencyEdge],
) -> Dict[str, int]:
    """
    Compute ready times for all tasks based on dependency graph (Part 7).

    For task t:
        ready_time(t) = max(finish(p)) for p in predecessors(t)

    If a task has no predecessors, its ready time is its own start time
    (meaning it was ready as soon as it could have started).

    Cross-element dependency gating applies only to a task's own BUILD
    task (P1-27: a real `depends:` edge only constrains the downstream
    element's *build*, per Part 32.2 - it never gates TRACK/FETCH/PUSH,
    which have no causal relationship to an upstream dependency). Those
    non-BUILD tasks fall into the same "no predecessors" case as a
    genuinely independent element - ready at their own start time - not
    a new behavior, the same fallback root elements already used.

    Gating also only applies to `build`-type edges (P4-11, Part 5.1/32.2):
    a `runtime`-only dependency's product is only needed at *runtime*,
    not staged before the successor's build starts - per BuildStream's
    own semantics, "an element's runtime dependencies are not available
    to the element at build time." A `runtime`-only edge therefore does
    not gate the successor's BUILD readiness at all, same as having no
    edge for readiness purposes (it still counts fully for structural
    analysis - reachability, blast radius, leaf/deferrability, Part
    24/25 - which reads `graph.dependencies` directly, unfiltered).

    Args:
        normalized_spans: Output from normalize_timestamps
        dependencies: List of dependency edges

    Returns:
        Dict mapping task key string to ready time in microseconds
    """
    # Build predecessor map using element UIDs - build-gating edges only.
    predecessors: Dict[str, List[str]] = {}  # successor -> list of predecessor element uids

    for dep in dependencies:
        if dep.dependency_type == "runtime":
            continue
        if dep.successor not in predecessors:
            predecessors[dep.successor] = []
        predecessors[dep.successor].append(dep.predecessor)

    element_build_finish = _element_build_finish(normalized_spans)

    # Compute ready times
    ready_times: Dict[str, int] = {}

    for span, q_start, q_finish in normalized_spans:
        task_key_str = str(span.task_key)
        element_uid = span.task_key.element_uid

        preds = predecessors.get(element_uid) if span.task_key.task_kind == TaskKind.BUILD else None
        if preds:
            pred_finish_times = [
                element_build_finish[pred] for pred in preds if pred in element_build_finish
            ]
            ready_times[task_key_str] = max(pred_finish_times) if pred_finish_times else q_start
        else:
            # No predecessors (or not a BUILD task) - ready at own start time
            ready_times[task_key_str] = q_start

    return ready_times


def validate_ordering(
    normalized_spans: List[Tuple[TaskSpan, int, int]],
    dependencies: List[DependencyEdge],
    ready_times: Dict[str, int],
) -> List[dict]:
    """
    Validate ordering constraints (Part 3.3).

    For each dependency edge predecessor -> task:
        finish(predecessor's BUILD) <= start(successor's BUILD)

    The only task-kind pairing a real `depends:` edge actually
    constrains (P1-27 - see compute_ready_times and
    _element_build_finish). Checking the successor's *earliest* task
    of any kind - as this used to - flagged spurious violations
    whenever a TRACK/FETCH task legitimately started before the
    dependency's build finished, which is normal, not an ordering bug.

    Only `build`-type edges are checked (P4-11) - a `runtime`-only
    dependency's BUILD is not required to finish before the successor's
    BUILD starts (see compute_ready_times), so it would be a false
    positive to flag that as an ordering violation.

    After quantization, small negative gaps should disappear.
    Large negative gaps indicate ordering violations.

    Args:
        normalized_spans: Output from normalize_timestamps
        dependencies: List of dependency edges
        ready_times: Ready times from compute_ready_times

    Returns:
        List of violation records
    """
    violations = []

    element_build_finish = _element_build_finish(normalized_spans)
    build_start_by_element: Dict[str, int] = {}
    for span, q_start, _q_finish in normalized_spans:
        if span.task_key.task_kind == TaskKind.BUILD:
            build_start_by_element[span.task_key.element_uid] = q_start

    # Check each build-gating dependency
    for dep in dependencies:
        if dep.dependency_type == "runtime":
            continue
        pred_finish = element_build_finish.get(dep.predecessor)
        succ_start = build_start_by_element.get(dep.successor)

        if pred_finish is not None and succ_start is not None and pred_finish > succ_start:
            logger.debug(
                "Ordering violation: %s finishes at %d after %s starts at %d (gap %dus)",
                dep.predecessor, pred_finish, dep.successor, succ_start,
                succ_start - pred_finish,
            )
            violations.append({
                'type': 'ordering_violation',
                'predecessor': dep.predecessor,
                'successor': dep.successor,
                'predecessor_finish': pred_finish,
                'successor_start': succ_start,
                'gap_us': succ_start - pred_finish,  # Negative means violation
            })

    return violations


def clamp_task_starts(
    normalized_spans: List[Tuple[TaskSpan, int, int]],
    ready_times: Dict[str, int],
    graph: Graph,
) -> Tuple[List[NormalizedTask], List[dict]]:
    """
    Clamp task starts to their ready times (Part 3.4).

    When start < ready after normalization:
        start' = ready
        finish' = finish (immutable)
        duration' = finish' - start'

    A genuine ordering violation (ready_us pushed past the span's own raw
    finish, not merely quantization noise - Part 3.3's own carve-out)
    would otherwise make this clamp produce clamped_start > clamped_finish,
    a structurally invalid negative-duration task (P1-36). That case is
    detected here and the task is excluded from the returned list -
    surfaced as a violation instead, never silently constructed - per
    Part 3.3's "no hidden runtime correction" and this codebase's general
    "no silent correction" discipline elsewhere (e.g. classify_resource_wait
    reporting UNKNOWN/ambiguous rather than fabricating a holder).

    Args:
        normalized_spans: Output from normalize_timestamps
        ready_times: Ready times from compute_ready_times
        graph: Dependency graph

    Returns:
        Tuple of (NormalizedTask objects, violation records for tasks
        excluded because clamping would have produced negative duration)
    """
    # Map element_uid -> its own BUILD task key (Part 32.2 - a `depends:`
    # edge means the downstream element's work needs the upstream
    # element's BUILD to have completed, not whichever task kind the
    # downstream task itself happens to be - the same real-world
    # semantics bga/analyzer.py::_compute_attribution's
    # explicit_predecessors already uses, Part 5.2/P1-03). An upstream
    # element with no BUILD task contributes no edge, rather than a
    # wrong one. NormalizedTask.dependencies is only read by
    # bga/replay/scheduler.py; getting it wrong under-constrains
    # replay's readiness gating, which can under-schedule the replay
    # makespan T_C below the certified LB, violating I2 (P1-26).
    #
    # Only build-gating edges are included (P4-11) - a runtime-only
    # dependency doesn't need to be staged before the successor's build
    # starts (see compute_ready_times's identical filter), so replay
    # must not gate the successor's readiness on it either.
    # `UX-481`: the task that put each element's artifact here, which is
    # its BUILD where it was built and its PULL where it was pulled -
    # see `_ARTIFACT_TASK_KINDS`. This was keyed on BUILD alone, so a
    # dependency that came off the cache offered no task to wait for and
    # the edge vanished: on `tests/fixtures/a_build_that_pulls` the
    # replay started `lib3`'s 9s build at t=0, before the three 1s pulls
    # it consumes had finished, and scored `T_C (9000000) < LB
    # (12000000)` - the same under-constraint this comment warns about,
    # one edge over from the one `UX-60` closed.
    build_task_by_element: Dict[str, str] = {
        uid: str(span.task_key)
        for uid, (span, _finish) in _element_artifact_task(normalized_spans).items()
    }
    # UX-60: an element's own FETCH, which its BUILD must wait for.
    # BuildStream cannot run build commands before the element's sources
    # are staged, and until now nothing in the replay's readiness model
    # said so - a BUILD task carried edges to its *dependencies'* builds
    # and none to its own fetch, so replay was free to start it at t=0.
    # That was invisible while no floor modelled the ordering either;
    # `UX-60`'s two-stage T-infinity does, and on the one checked-in
    # fixture with real FETCH durations it immediately produced
    # `T_C (118000000) < LB (122000000)` - the exact under-constraint
    # this function's own comment warns about, found by a floor finally
    # disagreeing with it.
    fetch_task_by_element: Dict[str, str] = {}
    for span, _q_start, _q_finish in normalized_spans:
        if span.task_key.task_kind == TaskKind.FETCH:
            fetch_task_by_element[span.task_key.element_uid] = str(span.task_key)

    # `UX-531`: the build-gating edges, indexed by successor once. The
    # loop below used to scan every edge per task - 4,002 x 11,800 on the
    # seeded run - and the filter and the order are the ones it applied.
    build_gating_predecessors: Dict[str, List[str]] = {}
    for dep_edge in graph.dependencies:
        if dep_edge.dependency_type == "runtime":
            continue
        build_gating_predecessors.setdefault(
            dep_edge.successor, []).append(dep_edge.predecessor)

    result = []
    violations = []

    for span, q_start, q_finish in normalized_spans:
        task_key_str = str(span.task_key)
        ready_us = ready_times.get(task_key_str, q_start)

        # Clamp start to ready time if necessary
        clamped_start = max(q_start, ready_us)
        if clamped_start > q_start:
            logger.debug(
                "Clamped start of %s: %d -> %d (ready at %d)",
                task_key_str, q_start, clamped_start, ready_us,
            )

        # Finish time is immutable
        clamped_finish = q_finish

        if clamped_start > clamped_finish:
            logger.error(
                "Excluding %s: clamping start to ready time (%d) would produce "
                "a negative-duration task (raw span %d..%d, ready %d) - a genuine "
                "ordering violation, not quantization noise. See violations list.",
                task_key_str, clamped_start, q_start, q_finish, ready_us,
            )
            violations.append({
                'type': 'clamp_negative_duration',
                'task_key': task_key_str,
                'ready_us': ready_us,
                'raw_start_us': q_start,
                'raw_finish_us': q_finish,
                'clamped_start_us': clamped_start,
                'clamped_finish_us': clamped_finish,
            })
            continue

        # Get build-gating dependencies for this task from the graph
        deps = []
        if span.task_key.task_kind == TaskKind.BUILD:
            own_fetch = fetch_task_by_element.get(span.task_key.element_uid)
            if own_fetch:
                deps.append(own_fetch)
        for predecessor in build_gating_predecessors.get(
                span.task_key.element_uid, ()):
            pred_key = build_task_by_element.get(predecessor)
            if pred_key:
                deps.append(pred_key)

        result.append(NormalizedTask(
            task_key=span.task_key,
            ready_us=ready_us,
            start_us=clamped_start,
            finish_us=clamped_finish,
            dependencies=deps,
            resources=span.resources,
            primary_resource=span.primary_resource,
            status=span.status,  # UX-62
        ))

    return result, violations


def normalize_trace(trace: Trace, graph: Graph, epsilon_us: int = 50000) -> Tuple[List[NormalizedTask], List[dict]]:
    """
    Full trace normalization pipeline (Part 3).
    
    Combines timestamp quantization, ready time computation,
    ordering validation, and start clamping.
    
    Args:
        trace: Input trace
        graph: Dependency graph
        epsilon_us: Quantization epsilon in microseconds
        
    Returns:
        Tuple of (normalized_tasks, violations)
    """
    # Step 1: Quantize timestamps
    normalized_spans = normalize_timestamps(trace.spans, epsilon_us)
    
    # Step 2: Compute ready times
    ready_times = compute_ready_times(normalized_spans, graph.dependencies)
    
    # Step 3: Validate ordering
    violations = validate_ordering(normalized_spans, graph.dependencies, ready_times)
    
    # Step 4: Clamp starts to ready times
    normalized_tasks, clamp_violations = clamp_task_starts(normalized_spans, ready_times, graph)
    violations = violations + clamp_violations

    logger.info(
        "Normalized %d tasks (%d ordering violations)",
        len(normalized_tasks), len(violations),
    )

    return normalized_tasks, violations
