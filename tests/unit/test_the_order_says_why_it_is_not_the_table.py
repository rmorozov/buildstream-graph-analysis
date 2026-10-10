"""UX-1342: the joint-saving order names the elements the time-concentration table lacks."""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.findings import _outlook_findings, compute_findings

RUNS = [Path("tests/fixtures/macro_micro/run"), Path("tests/fixtures/golden/mixed_task_kinds")]


def _lines(found):
    (joint,) = [f for f in found if f["id"] == "joint-saving"]
    return joint, [line for line in joint["detail"] if "Not the table above" in line]


@pytest.mark.parametrize("run", RUNS)
def test_the_line_names_exactly_the_joint_elements_missing_from_the_table(run):
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(run)
    found = compute_findings(analyzer.analyze(run))
    joint, lines = _lines(found)
    (table,) = [f for f in found if f["id"] == "time-concentration"]
    absent = {uid for uid in joint["elements"] if uid not in table["elements"]}

    assert absent
    assert len(lines) == 1
    assert _named(lines[0]) == absent
    if run.name == "run":
        assert "codegen.bst" in lines[0]


def _named(line):
    return set(re.split(r", | and ", re.search(r" so (.*?) enters? here", line).group(1)))


def _synthetic(elements, shown):
    horizon = [{"element_uid": uid, "makespan_after_us": 1_000_000} for uid in elements]
    detail = [{"element_uid": uid, "duration_us": 9_000_000} for uid in shown]
    joint = {"elements": elements, "joint_saving_us": 5_000_000, "sum_of_individual_us": 5_000_000, "relation": "add"}
    signals = {"joint_saving": joint, "optimization_horizon": horizon, "critical_path_detail": detail}
    return SimpleNamespace(signals=signals, total_duration_us=1_000_000_000)


def test_no_line_when_every_joint_element_is_in_the_table():
    _, lines = _lines(_outlook_findings(_synthetic(["A", "B"], ["A", "B"])))
    assert lines == []


def test_a_line_when_one_is_missing():
    _, lines = _lines(_outlook_findings(_synthetic(["A", "B"], ["A"])))
    assert len(lines) == 1 and "B enters here" in lines[0]
    assert "critical path" in lines[0] and "steps before it are done" in lines[0]


def test_the_cause_holds_when_the_absent_element_is_the_first_step():
    _, lines = _lines(_outlook_findings(_synthetic(["X", "A", "B"], ["A", "B", "C", "D"])))
    assert len(lines) == 1 and _named(lines[0]) == {"X"}
    assert "re-ranked" not in lines[0]


def test_only_joint_elements_are_named_never_a_table_element():
    _, lines = _lines(_outlook_findings(_synthetic(["A", "B"], ["A", "C"])))
    assert _named(lines[0]) == {"B"}


def test_two_absent_elements_take_the_plural():
    _, lines = _lines(_outlook_findings(_synthetic(["A", "B", "C"], ["A"])))
    assert _named(lines[0]) == {"B", "C"} and " enter here" in lines[0]


def test_an_empty_table_names_nothing():
    _, lines = _lines(_outlook_findings(_synthetic(["A", "B"], [])))
    assert lines == []


def test_a_one_step_horizon_has_no_order_and_no_line():
    _, lines = _lines(_outlook_findings(_synthetic(["A"], ["B"])))
    assert lines == []
