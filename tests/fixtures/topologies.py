"""
Shared synthetic graph topology fixture library (P3-01, spec Part 36.1).

Each factory below builds one of the topologies Part 36.1 requires
tests to cover (linear chain, diamond, fan-in, fan-out, multiple equal
predecessors, deep unequal predecessors, independent branches, terminal
tasks, requested/non-requested targets) and returns a
`(run_context, graph, trace)` tuple of plain JSON-serializable dicts in
the canonical graph/v9 + trace/v9 shape (Part 32.2/32.3) - the same
shape already used across the P1/P2 regression tests (e.g.
`tests/unit/test_cold_floor.py`), so any test that already knows how to
write a run dir from that shape can consume these directly.

`write_run_dir` does that writing; `build_analyzer` is a convenience
that writes + constructs a loaded `BuildEfficiencyAnalyzer` in one call.
No test *assertions* live here - only fixture construction (Part 36.1's
assertions are the consuming tasks' job: P3-03 through P3-09 and various
P1-*/P2-* acceptance tests).
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bga import BuildEfficiencyAnalyzer

RunContext = dict
Graph = dict
Trace = dict
Topology = Tuple[RunContext, Graph, Trace]


def _element(uid: str, cache_key: Optional[str] = None, requested_target: bool = False) -> dict:
    return {"uid": uid, "cache_key": cache_key, "requested_target": requested_target}


def _dependency(predecessor: str, successor: str, dependency_type: str = "build") -> dict:
    return {"predecessor": predecessor, "successor": successor, "dependency_type": dependency_type}


def _span(
    uid: str, start_us: int, dur_us: int,
    kind: str = "BUILD", phase: str = "BUILD", attempt: int = 0,
    resources: Tuple[str, ...] = ("PROCESS",),
) -> dict:
    return {
        "task_key": f"{uid}|{kind}|{phase}|{attempt}",
        "ts_us": start_us,
        "dur_us": dur_us,
        "resources": list(resources),
        "primary_resource": resources[0] if resources else None,
    }


def _run_context(
    wall_end_us: int, max_jobs: int = 8,
    resource_capacities: Optional[Dict[str, int]] = None,
    trace_epsilon_us: int = 1000,
) -> RunContext:
    return {
        "trace_epsilon_us": trace_epsilon_us,
        "wall_clock": {"start_us": 0, "end_us": wall_end_us},
        "max_jobs": max_jobs,
        "resource_capacities": resource_capacities or {"PROCESS": max_jobs},
        # Declares as many effective CPUs as max_jobs, matching each
        # topology's own concurrency - avoids a spurious CPU
        # reconciliation warning (Part 33.3) from the default
        # effective_cpus=1.0 fallback whenever a fixture runs >1 task
        # concurrently, which every topology but linear_chain does.
        "cpu_accounting": {"effective_cpus": max_jobs},
    }


def _build(
    elements: List[dict], dependencies: List[dict], spans: List[dict],
    wall_end_us: int, max_jobs: int = 8,
    resource_capacities: Optional[Dict[str, int]] = None,
) -> Topology:
    graph = {"elements": elements, "dependencies": dependencies}
    trace = {"spans": spans, "phases": []}
    run_context = _run_context(wall_end_us, max_jobs=max_jobs, resource_capacities=resource_capacities)
    return run_context, graph, trace


def _duration_for(uid: str, default_us: int, durations: Optional[Dict[str, int]]) -> int:
    return (durations or {}).get(uid, default_us)


# --- Topology factories (Part 36.1) ---

def linear_chain(
    n: int = 3, duration_us: int = 10000,
    durations: Optional[Dict[str, int]] = None,
    requested_target_last: bool = True,
) -> Topology:
    """elem0 -> elem1 -> ... -> elem(n-1), each depending only on its
    immediate predecessor, run strictly sequentially."""
    uids = [f"elem{i}.bst" for i in range(n)]
    elements = [
        _element(uid, requested_target=requested_target_last and i == n - 1)
        for i, uid in enumerate(uids)
    ]
    dependencies = [_dependency(uids[i - 1], uids[i]) for i in range(1, n)]

    spans = []
    t = 0
    for uid in uids:
        d = _duration_for(uid, duration_us, durations)
        spans.append(_span(uid, t, d))
        t += d

    return _build(elements, dependencies, spans, wall_end_us=t, max_jobs=1)


def diamond(duration_us: int = 10000, durations: Optional[Dict[str, int]] = None) -> Topology:
    """a -> {b, c} -> d: b and c run concurrently between a and d."""
    a, b, c, d = "a.bst", "b.bst", "c.bst", "d.bst"
    elements = [_element(a), _element(b), _element(c), _element(d, requested_target=True)]
    dependencies = [_dependency(a, b), _dependency(a, c), _dependency(b, d), _dependency(c, d)]

    da = _duration_for(a, duration_us, durations)
    db = _duration_for(b, duration_us, durations)
    dc = _duration_for(c, duration_us, durations)
    dd = _duration_for(d, duration_us, durations)
    mid = da + max(db, dc)
    spans = [
        _span(a, 0, da),
        _span(b, da, db),
        _span(c, da, dc),
        _span(d, mid, dd),
    ]
    return _build(elements, dependencies, spans, wall_end_us=mid + dd, max_jobs=2)


def fan_in(
    n: int = 4, duration_us: int = 10000, durations: Optional[Dict[str, int]] = None,
) -> Topology:
    """n independent predecessors converging on one successor."""
    pred_uids = [f"pred{i}.bst" for i in range(n)]
    sink = "sink.bst"
    elements = [_element(uid) for uid in pred_uids] + [_element(sink, requested_target=True)]
    dependencies = [_dependency(uid, sink) for uid in pred_uids]

    pred_durations = [_duration_for(uid, duration_us, durations) for uid in pred_uids]
    ready_us = max(pred_durations)
    spans = [_span(uid, 0, d) for uid, d in zip(pred_uids, pred_durations)]
    sink_dur = _duration_for(sink, duration_us, durations)
    spans.append(_span(sink, ready_us, sink_dur))

    return _build(elements, dependencies, spans, wall_end_us=ready_us + sink_dur, max_jobs=n)


def fan_out(
    n: int = 4, duration_us: int = 10000, durations: Optional[Dict[str, int]] = None,
) -> Topology:
    """one predecessor, n independent successors (all requested targets)."""
    source = "source.bst"
    succ_uids = [f"succ{i}.bst" for i in range(n)]
    elements = [_element(source)] + [_element(uid, requested_target=True) for uid in succ_uids]
    dependencies = [_dependency(source, uid) for uid in succ_uids]

    source_dur = _duration_for(source, duration_us, durations)
    spans = [_span(source, 0, source_dur)]
    finish = source_dur
    for uid in succ_uids:
        d = _duration_for(uid, duration_us, durations)
        spans.append(_span(uid, source_dur, d))
        finish = max(finish, source_dur + d)

    return _build(elements, dependencies, spans, wall_end_us=finish, max_jobs=n)


def multiple_equal_predecessors(duration_us: int = 10000) -> Topology:
    """target depends on two predecessors that finish at exactly the
    same normalized time but sit at different depths (shallow.bst is a
    direct root; deep_pre.bst -> deep.bst is a 2-level chain) - feeds
    tie-break tests (Part 36.4: same finish, different depth -> greater
    depth wins)."""
    shallow, deep_pre, deep, target = "shallow.bst", "deep_pre.bst", "deep.bst", "target.bst"
    elements = [
        _element(shallow), _element(deep_pre), _element(deep),
        _element(target, requested_target=True),
    ]
    dependencies = [
        _dependency(deep_pre, deep),
        _dependency(shallow, target),
        _dependency(deep, target),
    ]
    tie_us = 2 * duration_us
    spans = [
        _span(shallow, 0, tie_us),
        _span(deep_pre, 0, duration_us),
        _span(deep, duration_us, duration_us),
        _span(target, tie_us, duration_us),
    ]
    return _build(elements, dependencies, spans, wall_end_us=tie_us + duration_us, max_jobs=2)


def deep_unequal_predecessors(duration_us: int = 10000, chain_length: int = 3) -> Topology:
    """target depends on a shallow predecessor that finishes early and a
    `chain_length`-deep chain that finishes later - target's ready time
    is governed by the deep chain, not the shallow one."""
    shallow = "shallow.bst"
    chain_uids = [f"deep{i}.bst" for i in range(chain_length)]
    target = "target.bst"

    elements = [_element(shallow)] + [_element(uid) for uid in chain_uids] + [
        _element(target, requested_target=True)
    ]
    dependencies = [_dependency(chain_uids[i - 1], chain_uids[i]) for i in range(1, chain_length)]
    dependencies.append(_dependency(shallow, target))
    dependencies.append(_dependency(chain_uids[-1], target))

    spans = [_span(shallow, 0, duration_us)]
    t = 0
    for uid in chain_uids:
        spans.append(_span(uid, t, duration_us))
        t += duration_us
    target_dur = duration_us
    spans.append(_span(target, t, target_dur))

    return _build(elements, dependencies, spans, wall_end_us=t + target_dur, max_jobs=2)


def independent_branches(
    n: int = 2, chain_length: int = 3, duration_us: int = 10000,
) -> Topology:
    """n fully disconnected linear chains sharing no dependencies -
    each branch's last element is a requested target."""
    elements: List[dict] = []
    dependencies: List[dict] = []
    spans: List[dict] = []
    finish = 0

    for branch in range(n):
        uids = [f"branch{branch}_elem{i}.bst" for i in range(chain_length)]
        for i, uid in enumerate(uids):
            elements.append(_element(uid, requested_target=(i == chain_length - 1)))
            if i > 0:
                dependencies.append(_dependency(uids[i - 1], uid))
        t = 0
        for uid in uids:
            spans.append(_span(uid, t, duration_us))
            t += duration_us
        finish = max(finish, t)

    return _build(elements, dependencies, spans, wall_end_us=finish, max_jobs=n)


