"""UX-1377: a cached element is a choke point of the graph, not a bottleneck of the run.

`bga whatif --element lib0.bst` refuses an element with no measured
duration; the text report used to name the same elements as bottlenecks.
Input classes: cold, incremental with some cached, incremental with all cached.
"""

import copy
import json
import os
import pathlib
import subprocess
import sys

from bga.report.text import format_text
from tests.fixtures import topologies as topo

REPO = pathlib.Path(__file__).resolve().parents[2]
COLD = REPO / "tests/fixtures/same_build_twice_cold/run"
INCREMENTAL = REPO / "tests/fixtures/same_build_twice_incremental/run"


class _Result:
    """The attributes `format_text` reads, with only `structural` filled."""

    def __init__(self, structural):
        self.run_id = "test-run"
        self.total_duration_us = 40_000_000
        self.signals = {}
        self.structural = structural
        self.floors = {}
        self.attribution = {}
        self.confidence = {}
        self.violations = []
        self.utilisation = {}
        self.occupancy = {}
        self.pipeline_overhead = {}


def _bga(*args) -> str:
    env = dict(os.environ, PYTHONPATH=str(REPO))
    run = subprocess.run([sys.executable, "-m", "bga.cli", *args], capture_output=True, text=True, cwd=REPO, env=env)
    assert run.returncode == 0, run.stderr
    return run.stdout


def _bottleneck_line(report: str) -> str:
    lines = [line.strip() for line in report.splitlines() if "Bottlenecks Identified" in line]
    assert len(lines) <= 1
    return lines[0] if lines else ""


def test_an_incremental_run_names_only_what_it_rebuilt():
    line = _bottleneck_line(_bga("analyze", str(INCREMENTAL)))
    assert line == "Bottlenecks Identified: 1 - lib3.bst (3 without measured build time)"


def test_the_json_publishes_the_split_beside_the_choke_points():
    bottleneck = json.loads(_bga("analyze", str(INCREMENTAL), "--format", "json"))["bottleneck"]
    assert {c["element_uid"] for c in bottleneck["choke_points"]} == {"lib0.bst", "lib1.bst", "lib2.bst", "lib3.bst"}
    assert sorted(bottleneck["unpriced_choke_points"]) == ["lib0.bst", "lib1.bst", "lib2.bst"]


def test_a_cold_run_is_unchanged():
    line = _bottleneck_line(_bga("analyze", str(COLD)))
    assert line.startswith("Bottlenecks Identified: 4 - ")
    assert "cached" not in line


def test_an_all_cached_run_names_no_element_and_states_the_cached_count(tmp_path):
    run_context, graph, trace = copy.deepcopy(topo.the_same_build_twice()[1])
    run_context["queue_summary"] = {"build": {"processed": 0, "skipped": 4, "failed": 0}}
    trace["spans"] = []
    report = _bga("analyze", str(topo.write_run_dir(tmp_path, (run_context, graph, trace))))
    assert "lib" not in _bottleneck_line(report)
    assert "4 cached" in report


def test_a_document_whose_choke_points_are_all_unpriced_names_none():
    structural = {
        "metrics": {"num_elements": 4, "num_edges": 3, "max_depth": 3},
        "bottleneck": {
            "choke_points": [{"element_uid": u, "downstream_count": 1} for u in ("a.bst", "b.bst")],
            "unpriced_choke_points": ["a.bst", "b.bst"],
        },
        "parallelism": {},
    }

    line = _bottleneck_line(format_text(_Result(structural), section="graph"))
    assert line == "Bottlenecks Identified: 0 (2 without measured build time)"


def test_a_pulled_only_choke_point_is_unpriced_beside_a_rebuilt_one(tmp_path):
    """Owner's review of #352: a PULL span is work time, not a build; only BUILD prices a bottleneck."""
    run_context, graph, trace = copy.deepcopy(topo.the_same_build_twice()[1])
    trace["spans"].append(
        {
            "task_key": "lib0.bst|PULL|PULL|0",
            "ts_us": 0,
            "dur_us": 3_000_000,
            "resources": ["NETWORK"],
            "primary_resource": "NETWORK",
        }
    )
    run = str(topo.write_run_dir(tmp_path, (run_context, graph, trace)))
    bottleneck = json.loads(_bga("analyze", run, "--format", "json"))["bottleneck"]
    assert sorted(bottleneck["unpriced_choke_points"]) == ["lib0.bst", "lib1.bst", "lib2.bst"]
    assert (
        _bottleneck_line(_bga("analyze", run)) == "Bottlenecks Identified: 1 - lib3.bst (3 without measured build time)"
    )


def test_an_unstarted_choke_point_is_not_called_cached(tmp_path):
    """Owner's re-review of #352: an interrupted cold run has no cache hit to claim."""
    run_context, graph, trace = copy.deepcopy(topo.the_same_build_twice()[0])
    trace["spans"] = [span for span in trace["spans"] if not span["task_key"].startswith("lib3.bst|")]
    line = _bottleneck_line(_bga("analyze", str(topo.write_run_dir(tmp_path, (run_context, graph, trace)))))
    assert line.startswith("Bottlenecks Identified: 3 - "), line
    assert line.endswith(" (1 without measured build time)"), line
    assert "lib3.bst" not in line and "cached" not in line
