#!/usr/bin/env python3
"""Generate a synthetic, realistically-shaped BuildStream run directory at
a scale no real example project in this repo reaches.

Why this exists
---------------
Every finding in the first audit round (`UX-27`..`UX-40`) came from
projects of 8-13 elements on one 4-core host, and
`docs/design-directions.md` named scale as the thing no audit had probed.
The second round probed it with the output of this script and found four
defects that were invisible at eleven elements - `UX-41` (level
decomposition), `UX-42` (quadratic attribution), `UX-43` (choke-point
degeneration), `UX-44` (the slack placeholder) - plus `UX-47`.

Those tasks' acceptance tests all say "the 1202-element scale fixture",
so the fixture has to be reproducible or the tests are unrunnable. That
is this script's whole job. Run with the same `--seed` and it emits a
byte-identical run directory.

What it is and is not
---------------------
This synthesizes the *ingested* form - `graph.json`, `trace.json`,
`run-context.json` - not a real build. It therefore exercises `bga`'s
**analysis** side at scale and says nothing about whether the capture
tools survive a thousand-element build (recorded as open item 6 in
`docs/design-directions.md`).

What makes it usable as evidence rather than noise is that the timeline
is not random: durations are drawn per layer, and the schedule is a real
dependency-respecting greedy pass onto a fixed builder pool, so no task
ever starts before its predecessors finish and no more than `--builders`
tasks are ever in flight. The resulting trace is internally consistent in
exactly the ways `bga`'s invariants check.

The graph shape is the normal shape of a real BuildStream project, which
is the point: one `toolchain.bst` import that everything depends on, N
layers of M modules with real fan-out/fan-in between adjacent layers, and
an `all.bst` stack on top. `UX-41` exists because that common base
element is precisely what collapses a BFS level decomposition.

Usage
-----
    tools/gen_synthetic_scale_run.py /tmp/run-scale-1200
    bga analyze /tmp/run-scale-1200

Defaults reproduce the fixture the round-2 findings were filed against:
1202 elements, 14 real levels, 16 builders, a ~362s horizon. Round 5
added a realistic minority of `runtime` dependencies (see
RUNTIME_EDGE_EVERY), which changes the dependency count and the exact
per-element numbers quoted in UX-41..UX-44 slightly - those docs record
the figures from the fixture as it stood when they were filed.
"""

import argparse
import json
import random
from pathlib import Path

# Defaults chosen to reproduce the round-2 audit fixture exactly. Changing
# any of them changes the numbers quoted in UX-41..UX-44's Motivation
# sections, so they are defaults rather than hardcoded constants only so
# the shape can be varied deliberately.
DEFAULT_LAYERS = 12
DEFAULT_WIDTH = 100
DEFAULT_BUILDERS = 16
DEFAULT_SEED = 1200

# Per-module build duration, in seconds. A real project's elements vary by
# an order of magnitude; a fixture where every element takes the same time
# would make several of the signals under test degenerate for reasons
# unrelated to the defects being probed.
MIN_DURATION_S = 0.4
MAX_DURATION_S = 9.0

# How many modules in the previous layer each module depends on. Two is
# enough to give the graph real fan-in without making it dense - the
# resulting `avg_fanout` of ~2.7 is close to what real projects show.
DEPS_PER_MODULE = 2

# UX-52: one in this many layer-to-layer edges is a `runtime` dependency
# rather than a `build` one. Real projects mix them as a matter of course
# - a `freedesktop-sdk` subgraph measured 27 runtime edges among 502,
# ~5% - and this generator previously emitted `build` unconditionally.
# That is precisely why a 1202-element scale probe could not find UX-52,
# where runtime edges were being counted as gating: the fixture had none.
# A fixture written alongside the analyzer tends to contain only the
# cases the analyzer already handles, so this ratio is deliberately
# copied from a real project rather than chosen.
RUNTIME_EDGE_EVERY = 20


def build_graph(layers, width, rng):
    """Return (elements, dependencies) for the layered graph.

    Shape: toolchain.bst (import, root) -> every module; each module in
    layer L depends on DEPS_PER_MODULE modules of layer L-1; all.bst
    (stack) depends on every module of the last layer.

    Every module also depends directly on toolchain.bst, which is what
    makes this a realistic BuildStream project and what makes a
    shortest-path level decomposition collapse it (UX-41).
    """
    elements = [
        {
            "uid": "toolchain.bst",
            "cache_key": "tc",
            "requested_target": False,
            "element_kind": "import",
        }
    ]
    dependencies = []

    def mod(layer, index):
        return f"layer{layer:02d}/mod{index:03d}.bst"

    for layer in range(layers):
        for index in range(width):
            uid = mod(layer, index)
            elements.append(
                {
                    "uid": uid,
                    "cache_key": f"k{(layer * width + index) % 100:02d}",
                    "requested_target": False,
                    "element_kind": "cmake",
                }
            )
            dependencies.append(
                {
                    "predecessor": "toolchain.bst",
                    "successor": uid,
                    "dependency_type": "build",
                }
            )
            if layer == 0:
                continue
            # Deterministic given the seed: rng is consumed in a fixed
            # order across the whole nested loop.
            for pred_index in rng.sample(range(width), DEPS_PER_MODULE):
                # UX-52: a deterministic minority of layer-to-layer edges
                # are `runtime`, which do not gate build scheduling.
                edge_ordinal = layer * width + index + pred_index
                dependency_type = (
                    "runtime" if edge_ordinal % RUNTIME_EDGE_EVERY == 0 else "build"
                )
                dependencies.append(
                    {
                        "predecessor": mod(layer - 1, pred_index),
                        "successor": uid,
                        "dependency_type": dependency_type,
                    }
                )

    elements.append(
        {
            "uid": "all.bst",
            "cache_key": "all",
            "requested_target": True,
            "element_kind": "stack",
        }
    )
    for index in range(width):
        dependencies.append(
            {
                "predecessor": mod(layers - 1, index),
                "successor": "all.bst",
                "dependency_type": "build",
            }
        )

    return elements, dependencies


