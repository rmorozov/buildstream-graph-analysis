"""UX-1357: what if this dependency edge were not there - `bga whatif --drop-edge PRED SUCC`.

Replays the run through `correlate.project_without_edges` with the edges
removed and every element only they pulled into the target's closure
pruned. BuildStream semantics: a build waits for its build deps and
their runtime-only closure; its own runtime-only deps do not gate it.
The answer is a priced question for the recipe author, never a removal
verdict - bga cannot know why an edge exists.
"""

import difflib
from dataclasses import replace
from typing import Optional

from . import shown as qty
from .ingest.models import TaskKind

CONVENTION = (
    "A replay over this run's measured durations and builders with the edge removed and every element "
    "only it pulled into the target's closure pruned. A priced question for the recipe author, not a "
    "removal verdict: bga cannot know why the edge exists."
)


def _known(graph) -> set[str]:
    return {element.uid for element in getattr(graph, "elements", None) or []}


def _edge_set(graph) -> set[tuple[str, str]]:
    return {(d.predecessor, d.successor) for d in getattr(graph, "dependencies", None) or []}


def _nearest(name: str, pool) -> list[str]:
    return difflib.get_close_matches(name, sorted(pool), n=3, cutoff=0.4)


def refusals(graph, edges) -> list[dict]:
    """An edge the graph does not hold is refused with the nearest names it does."""
    known, present, out = _known(graph), _edge_set(graph), []
    for predecessor, successor in edges:
        if (predecessor, successor) in present:
            continue
        if predecessor in known and successor in known:
            near = [p for p, s in present if s == successor]
            hint = f" {successor} depends on: {', '.join(_nearest(predecessor, near) or sorted(near)[:3])}."
        else:
            hint = "".join(
                f" Nearest to {name}: {', '.join(_nearest(name, known)) or 'none'}."
                for name in (predecessor, successor)
                if name not in known
            )
        out.append(
            {
                "check": "unknown_edge",
                "elements": [predecessor, successor],
                "sentence": f"No edge {predecessor} -> {successor} in this run's graph.{hint}",
            }
        )
    return out


def targets(graph) -> set[str]:
    """The requested targets, or every element nothing depends on."""
    elements = getattr(graph, "elements", None) or []
    marked = {e.uid for e in elements if e.requested_target}
    consumed = {d.predecessor for d in graph.dependencies}
    return marked or {e.uid for e in elements if e.uid not in consumed}


def closure(dependencies, roots) -> set[str]:
    """Everything `roots` need built, over build and runtime edges alike."""
    preds: dict[str, list[str]] = {}
    for d in dependencies:
        preds.setdefault(d.successor, []).append(d.predecessor)
    seen, stack = set(roots), list(roots)
    while stack:
        for p in preds.get(stack.pop(), ()):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return seen


def gating_pairs(dependencies) -> set[tuple[str, str]]:
    """`(P, S)`: P's artifact must exist before S builds - S's build deps plus their runtime-only closure."""
    runtime: dict[str, set[str]] = {}
    build: dict[str, set[str]] = {}
    for d in dependencies:
        (runtime if d.dependency_type == "runtime" else build).setdefault(d.successor, set()).add(d.predecessor)
    pairs = set()
    for successor, deps in build.items():
        stack = list(deps)
        while stack:
            p = stack.pop()
            if (p, successor) not in pairs:
                pairs.add((p, successor))
                stack.extend(runtime.get(p, ()))
    return pairs


def _gated(tasks, pairs, fixed):
    """The run's tasks with every gating pair a dependency, and `fixed` elements' builds instant."""
    artifact = {}
    for t in tasks:
        if t.task_key.task_kind in (TaskKind.BUILD, TaskKind.PULL):
            artifact.setdefault(t.task_key.element_uid, str(t.task_key))
    by_successor: dict[str, list[str]] = {}
    for p, s in pairs:
        if p in artifact:
            by_successor.setdefault(s, []).append(artifact[p])
    out = []
    for t in tasks:
        changes = {}
        if t.task_key.task_kind == TaskKind.BUILD:
            extra = sorted(set(by_successor.get(t.task_key.element_uid, ())) - set(t.dependencies))
            changes["dependencies"] = [*t.dependencies, *extra]
            if t.task_key.element_uid in fixed:
                changes["finish_us"] = t.start_us
        out.append(replace(t, **changes) if changes else t)
    return out


