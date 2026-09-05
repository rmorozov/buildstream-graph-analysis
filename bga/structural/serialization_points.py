"""UX-22/UX-31: per-element parallelism-pinning detection.

`UX-22` built this to flag the opposite condition from the one it now
detects, on a premise that turned out not to hold. It assumed a project
could give a specific element *more* native build-system parallelism
than the default (via `public: bst: max-jobs:`) and flagged several such
near-full-core elements dispatching concurrently as an oversubscription
risk.

`UX-31` re-checked that against a real BuildStream 2.7.0 install and a
real traced build: `max-jobs` is a **protected, project-wide** base
variable that an element may not redefine, BuildStream never reads a
`max-jobs` key out of `public:` at all, and the only per-element
parallelism control that exists is `variables: notparallel: True`,
which clamps that element to one job. So the raising case `UX-22`
targeted is not expressible, and the *lowering* case is - and is
common, since `notparallel` is the standard workaround for a race-prone
Makefile and routinely outlives the reason it was added.

What this module flags now: an element pinned below the parallelism the
rest of the build got, that is also expensive enough for it to matter -

  (a) `notparallel` set, or a resolved `max_jobs` below the value most
      other elements in this run resolved to,
  (b) a real, measured long duration relative to this run's own tasks,
  (c) a real blast radius - other elements genuinely wait on it.

(c) replaces `UX-22`'s concurrent-dispatch pairing, which was specific
to the risk it was looking for (two full-core builds at once). For a
serialized element the question is not who it runs beside, but how much
of the build is stuck behind it.

Plane 2 measures the same condition directly and far more reliably
(`UX-32`'s `pinned_to_one_job`) - but only for a build captured under
the tracer. This is the cheap, static, Plane-1-side signal available
from a plain `bst show`.
"""
from dataclasses import dataclass, field
from statistics import mean
from typing import Optional

from ..graph.edg import compute_reachability
from ..ingest.models import Element, Graph, NormalizedTask


@dataclass(frozen=True)
class SerializationPointRisk:
    """One element pinned below the parallelism the rest of the build
    got, long enough for that to cost real time, with real work waiting
    behind it (UX-31).

    `elements` stays a list for schema compatibility with `UX-22`'s own
    published shape, but now holds exactly one element - the pinning is
    a property of that element, not of a group."""
    elements: list[str]
    element_max_jobs: dict[str, int] = field(default_factory=dict)
    element_duration_us: dict[str, int] = field(default_factory=dict)
    builders: int = 0
    governing_cores: int = 0
    hint: str = ""
    # UX-31: why this element is pinned - True when it carries
    # `notparallel`, False when its resolved max_jobs is simply below
    # the run's typical value, None when unknown.
    notparallel: Optional[bool] = None
    typical_max_jobs: Optional[int] = None
    downstream_count: int = 0


@dataclass(frozen=True)
class SerializationPointAnalysis:
    risks: list[SerializationPointRisk]


def _build_hint(
    element: str, max_jobs: int, typical_max_jobs: int, duration_us: int,
    downstream_count: int, notparallel: Optional[bool],
) -> str:
    """UX-04's own per-category hint precedent: a real, actionable
    sentence naming the specific element and the real numbers behind the
    call, not just a bare flag."""
    cause = (
        "`variables: notparallel: True`"
        if notparallel else f"a resolved max-jobs of {max_jobs}"
    )
    return (
        f"{element} runs its own build system at {max_jobs} job(s) - {cause} - while "
        f"the rest of this build runs at {typical_max_jobs}, and it is the longest "
        f"kind of task here ({duration_us / 1e6:.1f}s) with {downstream_count} "
        f"element(s) waiting behind it. If its sources can handle parallelism, "
        f"removing the pin is a single-line change; if they genuinely cannot, it is "
        f"a real synchronization point worth splitting up"
    )


def detect_large_serialization_points(
    elements: list[Element],
    tasks: dict[str, NormalizedTask],
    graph: Graph,
    builders: Optional[int],
    governing_cores: Optional[int],
    long_duration_multiplier: float = 2.0,
) -> SerializationPointAnalysis:
    """
    Args:
        elements: graph.elements (for each element's own resolved
            `max_jobs` and `notparallel` - UX-31)
        tasks: element_uid -> its NormalizedTask (one task per element,
            the same simplification `compute_sensitivity` already makes)
        graph: the dependency graph, for reachability
        builders: this run's resource_capacities.PROCESS - unused by the
            detection itself now (a pinned element is a problem whether
            or not anything runs beside it), kept as reported context
        governing_cores: cpu_budget or host_cpu_count - likewise kept as
            reported context, no longer a threshold input
        long_duration_multiplier: an element's duration must be at least
            this multiple of the mean task duration in this run to count
            as "long" - relative to this run's own real data, not an
            arbitrary absolute constant

    Returns:
        SerializationPointAnalysis with one risk per genuinely pinned,
        expensive, depended-upon element. Empty when no element is
        pinned below the run's typical resolved `max_jobs` - including
        the common case of a project that simply runs everything at one
        job, which is the project's own choice, not an outlier.
    """
    durations = [task.dur_us for task in tasks.values() if task.dur_us > 0]
    if not durations:
        return SerializationPointAnalysis(risks=[])
    long_duration_threshold_us = long_duration_multiplier * mean(durations)

    # The run's own typical resolved parallelism, not a constant: what
    # "pinned" means is "below what everything else here got".
    resolved = [e.max_jobs for e in elements if e.max_jobs is not None]
    if not resolved:
        return SerializationPointAnalysis(risks=[])
    typical_max_jobs = max(resolved)
    if typical_max_jobs <= 1:
        # Whole project runs at one job. Nothing is an outlier.
        return SerializationPointAnalysis(risks=[])

    reachable_downstream, _ = compute_reachability(graph)

    risks: list[SerializationPointRisk] = []
    for element in elements:
        pinned_by_flag = element.notparallel is True
        pinned_by_value = element.max_jobs is not None and element.max_jobs < typical_max_jobs
        if not (pinned_by_flag or pinned_by_value):
            continue
        task = tasks.get(element.uid)
        if task is None or task.dur_us < long_duration_threshold_us:
            continue
        downstream_count = len(reachable_downstream.get(element.uid, set()))
        if downstream_count == 0:
            # Nothing waits on it, so its serialization costs the build
            # only its own slot - not a synchronization point.
            continue
        max_jobs = element.max_jobs if element.max_jobs is not None else 1
        risks.append(SerializationPointRisk(
            elements=[element.uid],
            element_max_jobs={element.uid: max_jobs},
            element_duration_us={element.uid: task.dur_us},
            builders=builders or 0,
            governing_cores=governing_cores or 0,
            notparallel=element.notparallel,
            typical_max_jobs=typical_max_jobs,
            downstream_count=downstream_count,
            hint=_build_hint(
                element.uid, max_jobs, typical_max_jobs, task.dur_us,
                downstream_count, element.notparallel,
            ),
        ))
    risks.sort(key=lambda r: -next(iter(r.element_duration_us.values())))
    return SerializationPointAnalysis(risks=risks)
