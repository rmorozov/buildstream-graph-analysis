"""UX-1138: an element is pinned to one job when BuildStream resolved it one.

The capture flagged `pinned_to_one_job` from an argv `-j1`, and
autotools' default install step is `make -j1 install` while the build
step's width travels in `MAKEFLAGS`. On the fdsdk capture 5 of 9
elements read pinned at width 4, peaking at 8 to 12 work processes.
"""

import copy
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.plane2 import apply_resolved_widths, resolved_widths

FIXTURE_RUN = REPO / "tests/fixtures/macro_micro/run"
FIXTURE_PLANE2 = REPO / "tests/fixtures/macro_micro/plane2.json"


def _report_with_a_false_pin():
    report = json.loads(FIXTURE_PLANE2.read_text(encoding="utf-8"))
    for entry in report["per_element_parallelism"]:
        if entry["element"] == "codegen.bst":
            entry["requested_jobs"] = 1
            entry["findings"] = ["pinned_to_one_job"]
    return report


def _pinned(report):
    return sorted(e["element"] for e in report["per_element_parallelism"] if "pinned_to_one_job" in e["findings"])


def test_an_argv_pin_at_a_resolved_width_of_four_is_dropped():
    report = _report_with_a_false_pin()
    assert _pinned(report) == ["codegen.bst", "core.bst"]
    apply_resolved_widths(report, resolved_widths(str(FIXTURE_RUN / "graph.json")))
    assert _pinned(report) == ["core.bst"]


def test_a_resolved_width_of_one_is_pinned_whatever_the_argv_said():
    report = copy.deepcopy(_report_with_a_false_pin())
    for entry in report["per_element_parallelism"]:
        entry["findings"] = []
    apply_resolved_widths(report, resolved_widths(str(FIXTURE_RUN / "graph.json")))
    assert _pinned(report) == ["core.bst"]


def test_the_capacity_finding_names_only_the_resolved_pin(tmp_path):
    plane2 = tmp_path / "plane2.json"
    plane2.write_text(json.dumps(_report_with_a_false_pin()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from bga.cli import main; raise SystemExit(main())",
            "analyze",
            str(FIXTURE_RUN),
            "--plane2",
            str(plane2),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    )
    findings = {f["id"]: f for f in json.loads(result.stdout)["findings"]}
    assert findings["capacity-recommendation"]["elements"] == ["core.bst"]
