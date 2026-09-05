"""Stack-consolidation structural advisory (P4-15 Direction 1).

Not spec-mandated - bga's own added heuristic (see
docs/backlog/tasks/P4-15-stack-consolidation-heuristic.md). Purely structural
(graph topology + element_kind only, no timing data needed) - for a real,
measured comparison of a flagged candidate's actual checkout cost, see
the separate standalone tool tools/bst_checkout_cost.py.

Finds groups of 2+ elements that share the exact same set of immediate
consumers (every element that depends on any one of them depends on all
of them, and vice versa) - a well-defined, real "these are always
consumed together" signal - and flags groups with no existing `kind:
stack` element whose own dependencies exactly match the group, as
candidates worth considering for consolidation under one.
"""
from collections import defaultdict

from bga.graph.edg import build_element_graph
from bga.ingest.models import Graph


def find_consolidation_candidates(graph: Graph) -> list[dict]:
    """Real, deterministic structural candidates - never a timing
    estimate (see the module docstring). Each result:
    {"elements": [uid, ...], "shared_consumers": [uid, ...]}, sorted by
    group size (largest first) then by the group's own sorted element
    list (for deterministic output, Part 35/I11's same discipline).
    """
    if not graph.elements or not graph.dependencies:
        return []

    predecessors, successors = build_element_graph(graph)
    element_kind_by_uid = {e.uid: e.element_kind for e in graph.elements}

    # Group elements by their exact immediate-consumer set - elements
    # with no consumers at all (nothing currently depends on them) are
    # excluded: an empty set isn't a real shared relationship, grouping
    # every unconsumed leaf together on that basis would be a false
    # signal, not a genuine "always consumed together" one.
    groups: dict[frozenset[str], list[str]] = defaultdict(list)
    for uid in element_kind_by_uid:
        consumers = frozenset(successors.get(uid, []))
        if consumers:
            groups[consumers].append(uid)

    # Existing `stack` elements' own dependency sets - a group already
    # covered by one of these (exact match) needs no advisory.
    existing_stack_dep_sets = {
        frozenset(predecessors.get(uid, []))
        for uid, kind in element_kind_by_uid.items()
        if kind == "stack"
    }

    candidates = []
    for consumers, uids in groups.items():
        if len(uids) < 2:
            continue
        if frozenset(uids) in existing_stack_dep_sets:
            continue
        candidates.append({
            "elements": sorted(uids),
            "shared_consumers": sorted(consumers),
        })

    candidates.sort(key=lambda c: (-len(c["elements"]), c["elements"]))
    return candidates
