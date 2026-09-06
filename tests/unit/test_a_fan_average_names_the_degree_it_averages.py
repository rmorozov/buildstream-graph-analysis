"""UX-733: `avg_fanin`/`avg_fanout` named the wrong degree, and neither
sentence said the two numbers can never differ.

Which side is "dependencies" is derived here from `graph.json`'s own
`predecessor`/`successor` records (`UX-719`'s approach: an in-edge is a
dependency, an out-edge a dependent), not read off the schema's prose -
a sentence copied from the fix would pass however wrong it was. The
equality is derived the same way, from the raw edge count, not from
either description's claim about it.
"""
import json
import pathlib
import statistics
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas

RUN = REPO / "tests/fixtures/macro_micro/run"


def _raw_degrees():
    """Nodes and in/out degree per element, counted from the declared
    edges directly - independent of the analyzer and of any prose."""
    deps = json.loads((RUN / "graph.json").read_text())["dependencies"]
    nodes, in_degree, out_degree = set(), {}, {}
    for dep in deps:
        p, s = dep["predecessor"], dep["successor"]
        nodes.add(p)
        nodes.add(s)
        out_degree[p] = out_degree.get(p, 0) + 1
        in_degree[s] = in_degree.get(s, 0) + 1
    return nodes, in_degree, out_degree, len(deps)


def _report():
    from tools.bga_view import payloads

    return payloads(str(RUN))["report.json"]


def _graph_metrics():
    return schemas.schema(schemas.ANALYZE)["properties"]["graph_metrics"][
        "properties"]


class TestBothAveragesMatchTheDegreeTheyClaimAndEachOther:
    """Numeric cross-check, no prose involved."""

    def test_avg_fanin_is_the_mean_in_degree(self):
        nodes, in_degree, _, _ = _raw_degrees()
        mean_in = statistics.mean(in_degree.get(n, 0) for n in nodes)
        assert _report()["graph_metrics"]["avg_fanin"] == mean_in

    def test_avg_fanout_is_the_mean_out_degree(self):
        nodes, _, out_degree, _ = _raw_degrees()
        mean_out = statistics.mean(out_degree.get(n, 0) for n in nodes)
        assert _report()["graph_metrics"]["avg_fanout"] == mean_out

    def test_the_two_are_equal_by_the_handshake_lemma(self):
        nodes, _, _, n_edges = _raw_degrees()
        gm = _report()["graph_metrics"]
        assert gm["avg_fanin"] == gm["avg_fanout"] == n_edges / len(nodes)


class TestEachDescriptionNamesTheDegreeItAverages:
    """`avg_fanin` averages in-degree - how many dependencies an element
    names for itself, the same quantity `elements.fan_in.direct_count`
    already names correctly (`UX-719`'s untouched anchor). `avg_fanout`
    averages out-degree - how many other elements name it as theirs,
    i.e. its dependents. The check is structural (which word the
    sentence uses), not a match against the fix's own wording."""

    ANCHOR_PHRASE = "dependencies this element names"

    def test_the_anchor_still_calls_in_degree_dependencies(self):
        """Confirms the derivation, not the fix: `fan_in.direct_count`
        is untouched by this task and already names in-degree
        correctly - that's what "dependencies" means below."""
        anchor = schemas.schema(schemas.ANALYZE)["properties"]["elements"][
            "properties"]["fan_in"]["additionalProperties"][
            "properties"]["direct_count"]["description"].lower()
        assert self.ANCHOR_PHRASE in anchor

    def test_avg_fanin_names_dependencies_not_dependents(self):
        text = _graph_metrics()["avg_fanin"]["description"].lower()
        assert "dependencies" in text
        assert "dependents" not in text

    def test_avg_fanout_names_dependents_not_dependencies(self):
        text = _graph_metrics()["avg_fanout"]["description"].lower()
        assert "dependents" in text
        assert "dependencies" not in text


class TestBothDescriptionsStateTheEqualityByConstruction:
    """Two keys, one quantity - the Outcome's decision was to keep both
    and say so. A sentence that doesn't name the counterpart and the
    reason (every edge is one in-edge and one out-edge) leaves a reader
    to rediscover the redundancy the hard way."""

    def test_avg_fanin_names_avg_fanout_and_the_reason(self):
        text = _graph_metrics()["avg_fanin"]["description"].lower()
        assert "avg_fanout" in text
        assert "construction" in text
        assert "in-edge" in text and "out-edge" in text

    def test_avg_fanout_names_avg_fanin_and_the_reason(self):
        text = _graph_metrics()["avg_fanout"]["description"].lower()
        assert "avg_fanin" in text
        assert "construction" in text
        assert "in-edge" in text and "out-edge" in text
