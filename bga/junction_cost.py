"""UX-904: N separate variant builds priced against one junctioned invocation.

A projection over N captures of one build type under different variants,
shaped like `bga whatif`: refusals are answers, and every figure carries
the assumption its arithmetic used. A re-capture is the ground truth.

Identity is the cache key (`graph/v9`, `Element.cache_key`): in one
junctioned invocation element names carry a junction prefix, and an asan
and a release compile of one source share a name and not a key.
"""

from collections.abc import Sequence
from typing import Optional

from . import buildclass, schemas
from .plural import plural

ASSUMPTIONS = {
    "pipeline_once": "One invocation pays each pipeline phase once, at the largest of the N "
    "measured costs; a union graph that loads or resolves slower than its largest part is not "
    "modelled, so the pipeline saving is an upper bound.",
    "shared_by_key": "Two elements are one element only when their cache keys are identical; "
    "a shared element is built once, at the longest of its measured durations.",
    "unlimited_capacity": "The floors are T-infinity: longest build-edge paths under unlimited "
    "builders, a lower bound on any schedule, not a forecast.",
    "junction_staging": "Staging the junctioned subprojects is not measured here (no bst on the "
    "capturing host), so the one-invocation bound excludes it.",
}

CONVENTION = (
    "A structural projection over N measured runs, not a simulation: a re-capture of the "
    "junctioned invocation is still the ground truth."
)


def run_view(result, graph) -> dict:
    """The parts of one analysed run this projection reads."""
    instance = getattr(result, 'run_instance', None) or {}
    overhead = getattr(result, 'pipeline_overhead', None) or {}
    durations = (getattr(result, 'signals', None) or {}).get('element_durations') or {}
    elements = getattr(graph, 'elements', None) or []
    edges = [
        (edge.predecessor, edge.successor)
        for edge in (getattr(graph, 'dependencies', None) or [])
        if getattr(edge, 'dependency_type', 'build') != 'runtime'
    ]
    return {
        "run_id": getattr(result, 'run_id', None),
        "build_class": instance.get('build_class'),
        "phases": [dict(phase) for phase in overhead.get('phases') or []],
        "keys": {element.uid: element.cache_key for element in elements},
        "edges": edges,
        "durations": {str(uid): int(value or 0) for uid, value in durations.items()},
    }


def project(runs: Sequence[dict]) -> dict:
    """`junction-cost/v1` over `run_view`s: refused, or projected."""
    runs = list(runs)
    document = {
        "runs": [_run_summary(run) for run in runs],
        "convention": CONVENTION,
        "assumptions": [{"id": key, "text": text} for key, text in ASSUMPTIONS.items()],
        "refusals": _refusals(runs),
        "projected": None,
    }
    if document["refusals"]:
        return schemas.stamp(document, schemas.JUNCTION_COST)
    document["projected"] = _projected(runs)
    return schemas.stamp(document, schemas.JUNCTION_COST)


def _run_summary(run: dict) -> dict:
    return {
        "run_id": run.get("run_id"),
        "build_class": buildclass.label(run.get("build_class")),
        "elements": len(run.get("keys") or {}),
        "keyed_elements": sum(1 for key in (run.get("keys") or {}).values() if key),
        "pipeline_overhead_us": sum(int(phase.get("elapsed_us") or 0) for phase in run.get("phases") or []),
    }


def _type_only(block: Optional[dict]) -> Optional[dict]:
    # The variant is what differs by construction; the type is what must not.
    return {"type": block.get("type"), "variant": {}} if block else None


def _refusals(runs: list[dict]) -> list[dict]:
    if len(runs) < 2:
        return [
            {
                "check": "single_run",
                "runs": [run.get("run_id") for run in runs],
                "sentence": "One run is nothing to join: the question is N separate invocations "
                "against one, and it needs at least two.",
            }
        ]
    blocks = [run.get("build_class") for run in runs]
    if not buildclass.homogeneous([_type_only(block) for block in blocks]):
        seen = sorted({(block or {}).get("type") or buildclass.NOT_DECLARED for block in blocks})
        return [
            {
                "check": "different_types",
                "runs": [run.get("run_id") for run in runs],
                "sentence": f"These runs declare different build types ({', '.join(seen)}): "
                f"variants of one build join, a nightly and a review build do not.",
            }
        ]
    unkeyed = [run.get("run_id") for run in runs if not any((run.get("keys") or {}).values())]
    if unkeyed:
        return [
            {
                "check": "no_cache_keys",
                "runs": unkeyed,
                "sentence": f"No cache keys in {', '.join(str(r) for r in unkeyed)}: the key is "
                f"the only identity two variants share, so nothing can be joined.",
            }
        ]
    return []


def _node(run_index: int, uid: str, key: Optional[str]) -> str:
    return key if key else f"{run_index}:{uid}"


def _floor(nodes: dict[str, int], edges: set[tuple[str, str]]) -> int:
    from .graph.edg import compute_critical_path
    from .ingest.models import DependencyEdge, Element, Graph

    graph = Graph(
        elements=[Element(uid=node) for node in sorted(nodes)],
        dependencies=[DependencyEdge(predecessor=a, successor=b) for a, b in sorted(edges)],
    )
    length, _path = compute_critical_path(graph, nodes)
    return int(length)