def project(graph, tasks, run_context, edges, fixed=()) -> Optional[dict]:
    """The replay before and after, the closure's size before and after, and the pruned set."""
    from .correlate import project_without_edges

    removed = set(edges)
    after_deps = [d for d in graph.dependencies if (d.predecessor, d.successor) not in removed]
    roots = targets(graph)
    before_set, after_set = closure(graph.dependencies, roots), closure(after_deps, roots)
    pruned = frozenset(before_set - after_set)
    before_pairs = gating_pairs(graph.dependencies)
    lost = (before_pairs - gating_pairs(after_deps)) | removed
    replayed = project_without_edges(_gated(tasks, before_pairs, set(fixed)), run_context, sorted(lost), pruned=pruned)
    if replayed is None:
        return None
    return {
        "baseline_makespan_us": int(replayed["replayed_baseline_us"]),
        "makespan_after_us": int(replayed["projected_us"]),
        "saving_us": int(replayed["saving_us"]),
        "elements_before": len(before_set),
        "elements_after": len(after_set),
        "pruned": sorted(pruned),
        "capacities": replayed["capacities"],
    }


def answer(analyzer, result, elements, raw_edges) -> dict:
    """A `whatif/v1` for `elements`, with its `edges` answer when edges are asked; edges alone are a question."""
    from .whatif import project as project_elements

    graph = analyzer.graph
    document = project_elements(result, graph, list(elements))
    if not raw_edges:
        return document
    edges = [tuple(edge) for edge in raw_edges]
    document["refusals"] = [r for r in document["refusals"] if r["check"] != "empty_selection"]
    edge_refusals = refusals(graph, edges)
    scheduler = getattr(analyzer, "replay_scheduler", None)
    projected = None
    if not edge_refusals and not document["refusals"] and scheduler is not None:
        projected = project(graph, scheduler.tasks, scheduler.run_context, edges, fixed=document["selected"])
    document["edges"] = {
        "dropped": [list(edge) for edge in edges],
        "convention": CONVENTION,
        "refusals": edge_refusals,
        "projected": projected,
    }
    return document


def _hours(us: int) -> str:
    return f"{us / 3.6e9:.2f} h" if us >= 3.6e9 else qty.duration(us)


def render(document: dict) -> list[str]:
    """The edge answer as text, after the element answer when one was asked."""
    from .whatif import render as render_elements

    edges = document.get("edges")
    if edges is None:
        return render_elements(document)
    lines = render_elements(document) if document["selected"] else []
    named = ", ".join(f"{p} -> {s}" for p, s in edges["dropped"])
    lines.append(f"What if these edges were dropped: {named}")
    refused = edges["refusals"] + ([] if document["selected"] else document["refusals"])
    lines.extend(f"  Refused: {r['sentence']}" for r in refused)
    projected = edges["projected"]
    if projected:
        before, after = projected["baseline_makespan_us"], projected["makespan_after_us"]
        share = f" ({-projected['saving_us'] / before:.1%})" if before else ""
        wall = document.get("total_duration_us")
        lines.append(
            f"  Replayed makespan{' with the fixes above' if document['selected'] else ''}: "
            f"{_hours(before)} -> {_hours(after)}{share}" + (f"; observed wall {_hours(wall)}" if wall else "")
        )
        pruned = projected["pruned"]
        lines.append(
            f"  Elements in the target's closure: {projected['elements_before']} -> {projected['elements_after']}"
            + (f"; pruned {len(pruned)}: {', '.join(pruned)}" if pruned else "")
        )
        lines.append(f"  {edges['convention']}")
    return lines
