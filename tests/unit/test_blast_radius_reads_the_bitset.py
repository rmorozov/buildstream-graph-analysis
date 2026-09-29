"""UX-1106: `compute_blast_radius` sums durations off the bitset, decoding no set."""

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.cli import main
from bga.diagnostics.analyzer import DiagnosticsAnalyzer
from bga.graph.edg import ReachabilitySets, analyze_graph
from bga.ingest.loader import load_all
from bga.normalize.timestamps import normalize_trace


def _write(run_dir, names, edges):
    run_dir.mkdir(parents=True)
    dur = 1000
    elements = [{"uid": n, "requested_target": False} for n in names]
    deps = [{"predecessor": a, "successor": b} for a, b in edges]
    spans = [
        {
            "task_key": f"{n}|BUILD|BUILD|0",
            "ts_us": i * dur,
            "dur_us": dur * (i + 1),
            "resources": ["PROCESS"],
            "primary_resource": "PROCESS",
        }
        for i, n in enumerate(names)
    ]
    ctx = {
        "trace_epsilon_us": dur,
        "wall_start_us": 0,
        "wall_end_us": 10**7,
        "max_jobs": 1,
        "resource_capacities": {"PROCESS": 1},
    }
    (run_dir / "run-context.json").write_text(json.dumps(ctx))
    (run_dir / "graph.json").write_text(json.dumps({"elements": elements, "dependencies": deps}))
    (run_dir / "trace.json").write_text(json.dumps({"spans": spans, "phases": []}))


CLASSES = {
    "chain": (["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")]),
    "wide": (["r", "x", "y", "z"], [("r", "x"), ("r", "y"), ("r", "z")]),
    "diamond": (["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]),
    "disconnected": (["a", "b", "c"], [("a", "b")]),
}


def _analyzer(run_dir):
    rc, g, tr = load_all(run_dir)
    tasks, _ = normalize_trace(tr, g, rc.trace_epsilon_us)
    return DiagnosticsAnalyzer(tasks, analyze_graph(g, tasks)), tasks


def _check(run_dir):
    da, tasks = _analyzer(run_dir)
    sets = da.graph_analysis["reachable_downstream"]
    assert isinstance(sets, ReachabilitySets)
    dur = {}
    for t in tasks:
        dur[t.task_key.element_uid] = dur.get(t.task_key.element_uid, 0) + t.dur_us
    results = da.compute_blast_radius()
    assert results
    assert len(sets._cache) == 0, f"{len(sets._cache)} sets decoded"
    for r in results:
        want = sum(dur.get(u, 0) for u in sets[r.element_uid])
        assert r.downstream_weighted_duration_us == want, r.element_uid
    return results


@pytest.mark.parametrize("name", list(CLASSES))
def test_input_classes(tmp_path, name):
    names, edges = CLASSES[name]
    _write(tmp_path / "run", names, edges)
    _check(tmp_path / "run")


def test_synthetic_layers_20_width_60(tmp_path):
    assert main(["gen-synthetic", str(tmp_path / "run"), "--layers", "20", "--width", "60", "--seed", "1"]) == 0
    assert len(_check(tmp_path / "run")) > 1000


def test_plain_dict_ranks_as_today(tmp_path):
    names, edges = CLASSES["diamond"]
    _write(tmp_path / "run", names, edges)
    da, _ = _analyzer(tmp_path / "run")
    fast = [(r.element_uid, r.downstream_weighted_duration_us) for r in da.compute_blast_radius()]
    sets = da.graph_analysis["reachable_downstream"]
    da.graph_analysis["reachable_downstream"] = {u: set(sets[u]) for u in sets}
    plain = [(r.element_uid, r.downstream_weighted_duration_us) for r in da.compute_blast_radius()]
    assert plain == fast
