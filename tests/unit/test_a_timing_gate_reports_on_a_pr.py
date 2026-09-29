"""`UX-1121`: a timing gate reports on a pull request and fails nowhere
but a push to main and the daily `timing.yml`, which fails only when
two consecutive scheduled runs agree (each tool's `--carry`, `UX-442`).

The `test` cell is replayed with `test_a_run_red_for_another_reason_adopts_nothing`'s
engine: the gate steps made red, the cell's result read per event.
"""
import pathlib
import re
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_a_run_red_for_another_reason_adopts_nothing import (
    DRIFT,
    MAIN,
    PERF,
    REPO,
    _cell,
    _holds,
    _jobs,
    _status,
)

TIMING = REPO / ".github/workflows/timing.yml"
PR = {**MAIN, "event_name": "pull_request", "ref": "refs/pull/7/merge"}
GATES = (("dev_tier_drift.py", "timing-tier-carry-"),
         ("dev_perf_ratchet.py", "timing-perf-carry-"))


def _result(red, github, tmp_path):
    return _cell(_jobs()["test"], "3.12", red, github, tmp_path)[0]


@pytest.mark.parametrize("red", [
    pytest.param({DRIFT}, id="drift"),
    pytest.param({PERF}, id="perf"),
    pytest.param({DRIFT, PERF}, id="both"),
])
def test_a_red_timing_gate_does_not_fail_a_pull_request(red, tmp_path):
    assert _result(red, PR, tmp_path) == "success", red


@pytest.mark.parametrize("red", [
    pytest.param({DRIFT}, id="drift"),
    pytest.param({PERF}, id="perf"),
])
def test_a_red_timing_gate_still_fails_a_push_to_main(red, tmp_path):
    """The control: a replay nothing could fail passes the PR case too."""
    assert _result(red, MAIN, tmp_path) == "failure", red


def test_a_pull_request_reports_both_gates_as_notices():
    context = {"matrix": {"python-version": "3.12"}}
    reporting = [s["name"] for s in _jobs()["test"]["steps"]
                 if "::notice::" in (s.get("run") or "")
                 and "tier_gate" in s["run"] and "perf_gate" in s["run"]
                 and _holds(s.get("if"), {**context, "github": PR}, _status(["failure"]))]
    assert len(reporting) == 1, reporting


def _timing():
    doc = yaml.safe_load(TIMING.read_text(encoding="utf-8"))
    return doc, doc.get("on", doc.get(True)) or {}


def test_the_timing_workflow_runs_daily_and_on_demand():
    _doc, on = _timing()
    assert on.get("schedule"), on
    assert "workflow_dispatch" in on, on
    assert "pull_request" not in on and "push" not in on, on


@pytest.mark.parametrize("tool,family", GATES)
def test_each_gate_carries_from_a_family_of_its_own(tool, family):
    """`--carry` is the two-run rule; its cache keys must be timing.yml's
    own, or ci.yml's per-push series would stand in for the second run."""
    doc, _on = _timing()
    steps = [s for job in doc["jobs"].values() for s in job["steps"]]
    runs = [s for s in steps if tool in (s.get("run") or "") and "--against" in s["run"]]
    assert len(runs) == 1, [s.get("name") for s in runs]
    carry = re.search(r'--carry "([^"]+)"', runs[0]["run"])
    assert carry, runs[0]["run"]
    caches = [s for s in steps if "actions/cache" in str(s.get("uses"))
              and s.get("with", {}).get("path") == carry[1]]
    assert {s["uses"].split("@")[0] for s in caches} == {
        "actions/cache/restore", "actions/cache/save"}, caches
    for step in caches:
        keys = [step["with"]["key"], *str(step["with"].get("restore-keys", "")).split()]
        assert all(key.startswith(family) for key in keys), (tool, keys)


@pytest.mark.parametrize("red, result", [
    pytest.param(set(), "success", id="green"),
    pytest.param({"drift"}, "failure", id="drift"),
    pytest.param({"perf"}, "failure", id="perf"),
])
def test_the_daily_run_fails_when_a_gate_held(red, result, tmp_path):
    doc, _on = _timing()
    (job,) = doc["jobs"].values()
    names = {s["name"] for s in job["steps"] if s.get("id") in red}
    github = {**MAIN, "event_name": "schedule"}
    assert _cell(job, "3.12", names, github, tmp_path)[0] == result