def graph_with_terminal_and_nonterminal_tasks(duration_us: int = 10000) -> Topology:
    """A mix of requested and non-requested elements: `dep.bst` is
    required (an ancestor of the requested `target.bst`), while
    `orphan.bst` -> `orphan_child.bst` form a branch entirely
    unreachable from any requested target - feeds leaf/deferrability
    analysis (dependencies not on any path to a requested target)."""
    dep, target = "dep.bst", "target.bst"
    orphan, orphan_child = "orphan.bst", "orphan_child.bst"

    elements = [
        _element(dep), _element(target, requested_target=True),
        _element(orphan), _element(orphan_child),
    ]
    dependencies = [
        _dependency(dep, target),
        _dependency(orphan, orphan_child),
    ]
    spans = [
        _span(dep, 0, duration_us),
        _span(target, duration_us, duration_us),
        _span(orphan, 0, duration_us),
        _span(orphan_child, duration_us, duration_us),
    ]
    return _build(elements, dependencies, spans, wall_end_us=2 * duration_us, max_jobs=2)


# --- Helpers for tests that consume the above ---

def write_run_dir(tmp_path: Path, topology: Topology, name: str = "run") -> Path:
    """Write a `(run_context, graph, trace)` topology to disk in the
    run-context.json/graph.json/trace.json layout `bga.ingest.loader`
    expects, and return the run directory path."""
    run_context, graph, trace = topology
    run_dir = tmp_path / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def build_analyzer(tmp_path: Path, topology: Topology, name: str = "run", **kwargs) -> BuildEfficiencyAnalyzer:
    """Write a topology to disk and return a loaded (but not yet
    analyzed) `BuildEfficiencyAnalyzer` - `**kwargs` are forwarded to
    the analyzer constructor (e.g. `cold=True`, `historical_runs=...`)."""
    run_dir = write_run_dir(tmp_path, topology, name=name)
    analyzer = BuildEfficiencyAnalyzer(run_dir, **kwargs)
    analyzer.load()
    return analyzer
