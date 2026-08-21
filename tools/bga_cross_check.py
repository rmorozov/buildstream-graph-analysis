#!/usr/bin/env python3
"""Recompute, from a run directory alone, quantities `bga` also computes
internally, and report where the two disagree.

Why this exists
---------------
Every audit round from the third onward has been opened by some version
of this script, written from scratch each time, and it has found a defect
every time it was pointed somewhere new:

- `UX-50` - `sensitivity.critical_path_us` vs `t_infinity_observed`
  disagreed on a real `examples/06` capture (an element read as
  zero-duration).
- `UX-52` - the same pair disagreed on a real `freedesktop-sdk` graph
  (`runtime` edges counted as gating).
- `UX-53` - the same pair disagreed on `synthetic_multi_subproject`, a
  fixture checked in since before the first round (two per-element
  duration definitions).

Three findings from one check, each on a different input, is the argument
for it being a tool rather than a habit. The point is that these are
quantities `bga` derives **twice by different routes**: an independent
third derivation is what turns "they agree" from a tautology into
evidence.

What it is not
--------------
Not a test, and not a validator of `bga`'s invariants - `bga` has those
(`I4`, `I9`, `I11`, the hard gates) and reports them itself. This is the
outside view: naive, slow, obvious code that a reader can check by eye,
compared against the optimized implementations. When they disagree, the
naive one is not automatically right - `UX-53`'s first suspicion was the
wrong way round - but they cannot both be.

Quantization
------------
`bga` quantizes every timestamp to the epsilon grid at ingestion (Part
3.2), so a comparison against raw `trace.json` durations disagrees by up
to epsilon per element for reasons that are not defects. This quantizes
the same way, which is what makes a remaining disagreement worth
reading: on the 1202-element scale fixture, not doing so produced four
false alarms.

Usage
-----
    bga analyze -d RUN_DIR -f json > analysis.json
    tools/bga_cross_check.py RUN_DIR analysis.json
"""

HELP = """Recompute, from a run directory alone, quantities `bga` also computes
internally, and report where the two disagree.

An independent second implementation of the same arithmetic: agreement is
evidence, disagreement is a defect in one of them. Every audit round from
the third onward opened with some version of this, and it found something
every time it was pointed somewhere new.

The findings it produced are listed in this module's own docstring.
"""
import argparse
import json
import sys
from collections import defaultdict
from typing import Dict, List


def _load(run_dir: str):
    with open(f"{run_dir}/graph.json", encoding="utf-8") as handle:
        graph = json.load(handle)
    with open(f"{run_dir}/trace.json", encoding="utf-8") as handle:
        trace = json.load(handle)
    with open(f"{run_dir}/run-context.json", encoding="utf-8") as handle:
        context = json.load(handle)
    return graph, trace, context


def topological_order(graph: dict, build_only: bool):
    """(order, predecessors). Ties broken by uid so the result depends
    only on the input, never on dict iteration order."""
    successors: Dict[str, List[str]] = defaultdict(list)
    predecessors: Dict[str, List[str]] = defaultdict(list)
    nodes = {element["uid"] for element in graph["elements"]}
    for dep in graph["dependencies"]:
        if build_only and dep.get("dependency_type") == "runtime":
            continue
        successors[dep["predecessor"]].append(dep["successor"])
        predecessors[dep["successor"]].append(dep["predecessor"])

    indegree = {node: 0 for node in nodes}
    for preds in successors.values():
        for succ in preds:
            indegree[succ] += 1
    ready = sorted(node for node, n in indegree.items() if n == 0)
    order = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for succ in sorted(successors.get(node, ())):
            indegree[succ] -= 1
            if indegree[succ] == 0:
                ready.append(succ)
                ready.sort()
    return order, predecessors


def longest_path_elements(graph: dict, build_only: bool) -> int:
    order, predecessors = topological_order(graph, build_only)
    depth: Dict[str, int] = {}
    for node in order:
        depth[node] = max((depth[p] for p in predecessors.get(node, ())), default=-1) + 1
    return max(depth.values()) + 1 if depth else 0


def longest_path_us(graph: dict, durations: Dict[str, int], build_only: bool = True) -> int:
    order, predecessors = topological_order(graph, build_only)
    best: Dict[str, int] = {}
    for node in order:
        best[node] = durations.get(node, 0) + max(
            (best[p] for p in predecessors.get(node, ())), default=0
        )
    return max(best.values()) if best else 0


