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
  const read = (key) => {
    const line = s.querySelector(`[data-list="${key}"]`);
    return line && {
      names: [...line.querySelectorAll('[data-raw]')].map((n) => n.dataset.raw),
      links: [...line.querySelectorAll('a[href][data-raw]')].map((a) => a.getAttribute('href')),
      more: line.querySelector('[data-more]')?.textContent ?? null};
  };
  return [s.dataset.element, s.dataset.onDemand === 'true', read('dependents'), read('direct')];
}))()"""

# UX-1200: the card's Focus, and the investigation's one Blocks figure.
_FOCUSED = """(() => {
  document.querySelector(`button.focus-this[data-focus-element="__UID__"]`)?.click();
  const panel = document.querySelector('[data-role=focus-investigation] [data-group=relationships]');
  const rows = [...(panel?.querySelectorAll('dt') ?? [])].map((dt) => [dt.textContent, dt.nextElementSibling]);
  return rows.filter(([label]) => label === 'Blocks').map(([, dd]) => dd.dataset.raw);
})()"""


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    return pages.two_plane_run(tmp_path_factory.mktemp("whole"), shape=SHAPE, name="big")


def _anchor(uid):
    return "element-" + re.sub(r"[^\w-]+", "-", uid)


def _line(row, field, count):
    """What a card's `data-list=<field>` line must read for one `fan_in` row."""
    names = row[field]
    more = row[count] - len(names)
    return names and {
        "names": names,
        "links": [f"#{_anchor(n)}" for n in names],
        "more": f", +{more:,} more" if more > 0 else None,
    }


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
@pytest.mark.parametrize("label", ["golden", "macro_micro", "big"])
def test_the_card_lists_what_an_element_blocks(label, request, tmp_path):
    """Every card, ranked (Ruslan 05:49) or built by an anchor, links what its element blocks
    and depends on, exactly, and its Focus investigation's Blocks is `dependent_count`."""
    from tools.bga_view import payloads

    run = request.getfixturevalue("big") if label == "big" else FIXTURES[label]
    fan_in = payloads(str(run))["report.json"]["elements"]["fan_in"]
    uri = pages.export_uri(run, tmp_path)
    with Browser(find_chrome()) as browser:
        ranked = browser.measure(uri, _CARDS, 1440, 900)
        wrong = [
            (uid, blocks, direct)
            for uid, _, blocks, direct in ranked
            if uid in fan_in
            and (blocks or None, direct or None)
            != (
                _line(fan_in[uid], "dependents", "dependent_count") or None,
                _line(fan_in[uid], "direct", "direct_count") or None,
            )
        ]
        assert ranked and wrong == [], wrong
        unranked = sorted(set(fan_in) - {card[0] for card in ranked}, key=lambda u: -fan_in[u]["dependent_count"])
        if label != "big":
            assert unranked == [], unranked
            return
        assert len([card[2]["links"] for card in ranked if card[0] == "layer12/mod058.bst"][0]) == 6
        uid = unranked[0]
        assert fan_in[uid]["dependent_count"] > 1, uid
        cards = browser.measure(f"{uri}#{_anchor(uid)}", _CARDS, 1440, 900)
        blocks = browser.measure(f"{uri}#{_anchor(uid)}", _FOCUSED.replace("__UID__", uid), 1440, 900)
    built = [line for name, on_demand, line, _ in cards if name == uid and on_demand]
    assert built == [_line(fan_in[uid], "dependents", "dependent_count")], built
    assert blocks == [str(fan_in[uid]["dependent_count"])], blocks


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_card_counts_the_dependents_past_the_cap(big, tmp_path):
    """The 1,202 run's one element past 40 dependents (toolchain.bst, 1,200) draws "+N more" on
    its ranked card, and its links plus N is the investigation's Blocks."""
    uid = "toolchain.bst"
    uri = f"{pages.export_uri(big, tmp_path)}#{_anchor(uid)}"
    with Browser(find_chrome()) as browser:
        cards = browser.measure(uri, _CARDS, 1440, 900)
        blocks = browser.measure(uri, _FOCUSED.replace("__UID__", uid), 1440, 900)
    built = [line for name, on_demand, line, _ in cards if name == uid and not on_demand]
    assert [line["more"] for line in built] == [", +1,160 more"], built
    assert blocks == [str(len(built[0]["links"]) + 1160)] == ["1200"], (blocks, built)
