"""UX-1187: every element view carries duration and level, and the level filter composes with Top-N.

Measured before, on the 1,202-element run (`--layers 20 --width 60`):
"All elements" had duration and no depth, "What does my element wait on"
depth and no duration.
"""

import re

import pytest

from bga import schemas
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

SHAPE = ("--layers", "20", "--width", "60")


def test_every_element_view_carries_duration_and_level():
    presets = schemas.schema(schemas.ANALYZE)["properties"]["elements"][schemas.PRESETS]
    short = {
        preset["name"]: sorted({"element", "element_durations", "unweighted_depth"} - set(preset["columns"]))
        for preset in presets
    }
    assert {name: gap for name, gap in short.items() if gap} == {}, short


_TABLE = """(() => {
  const t = document.querySelector('table[data-table="elements"]');
  const shown = [...t.querySelectorAll('tbody tr')].filter((tr) => tr.checkVisibility());
  const raw = (tr, c) => tr.querySelector(`td[data-column="${c}"]`)?.dataset.raw;
  return shown.map((tr) => [raw(tr, 'element'), raw(tr, 'unweighted_depth')]);
})()"""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_a_level_filter_composes_with_top_n(big, tmp_path):
    run = big
    state = "v.elements=All%20elements&t.elements.unweighted_depth=%3D%2012&n.elements=10:element_durations"
    with Browser(find_chrome()) as browser:
        rows = browser.measure(f"{pages.export_uri(run, tmp_path / 'page')}#elements~{state}", _TABLE, 1440, 900)
    assert len(rows) == 10 and {depth for _, depth in rows} == {"12"}, rows


def test_the_producer_publishes_what_each_element_blocks():
    """`dependents` is `dependent_count`'s population, capped at 40 as `direct` is."""
    from bga.graph.fan_in import DIRECT_NAMES_CAP, compute_fan_in
    from bga.ingest.models import DependencyEdge, Element, Graph

    names = [f"s{index:04d}.bst" for index in range(1004)]
    graph = Graph(
        elements=[Element(uid="root.bst"), Element(uid="lone.bst")] + [Element(uid=name) for name in names],
        dependencies=[DependencyEdge(predecessor="root.bst", successor=name) for name in names]
        + [DependencyEdge(predecessor=names[0], successor="lone.bst")],
    )
    rows = compute_fan_in(graph, {}, set())
    assert rows["root.bst"]["dependent_count"] == 1004
    assert rows["root.bst"]["dependents"] == names[:DIRECT_NAMES_CAP]
    assert rows[names[0]]["dependents"] == ["lone.bst"] and rows[names[0]]["dependent_count"] == 1
    assert rows["lone.bst"]["dependents"] == [] and rows["lone.bst"]["dependent_count"] == 0


FIXTURES = {
    "golden": pages.REPO / "tests/fixtures/golden/mixed_task_kinds",
    "macro_micro": pages.REPO / "tests/fixtures/macro_micro/run",
}

_CARDS = """(() => [...document.querySelectorAll('section[data-element]')].map((s) => {
  const line = s.querySelector('[data-list="dependents"]');
  return [s.dataset.element, s.dataset.onDemand === 'true', line && {
    names: [...line.querySelectorAll('[data-raw]')].map((n) => n.dataset.raw),
    more: line.querySelector('[data-more]')?.textContent ?? null}];
}))()"""


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    return pages.two_plane_run(tmp_path_factory.mktemp("whole"), shape=SHAPE, name="big")


def _anchor(uid):
    return "element-" + re.sub(r"[^\w-]+", "-", uid)


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
@pytest.mark.parametrize("label", ["golden", "macro_micro", "big"])
def test_the_card_lists_what_an_element_blocks(label, request, tmp_path):
    """No ranked card carries the Blocks list (+2,193 px on `xl_both`); the card an anchor
    builds names the most-blocking unranked element's dependents, exactly."""
    from tools.bga_view import payloads

    run = request.getfixturevalue("big") if label == "big" else FIXTURES[label]
    fan_in = payloads(str(run))["report.json"]["elements"]["fan_in"]
    uri = pages.export_uri(run, tmp_path)
    with Browser(find_chrome()) as browser:
        ranked = browser.measure(uri, _CARDS, 1440, 900)
        assert ranked and [uid for uid, _, line in ranked if line] == [], ranked
        unranked = sorted(set(fan_in) - {uid for uid, _, _ in ranked}, key=lambda u: -fan_in[u]["dependent_count"])
        if label != "big":
            assert unranked == [], unranked
            return
        uid = unranked[0]
        assert fan_in[uid]["dependent_count"] > 1, uid
        cards = browser.measure(f"{uri}#{_anchor(uid)}", _CARDS, 1440, 900)
    built = [line for name, on_demand, line in cards if name == uid and on_demand]
    assert built == [{"names": fan_in[uid]["dependents"], "more": None}], built


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_card_counts_the_dependents_past_the_cap(big, tmp_path, monkeypatch):
    """The 1,202 run's one element past 40 dependents (toolchain.bst, 1,200) has a ranked card,
    so the count is published past the cap on an unranked one to draw it."""
    import tools.bga_view as view

    real = view.payloads
    uid = "layer18/mod001.bst"

    def past_the_cap(*args, **kwargs):
        documents = real(*args, **kwargs)
        documents["report.json"]["elements"]["fan_in"][uid]["dependent_count"] += 1200
        return documents

    monkeypatch.setattr(view, "payloads", past_the_cap)
    with Browser(find_chrome()) as browser:
        cards = browser.measure(f"{pages.export_uri(big, tmp_path)}#{_anchor(uid)}", _CARDS, 1440, 900)
    built = [line["more"] for name, on_demand, line in cards if name == uid and on_demand]
    assert built == [", +1,200 more"], built
