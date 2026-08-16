"""UX-22: "large serialization point" detection.

A real BuildStream project can give a specific element more native
build-system parallelism (`--max-jobs`-equivalent) than the project
default via a per-element `public: bst: max-jobs:` override (captured
by `tools/bst_show_to_graph.py` as `Element.max_jobs` - see that
module's `_parse_max_jobs` for the real mechanism, confirmed
empirically). This is often *correct*: a large, monolithic element
(e.g. an LLVM build) can be a genuine single point of synchronization
in the whole build graph - it doesn't meaningfully parallelize with
anything else while it runs, so giving it the full host core count can
cut real wall-clock time dramatically.

But the same reasoning becomes actively harmful once BuildStream's own
`--builders` setting lets *multiple* such large, near-full-core-count
elements build concurrently - N simultaneous full-core-count builds is
a severe, real oversubscription risk `bga/analyzer.py`'s
`_check_process_oversubscription` (UX-12/UX-16) has no way to see at
all, since it only ever reasons about one aggregate, global
`native_max_jobs` value - it can't see *which* specific elements are
driving demand, or whether they're the kind of large, near-full-core
elements this scenario is about.

This module flags that specific, concrete risk: elements that combine
(a) a real, measured long duration, (b) a configured `max_jobs` close
to the full governing core count, and (c) genuine potential for
concurrent dispatch with a sibling candidate under the real `builders`
value (i.e. the graph shape actually allows more than one to be
dispatched at once, and `builders` is large enough to let it happen -
not just that more than one such element exists somewhere in the
graph).
"""
from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List, Optional

from ..graph.edg import compute_reachability
from ..ingest.models import Element, Graph, NormalizedTask


@dataclass(frozen=True)
class SerializationPointRisk:
    """A group of mutually-independent elements (no ancestor/descendant
    relationship) that could genuinely dispatch concurrently under the
    real `builders` value, each individually a real synchronization-risk
    candidate (long duration + near-full-core `max_jobs`)."""
    elements: List[str]
    element_max_jobs: Dict[str, int] = field(default_factory=dict)
    element_duration_us: Dict[str, int] = field(default_factory=dict)
    builders: int = 0
    governing_cores: int = 0
    hint: str = ""


@dataclass(frozen=True)
class SerializationPointAnalysis:
    risks: List[SerializationPointRisk]


def _build_hint(elements: List[str], builders: int) -> str:
    """UX-04's own per-category hint precedent: a real, actionable
    sentence naming the specific elements, not just a bare flag."""
    names = " and ".join(elements) if len(elements) <= 2 else ", ".join(elements[:-1]) + f", and {elements[-1]}"
    return (
        f"elements {names} are both configured near full core parallelism and "
        f"can dispatch concurrently under builders={builders} - consider a lower "
        f"per-element max-jobs for one, or reducing builders for this graph shape"
    )


def detect_large_serialization_points(
    elements: List[Element],
    tasks: Dict[str, NormalizedTask],
    graph: Graph,
    builders: Optional[int],
    governing_cores: Optional[int],
    near_full_ratio: float = 0.75,
    long_duration_multiplier: float = 2.0,
) -> SerializationPointAnalysis:
    """
    Args:
        elements: graph.elements (for each element's own `max_jobs`)
        tasks: element_uid -> its NormalizedTask (one task per element,
            the same simplification `compute_sensitivity` already makes)
        graph: the dependency graph, for reachability
        builders: this run's resource_capacities.PROCESS - concurrent
            dispatch of two elements is only physically possible when
            builders >= 2, regardless of anything else
        governing_cores: cpu_budget or host_cpu_count (UX-12/UX-15's own
            governing-ceiling precedent) - the ceiling `max_jobs` is
            compared against to decide "near full core"
        near_full_ratio: an element's max_jobs must be at least this
            fraction of governing_cores to count as "near full core"
        long_duration_multiplier: an element's duration must be at least
            this multiple of the mean task duration in this run to
            count as "long" - relative to this run's own real data, not
            an arbitrary absolute constant

    Returns:
        SerializationPointAnalysis with zero or more real risk groups -
        empty whenever builders < 2 (concurrent dispatch of two elements
        is impossible regardless of configuration - Acceptance Test #2's
        own explicit case) or governing_cores is unknown (nothing to
        compare max_jobs against) or fewer than two real candidates
        exist.
    """
    if builders is None or builders < 2 or governing_cores is None or governing_cores <= 0:
        return SerializationPointAnalysis(risks=[])

    durations = [task.dur_us for task in tasks.values() if task.dur_us > 0]
    if not durations:
        return SerializationPointAnalysis(risks=[])
    mean_duration_us = mean(durations)
    long_duration_threshold_us = long_duration_multiplier * mean_duration_us
    near_full_threshold = near_full_ratio * governing_cores

    candidates: List[str] = []
    element_max_jobs: Dict[str, int] = {}
    element_duration_us: Dict[str, int] = {}
    for element in elements:
        if element.max_jobs is None or element.max_jobs < near_full_threshold:
            continue
        task = tasks.get(element.uid)
        if task is None or task.dur_us < long_duration_threshold_us:
            continue
        candidates.append(element.uid)
        element_max_jobs[element.uid] = element.max_jobs
        element_duration_us[element.uid] = task.dur_us

    if len(candidates) < 2:
        return SerializationPointAnalysis(risks=[])

    reachable_downstream, _ = compute_reachability(graph)

    def _independent(a: str, b: str) -> bool:
        return b not in reachable_downstream.get(a, set()) and a not in reachable_downstream.get(b, set())

    # Greedy antichain partition (same shape as
    # bga/structural/batching.py's own - not cross-imported, since the
    # two features are independent and this is a handful of lines, not
    # worth coupling two modules over).
    groups: List[List[str]] = []
    for candidate in sorted(candidates, key=lambda uid: -element_duration_us[uid]):
        placed = False
        for group in groups:
            if all(_independent(candidate, member) for member in group):
                group.append(candidate)
                placed = True
                break
        if not placed:
            groups.append([candidate])

    risks = [
        SerializationPointRisk(
            elements=group,
            element_max_jobs={uid: element_max_jobs[uid] for uid in group},
            element_duration_us={uid: element_duration_us[uid] for uid in group},
            builders=builders,
            governing_cores=governing_cores,
            hint=_build_hint(group, builders),
        )
        for group in groups
        if len(group) >= 2
    ]
    return SerializationPointAnalysis(risks=risks)
