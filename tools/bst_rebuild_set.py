#!/usr/bin/env python3
"""Expand a set of "cut" elements into the set of artifacts that must be
deleted for those elements - and everything above them - to really
rebuild.

Why this exists
---------------
Capturing a real timeline from a real, well-maintained BuildStream
project (round 6's goal: `freedesktop-sdk`) runs into a hard practical
wall. Building such a project from source takes many hours, because the
bottom of it is a full compiler bootstrap; but building it *with* the
project's own artifact cache enabled produces a capture in which nothing
was built at all, only pulled. Neither is a usable timeline.

The way out is to build against the cache and then delete a chosen,
bounded subgraph's artifacts, so exactly that subgraph rebuilds from
source with its real dependencies, its real parallelism and its real
per-element durations, on top of a cached base.

Deleting an arbitrary set does not work. BuildStream decides to build an
element when *its own* artifact is missing; a cached dependent is never
rebuilt and never asks for its dependencies at all. So deleting a
mid-level element alone changes nothing observable: its cached dependents
still satisfy the build. The delete set has to be **upward-closed** over
build edges - every element that transitively build-depends on a cut,
including the requested target itself, or the build stops short of it.

That closure is what this computes, from the same `graph.json` that
`tools/bst_show_to_graph.py` already produces, so the rebuild set is a
reproducible function of (project, target, cuts) rather than a
hand-maintained list that silently drifts.

Build edges only
----------------
The closure follows `build` edges and ignores `runtime` ones, matching
the rule `bga/graph/edg.py::build_element_graph` states and `UX-52`
enforced: a `runtime`-only edge does not make its dependent need the
dependency *at build time*, so it cannot propagate a rebuild. Runtime
dependents that are themselves cut are still included, via their own
build edges.

Usage
-----
    tools/bst_show_to_graph.py PROJECT_DIR TARGET graph.json
    tools/bst_rebuild_set.py graph.json --cut components/openssl.bst \\
                                        --cut components/expat.bst
"""

HELP = """Expand a set of "cut" elements into the artifacts that must be deleted
for those elements - and everything above them - to really rebuild.

The set has to be upward-closed over *build* edges: BuildStream builds an
element only when its own artifact is missing, so a cached dependent never
asks for its dependencies at all. Runtime edges do not propagate a rebuild.

Why this exists, and the captures it produced: this module's own
docstring, and docs/audits/round-11.md.
"""
import argparse
import json
import sys
from collections.abc import Iterable


def build_successors(dependencies: Iterable[dict]) -> dict[str, list[str]]:
    """`{predecessor: [successors]}` over `build` edges only."""
    successors: dict[str, list[str]] = {}
    for dep in dependencies:
        if dep.get("dependency_type") == "runtime":
            continue
        successors.setdefault(dep["predecessor"], []).append(dep["successor"])
    return successors


def rebuild_set(graph: dict, cuts: Iterable[str]) -> list[str]:
    """Return the sorted upward closure of `cuts` over build edges.

    Every cut must exist in the graph; a typo'd or out-of-closure cut is
    an error rather than an empty contribution, because silently
    dropping one would produce a capture with fewer rebuilt elements
    than intended and nothing to say so.
    """
    known = {element["uid"] for element in graph["elements"]}
    missing = sorted(set(cuts) - known)
    if missing:
        raise KeyError(
            "cut elements not present in the graph: " + ", ".join(missing)
        )

    successors = build_successors(graph["dependencies"])

    closure: set[str] = set()
    stack = list(cuts)
    while stack:
        uid = stack.pop()
        if uid in closure:
            continue
        closure.add(uid)
        stack.extend(successors.get(uid, ()))
    return sorted(closure)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("graph_json", help="graph.json from tools/bst_show_to_graph.py.")
    parser.add_argument(
        "--cut",
        action="append",
        default=[],
        required=True,
        metavar="ELEMENT",
        help="Element to rebuild, with everything above it. Repeatable.",
    )
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="Print only the size of the resulting set.",
    )
    args = parser.parse_args()

    with open(args.graph_json, encoding="utf-8") as handle:
        graph = json.load(handle)

    try:
        elements = rebuild_set(graph, args.cut)
    except KeyError as error:
        print(error.args[0], file=sys.stderr)
        return 1

    if args.count_only:
        print(len(elements))
    else:
        print("\n".join(elements))
    return 0


if __name__ == "__main__":
    sys.exit(main())