def run(run_dir: str, analysis: dict) -> int:
    graph, trace, context = _load(run_dir)
    spans = trace["spans"]
    epsilon = context.get("trace_epsilon_us", 50000)

    def quantize(ts: int) -> int:
        # Part 3.2's exact round-half-up rule, integers only.
        return ((2 * ts + epsilon) // (2 * epsilon)) * epsilon

    # The longest task per element, matching
    # `bga/graph/edg.py::compute_element_durations` - the definition
    # UX-53 made single.
    durations: Dict[str, int] = defaultdict(int)
    build_durations: Dict[str, int] = defaultdict(int)
    for span in spans:
        uid, kind = span["task_key"].split("|")[:2]
        length = quantize(span["ts_us"] + span["dur_us"]) - quantize(span["ts_us"])
        durations[uid] = max(durations[uid], length)
        if kind == "BUILD":
            build_durations[uid] = max(build_durations[uid], length)

    runtime_edges = sum(
        1 for d in graph["dependencies"] if d.get("dependency_type") == "runtime"
    )
    kinds: Dict[str, int] = defaultdict(int)
    for element in graph["elements"]:
        kinds[element.get("element_kind")] += 1
    tasks_per_element = len(spans) / len(durations) if durations else 0

    print(f"elements:   {len(graph['elements'])}")
    print(f"deps:       {len(graph['dependencies'])} ({runtime_edges} runtime)")
    print(f"spans:      {len(spans)} over {len(durations)} elements "
          f"({tasks_per_element:.1f} tasks/element)")
    print(f"kinds:      {dict(sorted(kinds.items(), key=lambda kv: -kv[1]))}")
    print(f"longest path: {longest_path_elements(graph, True)} elements build-only, "
          f"{longest_path_elements(graph, False)} counting runtime edges")
    print()

    checks = []

    def check(name, mine, reported, note=""):
        checks.append((name, mine, reported, mine == reported, note))

    structural = analysis.get("structural") or {}
    floors = analysis.get("floors") or {}
    signals = analysis.get("signals") or {}
    occupancy = analysis.get("occupancy") or {}

    if structural and signals:
        check("metrics.critical_path_length vs len(signals.critical_path)",
              structural["metrics"]["critical_path_length"],
              len(signals["critical_path"]))
        check("sensitivity.critical_path_us vs floors.t_infinity_observed",
              structural["sensitivity"]["critical_path_us"],
              floors["t_infinity_observed"])
        check("structural.metrics.num_elements vs graph.json",
              structural["metrics"]["num_elements"], len(graph["elements"]))
    if floors:
        check("independent longest weighted path vs t_infinity_observed",
              longest_path_us(graph, build_durations), floors["t_infinity_observed"])
        if signals:
            check("BUILD durations along the reported critical path vs t_infinity",
                  sum(build_durations[e] for e in signals["critical_path"]),
                  floors["t_infinity_observed"])
    if analysis.get("attribution"):
        check("sum(attribution categories) vs total_duration_us",
              sum(analysis["attribution"].values()), analysis["total_duration_us"])
    if occupancy.get("horizon_us"):
        busy = sum(quantize(s["ts_us"] + s["dur_us"]) - quantize(s["ts_us"]) for s in spans)
        check("busy time / horizon vs occupancy.average_concurrency",
              round(busy / occupancy["horizon_us"], 6),
              round(occupancy["average_concurrency"], 6))
    utilisation = analysis.get("utilisation") or {}
    if utilisation.get("buckets"):
        check("sum(utilisation buckets) vs total_accounted_us",
              sum(utilisation["buckets"].values()), utilisation["total_accounted_us"])

    agreed = 0
    for name, mine, reported, ok, note in checks:
        agreed += ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}: independent={mine} "
              f"reported={reported} {note}")
    print(f"\n{agreed}/{len(checks)} cross-checks agree")

    violations = analysis.get("violations") or []
    print(f"violations reported by bga: {len(violations)}")
    for violation in violations:
        print(f"    {violation.get('type', violation)}")

    return 0 if agreed == len(checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("run_dir", help="A bga run directory.")
    parser.add_argument("analysis_json", help="`bga analyze -f json` output for it.")
    args = parser.parse_args()

    with open(args.analysis_json, encoding="utf-8") as handle:
        analysis = json.load(handle)
    return run(args.run_dir, analysis)


if __name__ == "__main__":
    sys.exit(main())