def schedule(elements, dependencies, durations, builders):
    """Greedy dependency-respecting schedule onto `builders` slots.

    Returns {uid: (start_us, dur_us)}. This is a real schedule, not
    randomly-assigned timestamps: a task starts at the later of (its last
    predecessor's finish) and (the earliest moment a builder frees up),
    so the trace satisfies the same ordering and capacity properties a
    real capture does. That is what makes the fixture usable for probing
    attribution and occupancy rather than only for timing.

    `all.bst` and `toolchain.bst` are structural (0-duration) and occupy a
    slot for an instant, matching how BuildStream reports import/stack
    elements - and matching the real captures of examples/06, where
    UX-34's structural-element filtering was built against exactly this.
    """
    preds = {e["uid"]: [] for e in elements}
    succs = {e["uid"]: [] for e in elements}
    for dep in dependencies:
        preds[dep["successor"]].append(dep["predecessor"])
        succs[dep["predecessor"]].append(dep["successor"])

    # Topological order. Ties are broken by uid so the result depends only
    # on the seed, never on dict iteration order.
    remaining = {uid: len(p) for uid, p in preds.items()}
    ready = sorted(uid for uid, n in remaining.items() if n == 0)
    order = []
    while ready:
        uid = ready.pop(0)
        order.append(uid)
        for succ in sorted(succs[uid]):
            remaining[succ] -= 1
            if remaining[succ] == 0:
                ready.append(succ)
                ready.sort()

    # Greedy assignment: builder slots as finish-time counters.
    slots = [0] * builders
    placement = {}
    for uid in order:
        ready_at = max((placement[p][0] + placement[p][1] for p in preds[uid]), default=0)
        slot = min(range(builders), key=lambda i: (slots[i], i))
        start = max(ready_at, slots[slot])
        dur = durations[uid]
        slots[slot] = start + dur
        placement[uid] = (start, dur)
    return placement


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", type=Path, help="Run directory to create")
    parser.add_argument("--layers", type=int, default=DEFAULT_LAYERS)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--builders", type=int, default=DEFAULT_BUILDERS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--run-id",
        default="scale-1200",
        help="run_identity_hash written to every file. Must match across "
        "the three files or ingestion rejects the directory.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    elements, dependencies = build_graph(args.layers, args.width, rng)

    durations = {}
    for element in elements:
        uid = element["uid"]
        if element["element_kind"] in ("import", "stack"):
            # Structural elements do no build work. 1us rather than 0 so
            # they still appear as real spans - a 0-duration span is a
            # different edge case and not the one this fixture is for.
            durations[uid] = 1
        else:
            durations[uid] = int(rng.uniform(MIN_DURATION_S, MAX_DURATION_S) * 1_000_000)

    placement = schedule(elements, dependencies, durations, args.builders)
    horizon = max(start + dur for start, dur in placement.values())

    spans = [
        {
            "task_key": f"{uid}|BUILD|BUILD|0",
            "ts_us": placement[uid][0],
            "dur_us": placement[uid][1],
            "resources": ["PROCESS"],
            "primary_resource": "PROCESS",
        }
        for uid in sorted(placement)
    ]
    # Sort by start time, then key - the order a real capture produces.
    spans.sort(key=lambda s: (s["ts_us"], s["task_key"]))

    # Pipeline overhead is real in every BuildStream run and is what UX-40
    # taught the confidence model to stop penalizing; a fixture without it
    # would exercise a path real captures never take.
    loading_us = 900_000
    resolving_us = 1_100_000

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "graph.json").write_text(
        json.dumps(
            {
                "elements": elements,
                "dependencies": dependencies,
                "run_identity_hash": args.run_id,
            },
            indent=1,
        )
    )
    (args.output / "trace.json").write_text(
        json.dumps({"run_identity_hash": args.run_id, "spans": spans, "phases": []}, indent=1)
    )
    (args.output / "run-context.json").write_text(
        json.dumps(
            {
                "trace_epsilon_us": 50_000,
                "resource_capacities": {
                    "PROCESS": args.builders,
                    "DOWNLOAD": 10,
                    "UPLOAD": 4,
                },
                "max_jobs": args.builders,
                "native_max_jobs": 4,
                "native_max_jobs_source": "parsed_from_invocation",
                "host_cpu_count": args.builders,
                "wall_clock": {
                    "start_us": 0,
                    "end_us": horizon + loading_us + resolving_us,
                },
                "pipeline_overhead": [
                    {"phase": "Loading elements", "elapsed_us": loading_us},
                    {"phase": "Resolving elements", "elapsed_us": resolving_us},
                ],
                "run_identity": {"manifest_hash": args.run_id, "targets": ["all.bst"]},
            },
            indent=1,
        )
    )

    work = sum(d for _, d in placement.values())
    print(f"Wrote {args.output}")
    print(f"  elements:     {len(elements)}")
    print(f"  dependencies: {len(dependencies)}")
    print(f"  real levels:  {args.layers + 2} (toolchain, {args.layers} layers, all.bst)")
    print(f"  builders:     {args.builders}")
    print(f"  horizon:      {horizon / 1e6:.2f}s")
    print(f"  total work:   {work / 1e6:.2f}s")


if __name__ == "__main__":
    main()
