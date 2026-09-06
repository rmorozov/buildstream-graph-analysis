"""UX-719: the bottleneck fan-in/fan-out prose named the wrong direction.

`bottleneck.high_fanin_elements` ranks `G.in_degree`, and the raw edge
list runs predecessor -> successor with the predecessor built first -
a dependency. So an in-edge is a dependency, not a dependent, and the
two blocks' sentences had that backwards.

The degree each block ranks is derived here from `graph.json`'s own
`predecessor`/`successor` records, not read off the schema's prose -
a sentence copied from the fix would pass however wrong it was.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas

RUN = REPO / "tests/fixtures/macro_micro/run"


def _raw_degrees():
    """In/out degree per element, counted from the declared edges
    directly - independent of the analyzer and of any prose."""
    deps = json.loads((RUN / "graph.json").read_text())["dependencies"]
    in_degree, out_degree = {}, {}
    for dep in deps:
        out_degree[dep["predecessor"]] = out_degree.get(dep["predecessor"], 0) + 1
        in_degree[dep["successor"]] = in_degree.get(dep["successor"], 0) + 1
    return in_degree, out_degree


def _report():
    from tools.bga_view import payloads

    return payloads(str(RUN))["report.json"]


def _bottleneck_node():
    return schemas.schema(schemas.ANALYZE)["properties"]["bottleneck"]


def _column(node, key):
    for column in node["bga:columns"]:
        if column["key"] == key:
            return column
    raise KeyError(key)


class TestEachBlockRanksTheDegreeCountedFromTheEdges:
    """Numeric cross-check, no prose involved."""

    def test_high_fanin_matches_raw_in_degree(self):
        in_degree, _ = _raw_degrees()
        rows = _report()["bottleneck"]["high_fanin_elements"]
        assert rows, "fixture should surface at least one row"
        for row in rows:
            assert row["fan_in"] == in_degree[row["element_uid"]], row

    def test_high_fanout_matches_raw_out_degree(self):
        _, out_degree = _raw_degrees()
        rows = _report()["bottleneck"]["high_fanout_elements"]
        assert rows, "fixture should surface at least one row"
        for row in rows:
            assert row["fan_out"] == out_degree[row["element_uid"]], row

    def test_the_acceptance_example(self):
        rows = _report()["bottleneck"]["high_fanin_elements"]
        assert rows[0]["element_uid"] == "app.bst"
        in_degree, out_degree = _raw_degrees()
        # The motivation's own reading: many dependencies, one dependent.
        assert in_degree["app.bst"] == 8
        assert out_degree["app.bst"] == 1


class TestTheProseNamesTheDirectionItRanks:
    """`high_fanin_elements` ranks in-degree - how many dependencies an
    element names for itself. `high_fanout_elements` ranks out-degree -
    how many other elements name it as theirs. The check is structural
    (which side of "depend on" carries "many others"), not a match
    against the sentence the fix wrote."""

    @staticmethod
    def _names_its_own_dependencies(text):
        """"Elements [that] depend on many others" - the subject is
        the one doing the depending."""
        text = text.lower()
        i = text.find("depend on")
        j = text.find("many others")
        return -1 not in (i, j) and i < j

    @staticmethod
    def _is_named_as_a_dependency(text):
        """"many others depend on" [it] - the subject is depended on."""
        text = text.lower()
        i = text.find("many others")
        j = text.find("depend on")
        return -1 not in (i, j) and i < j

    def test_high_fanin_block_says_it_holds_the_dependencies(self):
        node = _bottleneck_node()["properties"]["high_fanin_elements"]
        assert self._names_its_own_dependencies(node["description"]), \
            node["description"]
        assert not self._is_named_as_a_dependency(node["description"])

    def test_high_fanout_block_says_others_hold_it(self):
        node = _bottleneck_node()["properties"]["high_fanout_elements"]
        assert self._is_named_as_a_dependency(node["description"]), \
            node["description"]
        assert not self._names_its_own_dependencies(node["description"])

    def test_fan_in_column_matches_the_untouched_anchor(self):
        """`elements.fan_in.direct_count` describes the same in-degree
        quantity and was not touched by this fix - the two must agree
        on which phrase means "this element's own dependencies"."""
        anchor = schemas.schema(schemas.ANALYZE)["properties"]["elements"][
            "properties"]["fan_in"]["additionalProperties"][
            "properties"]["direct_count"]["description"]
        phrase = "dependencies this element names"
        assert phrase in anchor.lower()
        column = _column(_bottleneck_node()["properties"][
            "high_fanin_elements"], "fan_in")
        assert phrase in column["description"].lower()
        assert "naming this one as a dependency" not in \
            column["description"].lower()

    def test_fan_out_column_says_others_name_it(self):
        column = _column(_bottleneck_node()["properties"][
            "high_fanout_elements"], "fan_out")
        assert "naming this one as a dependency" in \
            column["description"].lower()
        assert "dependencies this element names" not in \
            column["description"].lower()


CLI_GUIDE = REPO / "docs/guides/cli.md"


class TestTheGuideOrdersTheSamePairTheSameWay:
    """`cli.md`'s `fan_in`, `fan_out` row names the same two phrases
    the schema does, in the same order - `fan_in` first."""

    @staticmethod
    def _row():
        for line in CLI_GUIDE.read_text(encoding="utf-8").splitlines():
            if "`fan_in`, `fan_out`" in line and "high_fanin_elements" in line:
                return line.lower()
        raise AssertionError("the fan_in/fan_out row was not found")

    def test_dependencies_named_before_elements_naming_it(self):
        row = self._row()
        own = row.find("dependencies this element names")
        named = row.find("naming this one as a dependency")
        assert -1 not in (own, named), row
        assert own < named, row
