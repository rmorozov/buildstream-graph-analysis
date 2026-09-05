"""UX-681: fan-in — what an element depends on, ranked.

`blast_radius` answers "what does changing this rebuild"; this answers
its mirror, "what does this pull in", which the element owner asks
first and the graph owner asks as "which fan-in is suspicious".

Nothing here is a new traversal. `compute_reachability` has returned
`reachable_upstream` in the same pass as the downstream set since
`UX-33`, and `compute_dominators` has run on every analysis since; both
reached `graph_analysis` and neither reached a reader. This is the
join that publishes them.

Plane 1 only. `UX-407`'s never-read edges are the column that turns
these counts into a question, and they are not here: they need Plane 2
to exist, so `ELEMENT_PLACEMENT_RULE` puts them on an `element_join`
row (`dependency_read_share`) rather than in a map every capture
carries and most captures could only fill with nulls.
"""
from typing import Optional

from .edg import compute_dominators, compute_reachability

#: `UX-681`: how many rows the ranking names, the same five
#: `top_blast_radius` names (`bga/analyzer.py`). Its mirror should be
#: the same length or a reader comparing the two is comparing lists of
#: different sizes.
TOP_FAN_IN = 5


def immediate_dominator(dominators: dict, uid: str) -> Optional[str]:
    """The nearest element every path from a root passes through.

    The dominator *set* is what `compute_dominators` returns; the one a
    developer waits on is the closest of them, which is the member whose
    own dominator set is largest - it is dominated by all the others.

    `None` for a root, which dominates only itself.
    """
    others = (dominators.get(uid) or set()) - {uid}
    if not others:
        return None
    return max(sorted(others), key=lambda name: len(dominators.get(name) or ()))


def compute_fan_in(graph, kinds: dict, structural_kinds) -> dict:
    """Per element: what it names, what that pulls in, and its gate."""
    _downstream, upstream = compute_reachability(graph)
    dominators = compute_dominators(graph)
    direct: dict = {element.uid: set() for element in graph.elements}
    for edge in graph.dependencies:
        if edge.successor in direct:
            direct[edge.successor].add(edge.predecessor)
    rows = {}
    for uid in sorted(direct):
        rows[uid] = {
            "direct_count": len(direct[uid]),
            # `compute_reachability` excludes the element itself, so
            # this is the closure and not the closure plus one - held
            # by a clause on that helper rather than by a subtraction
            # here, which would be a second rule that could not be wrong.
            "transitive_count": len(upstream.get(uid) or ()),
            "immediate_dominator": immediate_dominator(dominators, uid),
            "element_kind": kinds.get(uid, "unknown"),
            "is_structural_kind": kinds.get(uid) in structural_kinds,
        }
    return rows


def top_fan_in(rows: dict, limit: int = TOP_FAN_IN) -> list:
    """The ranking, by transitive count, structural elements excluded.

    `UX-76`'s rule, which the blast ranking applies and this mirrors: a
    toolchain has a large fan-in *on purpose*. Excluded from the
    ranking, never from `rows` - `UX-203` was filed because views were
    unreachable and answering this by hiding them would trade one
    defect for an older one.

    `UX-474`: and only elements that pull in something. An ordering over
    a constant is not a ranking, and a graph of leaves is all zeroes.
    """
    reaching = [uid for uid, row in rows.items()
                if not row["is_structural_kind"] and row["transitive_count"]]
    reaching.sort(key=lambda uid: (-rows[uid]["transitive_count"], uid))
    return reaching[:limit]
