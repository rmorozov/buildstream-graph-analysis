"""UX-1214 follow-up: a card's "+N more", Blocks and Depends on, filters the element table to every one it counts.

Measured before, on `_wide` (each layer01 element names 51 dependencies): `depends_on:layer00/mod049.bst`
matched 0 of its 50 dependents (each one's published `direct` stopped at 40); Depends on's rest was a span.
"""

import json
import re

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

FIXTURES = {
    "golden": pages.REPO / "tests/fixtures/golden/mixed_task_kinds",
    "macro_micro": pages.REPO / "tests/fixtures/macro_micro/run",
}

# The filter box typed `__CLAUSE__`: rows matched, rows carrying the list, drawn cells, the not-applied sentence.
_TYPED = """(() => {
  const [key, uid] = "__CLAUSE__".split(/:(.*)/);
  const t = document.querySelector('table[data-table="elements"]');
  const tools = t.parentNode.querySelector(".table-tools");
  const box = tools?.querySelector("input.table-filter");
  const listed = [...t.querySelectorAll("tbody tr")]
    .filter((tr) => (tr.getAttribute(`data-list-${key}`) ?? "").split(" ").includes(uid)).length;
  const read = (clause) => {
    if (!box) return null;
    box.value = clause;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    const copy = tools.querySelector(".copy-rows")?.textContent ?? "";
    return Number((/([\\d,]+) matched row/.exec(copy) ?? [0, "-1"])[1].replace(/,/g, ""));
  };
  const matched = read("__CLAUSE__");
  read("nosuch:x");
  return { listed, matched, said: tools?.querySelector(".filter-unread")?.textContent ?? null,
           drawn: [...t.querySelectorAll("th, td")].filter((c) => ["depends_on", "blocks"].includes(c.dataset.column)).length };
})()"""

# From the Leaves view, the card's `[data-list=__LIST__]` "+N more" pressed.
_FOLLOW = """(() => {
  const view = document.querySelector('select.preset-view[data-table="elements"]');
  view.value = "Leaves";
  view.dispatchEvent(new Event("change"));
  const more = document.querySelector('section[data-element="__UID__"] [data-list="__LIST__"] a[data-more]');
  more?.click();
  const copy = document.querySelector('table[data-table="elements"]').parentNode
    .querySelector(".table-tools .copy-rows")?.textContent ?? "";
  return { text: more?.textContent ?? null, href: more?.getAttribute("href") ?? null, view: view.value,
           matched: Number((/([\\d,]+) matched row/.exec(copy) ?? [0, "-1"])[1].replace(/,/g, "")) };
})()"""


def wide_run(into):
    """`gen-synthetic --layers 2 --width 50`, every layer01 element also naming all 50 of layer00: 51 each."""
    run = pages.scale_run(into, "wide", ("--layers", "2", "--width", "50"))
    graph = json.loads((run / "graph.json").read_text(encoding="utf-8"))
    uids = [element["uid"] for element in graph["elements"]]
    have = {(edge["predecessor"], edge["successor"]) for edge in graph["dependencies"]}
    graph["dependencies"] += [
        {"predecessor": lower, "successor": upper, "dependency_type": "build"}
        for upper in uids
        if upper.startswith("layer01/")
        for lower in uids
        if lower.startswith("layer00/") and (lower, upper) not in have
    ]
    (run / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
    # Every layer01 task (and the stack above them) starts after the last layer00 one ends, as the new edges say.
    trace = json.loads((run / "trace.json").read_text(encoding="utf-8"))
    late = max(span["ts_us"] + span["dur_us"] for span in trace["spans"] if span["task_key"].startswith("layer00/"))
    for span in trace["spans"]:
        if not span["task_key"].startswith(("layer00/", "toolchain")):
            span["ts_us"] += late
    (run / "trace.json").write_text(json.dumps(trace), encoding="utf-8")
    return run


@pytest.fixture(scope="module")
def wide(tmp_path_factory):
    return wide_run(tmp_path_factory.mktemp("wide"))


def _anchor(uid):
    return "element-" + re.sub(r"[^\w-]+", "-", uid)


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
@pytest.mark.parametrize("label", ["golden", "macro_micro", "wide"])
def test_a_card_s_more_reaches_every_dependency_both_ways(label, request, tmp_path):
    """`depends_on:<uid>` holds every element <uid> blocks and `blocks:<uid>` every one it depends on, past any
    40-name cap; both "+N more" land there; the not-applied sentence names no undrawn column."""
    from tools.bga_view import payloads

    run = request.getfixturevalue("wide") if label == "wide" else FIXTURES[label]
    fan_in = payloads(str(run))["report.json"]["elements"]["fan_in"]
    blocker = max(fan_in, key=lambda u: fan_in[u]["dependent_count"])
    needer = max(fan_in, key=lambda u: fan_in[u]["direct_count"])
    if label == "wide":
        blocker = "layer00/mod049.bst"
        # The 40-capped route undercounts here: no dependent's first 40 names it, and 40 of 51 inverted.
        assert sum(blocker in row["direct"][:40] for row in fan_in.values()) == 0, blocker
        assert len(fan_in[needer]["direct"][:40]) == 40 < fan_in[needer]["direct_count"] == 51, needer
    uri = pages.export_uri(run, tmp_path)
    with Browser(find_chrome()) as browser:
        down = browser.measure(uri, _TYPED.replace("__CLAUSE__", f"depends_on:{blocker}"), 1440, 900)
        up = browser.measure(uri, _TYPED.replace("__CLAUSE__", f"blocks:{needer}"), 1440, 900)
        if label == "wide":
            follow = [
                browser.measure(
                    f"{uri}#{_anchor(uid)}",
                    _FOLLOW.replace("__UID__", uid).replace("__LIST__", key),
                    1440,
                    900,
                    fresh_history=True,
                )
                for uid, key in ((blocker, "dependents"), (needer, "direct"))
            ]
    for typed, count in ((down, fan_in[blocker]["dependent_count"]), (up, fan_in[needer]["direct_count"])):
        got = typed["listed"] if typed["matched"] is None else typed["matched"]
        assert count > 0 and typed["drawn"] == 0 and got == count, (label, count, typed)
        assert typed["said"] is None or not re.search(r"Depends on|Blocks", typed["said"]), typed["said"]
    if label != "wide":
        return
    assert [(f["text"], f["view"], f["matched"]) for f in follow] == [
        ("+10 more", "All elements", 50),
        ("+11 more", "All elements", 51),
    ], follow
