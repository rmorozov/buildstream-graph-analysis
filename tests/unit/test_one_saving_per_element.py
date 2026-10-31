"""UX-1362: one element's saving is the same number in analyze, the structural list, correlate and whatif.

The shape is fdsdk's: a chain longer than the old eight-candidate cap, and one near-tie branch
whose 1 s slack was the structural ceiling's cap for every element on the chain.
"""

import json

import pytest

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.correlate import correlate
from bga.report.json import format_json
from bga.report.text import format_text
from bga.whatif import project
from tests.fixtures.topologies import _build, _dependency, _element, _span, write_run_dir

CHAIN = [f"c{i}.bst" for i in range(12)]
S = 1_000_000


def _topology():
    durations = {uid: (10 + 5 * i) * S for i, uid in enumerate(CHAIN)}
    elements = [dict(_element(uid, requested_target=uid == CHAIN[-1]), element_kind="autotools") for uid in CHAIN]
    elements.append(dict(_element("side.bst"), element_kind="autotools"))
    dependencies = [_dependency(CHAIN[i - 1], CHAIN[i]) for i in range(1, len(CHAIN))]
    # side.bst ties c1.bst less one second: the graph's smallest positive slack.
    dependencies += [_dependency(CHAIN[0], "side.bst"), _dependency("side.bst", CHAIN[2])]
    spans, at = [], 0
    for uid in CHAIN:
        spans.append(_span(uid, at, durations[uid]))
        if uid == CHAIN[1]:
            spans.append(_span("side.bst", at, durations[uid] - S))
        at += durations[uid]
    return _build(elements, dependencies, spans, wall_end_us=at, max_jobs=2)


@pytest.fixture(scope="module")
def readings(tmp_path_factory):
    run_dir = write_run_dir(tmp_path_factory.mktemp("one-saving"), _topology())
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()
    whatif = {}
    for uid in CHAIN:
        projected = project(result, analyzer.graph, [uid])["projected"]
        whatif[uid] = projected["joint_saving_us"]
    analysis = json.loads(format_json(result))
    joined = correlate(analysis, {"by_element": {}, "per_element_parallelism": [], "cpu_time": {"per_element": {}}})
    return result, analysis, joined, whatif, format_text(result)


def test_the_fixture_holds_a_one_second_tie_and_a_chain_past_eight(readings):
    _result, _analysis, _joined, whatif, _text = readings
    assert whatif["c1.bst"] == S
    assert sum(1 for saving in whatif.values() if saving > S) > 8


def test_analyze_publishes_whatifs_saving_for_every_chain_element(readings):
    result, _analysis, _joined, whatif, _text = readings
    detail = {d["element_uid"]: d["realizable_saving_us"] for d in result.signals["critical_path_detail"]}
    assert detail == whatif


def test_the_structural_opportunities_are_whatifs_savings(readings):
    _result, analysis, _joined, whatif, text = readings
    rows = analysis["sensitivity"]["top_opportunities"]
    assert [row["element_uid"] for row in rows] == sorted(whatif, key=lambda u: -whatif[u])[:5]
    for row in rows:
        assert row["saving_us"] == whatif[row["element_uid"]]
    assert f"- {CHAIN[-1]}: up to 65.0 s off the finish" in text
    assert "-> fixing it saves 65.0 s" in text


def test_correlate_publishes_whatifs_saving_for_every_chain_element(readings):
    _result, _analysis, joined, whatif, _text = readings
    published = {e["element"]: e["potential_saving_us"] for e in joined["elements"] if e["element"] in whatif}
    assert published == whatif