def _projected(runs: list[dict]) -> dict:
    per_run_nodes, per_run_edges = [], []
    seen_by: dict[str, list[int]] = {}
    for index, run in enumerate(runs):
        keys, durations = run.get("keys") or {}, run.get("durations") or {}
        nodes = {_node(index, uid, key): durations.get(uid, 0) for uid, key in keys.items()}
        edges = {
            (_node(index, a, keys.get(a)), _node(index, b, keys.get(b)))
            for a, b in run.get("edges") or []
            if a in keys and b in keys
        }
        per_run_nodes.append(nodes)
        per_run_edges.append(edges)
        for key in keys.values():
            if key:
                seen_by.setdefault(key, []).append(index)
    shared = sorted(key for key, indices in seen_by.items() if len(set(indices)) > 1)
    shared_set = set(shared)

    union_nodes: dict[str, int] = {}
    for nodes in per_run_nodes:
        for node, duration in nodes.items():
            union_nodes[node] = max(union_nodes.get(node, 0), duration)
    union_edges = set().union(*per_run_edges)
    closed = all(a in shared_set for a, b in union_edges if b in shared_set)

    shared_rows = []
    work_saving = 0
    for key in shared:
        measured = [nodes[key] for nodes in per_run_nodes if key in nodes]
        work_saving += sum(measured) - max(measured)
        uids = sorted({uid for run in runs for uid, k in (run.get("keys") or {}).items() if k == key})
        shared_rows.append({"cache_key": key, "elements": uids, "duration_us": max(measured)})

    phases = _phase_rows(runs)
    pipeline_saving = sum(row["saving_us"] for row in phases)
    pipeline_once = sum(row["max_us"] for row in phases)
    union_floor = _floor(union_nodes, union_edges)
    return {
        "shared": shared_rows,
        "shared_closed_downward": closed,
        "shared_work_saving_us": work_saving,
        "pipeline": phases,
        "pipeline_saving_us": pipeline_saving,
        "saving_us": pipeline_saving + work_saving,
        "separate_floors_us": [_floor(nodes, edges) for nodes, edges in zip(per_run_nodes, per_run_edges)],
        "union_floor_us": union_floor,
        "one_invocation_lower_bound_us": pipeline_once + union_floor,
        "junction_staging_us": None,
        "overlap": _overlap_sentence(shared, work_saving),
    }


def _phase_rows(runs: list[dict]) -> list[dict]:
    by_phase: dict[str, list[int]] = {}
    for run in runs:
        for phase in run.get("phases") or []:
            by_phase.setdefault(str(phase.get("phase") or ""), []).append(int(phase.get("elapsed_us") or 0))
    return [
        {"phase": name, "sum_us": sum(values), "max_us": max(values), "saving_us": sum(values) - max(values)}
        for name, values in by_phase.items()
    ]


def _overlap_sentence(shared: list[str], work_saving: int) -> str:
    if not shared:
        return (
            "No element is shared: one invocation builds everything the N builds did, so it saves "
            "no build work - what remains is the pipeline term, an assumption and not a measurement."
        )
    return f"{plural(len(shared), 'element')} shared by cache key; building each once saves {work_saving / 1e6:.3f}s of work."


def render(document: dict) -> list[str]:
    """The answer as text, from the document alone."""
    runs = document.get("runs") or []
    lines = [f"N separate invocations against one junctioned build: {plural(len(runs), 'run')}"]
    for run in runs:
        lines.append(
            f"  {run['run_id']}: {run['build_class'] or buildclass.NOT_DECLARED}, {run['keyed_elements']}/{run['elements']} keyed"
        )
    for refusal in document.get("refusals") or []:
        lines.append(f"  Refused: {refusal['sentence']}")
    projected = document.get("projected")
    if projected:
        lines.append(f"  Shared: {projected['overlap']}")
        lines.append(
            f"  Pipeline paid once instead of N times saves {projected['pipeline_saving_us'] / 1e6:.3f}s [pipeline_once]"
        )
        lines.append(f"  Total saving {projected['saving_us'] / 1e6:.3f}s (upper bound)")
        floors = ", ".join(f"{value / 1e6:.3f}s" for value in projected["separate_floors_us"])
        lines.append(
            f"  Floors: separate {floors}; union {projected['union_floor_us'] / 1e6:.3f}s [unlimited_capacity]"
        )
        lines.append(
            f"  One invocation costs at least {projected['one_invocation_lower_bound_us'] / 1e6:.3f}s, "
            f"plus junction staging (not measured) [junction_staging]"
        )
        if not projected["shared_closed_downward"]:
            lines.append(
                "  Caveat: a shared key depends on an unshared one - the keys do not cover their dependencies."
            )
    for assumption in document.get("assumptions") or []:
        lines.append(f"  [{assumption['id']}] {assumption['text']}")
    lines.append(f"  {document['convention']}")
    return lines
