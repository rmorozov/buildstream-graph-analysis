"""UX-1135: the joint saving is compared against each element priced alone.

Summing the horizon's steps telescopes, so `joint >= sum` held by
construction and the report called every set "separate pieces of work".
"""

from pathlib import Path
from types import SimpleNamespace

from bga import whatif
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.findings import _outlook_findings
from bga.graph.edg import compute_optimization_horizon, price_joint_saving
from bga.ingest.models import DependencyEdge, Element, Graph

MACRO_MICRO = Path("tests/fixtures/macro_micro/run")


def _priced(edges, durations, steps=None):
    graph = Graph(
        elements=[Element(uid) for uid in durations],
        dependencies=[DependencyEdge(a, b) for a, b in edges],
    )
    horizon = compute_optimization_horizon(graph, durations)
    return price_joint_saving(graph, durations, steps or horizon[:2])


def _sentence(joint):
    result = SimpleNamespace(signals={"joint_saving": joint}, total_duration_us=1_000_000_000)
    (finding,) = [f for f in _outlook_findings(result) if f["id"] == "joint-saving"]
    return finding["title"] + " " + finding["detail"][0]


def test_an_element_worth_nothing_alone_compounds_and_names_the_order():
    # Two parallel branches: B is worth 0 s alone, 60 once A is fixed.
    joint = _priced([], {"A": 100_000_000, "B": 60_000_000})

    assert joint["elements"] == ["A", "B"]
    assert joint["sum_of_individual_us"] == 40_000_000
    assert joint["joint_saving_us"] == 100_000_000
    assert joint["relation"] == "compound"
    assert joint["worth_more_after"] == ["B"]
    assert joint["savings_add"] is False
    assert _sentence(joint).endswith("more than the 40.0 s alone: B pays off after A")


def test_independent_elements_add():
    # One chain: each link is worth its own duration, alone or together.
    joint = _priced([("A", "B")], {"A": 100_000_000, "B": 50_000_000})

    assert joint["relation"] == "add"
    assert joint["savings_add"] is True
    assert "separate pieces of work that do not overlap" in _sentence(joint)


def test_elements_sharing_a_rival_overlap():
    # A -> B against a parallel C of 120: each alone saves 30, together still 30.
    steps = [{"element_uid": "A", "saving_us": 30_000_000}, {"element_uid": "B", "saving_us": 0}]
    joint = _priced([("A", "B")], {"A": 100_000_000, "B": 50_000_000, "C": 120_000_000}, steps)

    assert joint["sum_of_individual_us"] > joint["joint_saving_us"]
    assert joint["relation"] == "overlap"
    assert "fixing one makes the others worth less" in _sentence(joint)


def test_the_individual_sum_is_what_whatif_prices_each_element_at():
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(MACRO_MICRO)
    result = analyzer.analyze(MACRO_MICRO)
    joint = result.signals["joint_saving"]
    alone = [whatif.project(result, analyzer.graph, [uid])["projected"]["joint_saving_us"] for uid in joint["elements"]]

    assert joint["sum_of_individual_us"] == sum(alone)
    assert joint["relation"] == "compound"
