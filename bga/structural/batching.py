"""UX-20: map-reduce batch-opportunity analysis.

`compute_sensitivity`'s own `top_opportunities` (`bga/structural/analyzer.py`)
scores each element independently - a per-element proxy, not a
simulation of what fixing *several* elements *together* would actually
do to the real makespan. On a large graph, fixing the single reported
bottleneck, re-running `bga analyze`, discovering the next one, and
repeating serially can mean many slow iterations, when several
independent bottlenecks could often be identified and fixed together
in one batch instead.

This module provides the "map" (partition high-sensitivity elements
into groups with no pairwise ancestor/descendant relationship - fixing
them doesn't require sequencing the work) and the "reduce" (simulate
the *combined* effect of fixing every element in a group at once, via
`ReplayScheduler`'s `duration_overrides` param) halves of that
framing. Elements that ARE on the same dependency chain are reported as
`serialized_pairs` instead - fixing one doesn't help until the other is
also fixed, so they were deliberately not grouped together.

"Fixing" an element here means eliminating its duration entirely
(`duration_us = 0`) - the same "if all slack/improvable time were
eliminated" framing `compute_sensitivity`'s own `best_case_speedup`
already uses elsewhere in this codebase. A structural best-case
estimate, not a claim about what any real optimization would actually
achieve.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from ..graph.edg import compute_reachability
from ..ingest.models import Graph
from ..replay.scheduler import ReplayScheduler


@dataclass(frozen=True)
class BatchGroup:
    """A set of mutually-independent high-sensitivity elements (no
    pairwise ancestor/descendant relationship in the dependency graph)
    - the real "map" grouping this module produces."""
    elements: List[str]
    baseline_makespan_us: int
    combined_makespan_us: int
    combined_savings_us: int
    # Per-element makespan improvement if that element alone (not the
    # whole group) were fixed - lets a reader see the "combined" effect
    # is not simply the sum of the individual ones (real DAG scheduling
    # effects: shared critical-path membership, resource contention).
    individual_savings_us: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchOpportunities:
    """UX-20's own map-reduce result over a candidate set of high-
    sensitivity elements (typically `compute_sensitivity`'s own
    `top_opportunities`)."""
    groups: List[BatchGroup]
    serialized_pairs: List[Tuple[str, str]]


def _are_independent(a: str, b: str, reachable_downstream: Dict[str, Set[str]]) -> bool:
    """True iff neither element can reach the other - no ancestor/
    descendant relationship, i.e. fixing one is not blocked on fixing
    the other first."""
    return b not in reachable_downstream.get(a, set()) and a not in reachable_downstream.get(b, set())


def _partition_into_independent_groups(
    candidates: List[str], reachable_downstream: Dict[str, Set[str]],
) -> Tuple[List[List[str]], List[Tuple[str, str]]]:
    """Greedy antichain partition over `candidates` (caller supplies
    them in most-impactful-first order): each candidate joins the first
    existing group it's independent of every current member of, else
    starts a new group. Not necessarily the minimum possible number of
    groups (a harder optimization this task's own doc doesn't ask for -
    "report the independent-group structure and let the user choose",
    not optimize group count) - every group being a real antichain
    (no two members share an ancestor/descendant relationship) is what
    matters, not group-count optimality.
    """
    groups: List[List[str]] = []
    for candidate in candidates:
        placed = False
        for group in groups:
            if all(_are_independent(candidate, member, reachable_downstream) for member in group):
                group.append(candidate)
                placed = True
                break
        if not placed:
            groups.append([candidate])

    # Every genuinely serialized pair among the candidate set -
    # informational (not used to decide grouping above, which is
    # already settled), so a reader can see *why* two elements weren't
    # grouped together, not just that they weren't.
    serialized_pairs: List[Tuple[str, str]] = [
        (a, b)
        for i, a in enumerate(candidates)
        for b in candidates[i + 1:]
        if not _are_independent(a, b, reachable_downstream)
    ]
    return groups, serialized_pairs


def compute_batch_opportunities(
    candidates: List[str],
    graph: Graph,
    replay_scheduler: ReplayScheduler,
    element_to_task_key: Dict[str, str],
    priority_rule: str = 'lpt',
) -> BatchOpportunities:
    """Partitions `candidates` (element UIDs, most-impactful-first - the
    caller passes `compute_sensitivity`'s own `top_opportunities` order)
    into independent groups and simulates each group's combined effect
    of eliminating every member's duration at once.

    `element_to_task_key` maps each candidate element UID to the real
    task_key string `ReplayScheduler`'s own `duration_overrides` expects
    - structural analysis operates on one task per element, the same
    simplification `compute_sensitivity` itself already makes.
    """
    reachable_downstream, _ = compute_reachability(graph)
    raw_groups, serialized_pairs = _partition_into_independent_groups(candidates, reachable_downstream)

    baseline_makespan_us = replay_scheduler.replay(priority_rule=priority_rule).makespan_us

    groups: List[BatchGroup] = []
    for raw_group in raw_groups:
        task_keys = [
            (element, element_to_task_key[element])
            for element in raw_group if element in element_to_task_key
        ]
        if len(task_keys) < 2:
            # A "batch" of fewer than 2 real, resolvable tasks isn't a
            # map-reduce grouping opportunity - nothing to combine.
            continue

        combined_overrides = {task_key: 0 for _, task_key in task_keys}
        combined_makespan_us = replay_scheduler.replay(
            priority_rule=priority_rule, duration_overrides=combined_overrides,
        ).makespan_us

        individual_savings_us: Dict[str, int] = {}
        for element, task_key in task_keys:
            solo_makespan_us = replay_scheduler.replay(
                priority_rule=priority_rule, duration_overrides={task_key: 0},
            ).makespan_us
            individual_savings_us[element] = max(0, baseline_makespan_us - solo_makespan_us)

        groups.append(BatchGroup(
            elements=[element for element, _ in task_keys],
            baseline_makespan_us=baseline_makespan_us,
            combined_makespan_us=combined_makespan_us,
            combined_savings_us=max(0, baseline_makespan_us - combined_makespan_us),
            individual_savings_us=individual_savings_us,
        ))

    return BatchOpportunities(groups=groups, serialized_pairs=serialized_pairs)


def serialize_batch_opportunities(batch_result: BatchOpportunities) -> Dict[str, Any]:
    """Report-shape serialization of `compute_batch_opportunities`'s
    result (UX-20). A group with zero real `combined_savings_us` -
    fixing all its members together doesn't move the makespan at all -
    is a real, simulated fact, not a genuine opportunity worth mixing
    into `groups`; it's moved to `omitted_zero_savings_groups` instead
    (UX-26) so it stays visible (this codebase's "no silent gaps"
    discipline - see `docs/scenarios/UX-26-...md`) without cluttering
    the list a user actually wants to read.
    """
    all_groups = [
        {
            'elements': group.elements,
            'baseline_makespan_us': group.baseline_makespan_us,
            'combined_makespan_us': group.combined_makespan_us,
            'combined_savings_us': group.combined_savings_us,
            'individual_savings_us': group.individual_savings_us,
        }
        for group in batch_result.groups
    ]
    return {
        'groups': [g for g in all_groups if g['combined_savings_us'] > 0],
        'omitted_zero_savings_groups': [
            {'elements': g['elements']} for g in all_groups if g['combined_savings_us'] == 0
        ],
        'serialized_pairs': batch_result.serialized_pairs,
    }
