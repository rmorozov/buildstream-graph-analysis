"""UX-1155: a repeated control's accessible name says what it acts on, and
no drawing's name is a bare range.

Read from Chromium's accessibility tree (`cdp.mjs --ax`), not from
attributes. Measured on the two-plane review page before the fix: 37 `?`
doors in one name, 19 Focus in one, 57 marks in three, 14 "Investigate in
Perfetto" and 7 "Copy command" in one each, 74 folds named as their heading,
10 of 16 drawings named by a range alone. Two controls may share a name only
when they act on the same thing (one command, one query on one element).
"""

import collections
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Each kind's selector, and what one control of it acts on (`null`: itself).
KINDS = {
    "describe": ("button.describe", "null"),
    "collapse": ("button.collapse", "null"),
    "focus": ("button.focus-this", "null"),
    "mark": ("button.mark-this", "null"),
    "investigate": (".investigate > button", "c.parentElement.dataset.queryId + '|' + c.parentElement.dataset.element"),
    "copy-command": ("button.copy-step", "c.previousElementSibling?.dataset.argv ?? null"),
}

#: A range and a count and nothing else: "0 ms → 8.1 min across 6 rows."
BARE_RANGE = re.compile(r"^-?[\d.,%]+(?: [^\s\d→]+)? → -?[\d.,%]+(?: \S+)?(?: across [\d,]+ rows?)?\.?$")

_TAG = (
    pages.FULL_LAYOUT_JS
    + """
(async () => {
  document.querySelector('[data-all="false"]')?.click();
  for (const more of document.querySelectorAll("button.show-all-cards")) more.click();
  let n = 0;
"""
    + "".join(
        f"""  for (const c of document.querySelectorAll({sel!r})) {{
    c.setAttribute("data-ax-kind", {kind!r});
    c.setAttribute("data-ax-act", String({act} ?? "self-" + n++));
  }}
"""
        for kind, (sel, act) in KINDS.items()
    )
    + """  await new Promise((done) => setTimeout(done, 300));
  return ["button", "image", "heading"];
})()
"""
)


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def tree(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1155-{request.param}")
    if request.param == "two_plane":
        import tools.bga_view as view

        run = pages.two_plane_run(into, pages.REVIEW_SHAPE)
        page = pathlib.Path(into) / "report.html"
        view.export(str(run), str(page))
        uri = page.as_uri()
    else:
        uri = pages.export_uri(pages.FIXTURES[request.param], into)
    with Browser(chrome) as opened:
        widths = (1440, 390) if request.param == "two_plane" else (1440,)
        return request.param, {w: opened.ax(uri, _TAG, width=w, height=900) for w in widths}


def _shared(nodes):
    """`{kind: [(name, acts)]}` where one name covers controls acting on different things."""
    acts = collections.defaultdict(lambda: collections.defaultdict(set))
    for node in nodes:
        kind = node["attrs"].get("data-ax-kind")
        if kind:
            acts[kind][node["name"]].add(node["attrs"]["data-ax-act"])
    return {
        kind: [(name, len(on)) for name, on in names.items() if len(on) > 1]
        for kind, names in acts.items()
        if any(len(on) > 1 for on in names.values())
    }


@needs_browser
class TestAnAccessibleNameSaysWhatItActsOn:
    def test_the_kinds_are_on_the_page(self, tree):
        label, by_width = tree
        found = {n["attrs"].get("data-ax-kind") for n in by_width[1440]}
        assert {"describe", "collapse"} <= found, (label, found)
        if label == "two_plane":
            assert set(KINDS) <= found, (label, found)

    def test_no_two_controls_of_a_kind_share_a_name_unless_they_act_alike(self, tree):
        label, by_width = tree
        for width, nodes in by_width.items():
            shared = _shared(nodes)
            assert shared == {}, (label, width, {k: v[:3] for k, v in shared.items()})

    def test_no_control_repeats_a_heading(self, tree):
        """A fold named only by the heading it sits in says the heading twice, not what it does."""
        label, by_width = tree
        for width, nodes in by_width.items():
            headings = {n["name"] for n in nodes if n["role"] == "heading"}
            echoes = [n["name"] for n in nodes if n["attrs"].get("data-ax-kind") and n["name"] in headings]
            assert echoes == [], (label, width, echoes[:5])

    def test_no_drawing_is_named_by_a_bare_range(self, tree):
        label, by_width = tree
        for width, nodes in by_width.items():
            images = [n for n in nodes if n["role"] == "image" and n["attrs"].get("role") == "img"]
            assert images, (label, width)
            bare = [n["name"] for n in images if not n["name"] or BARE_RANGE.match(n["name"])]
            assert bare == [], (label, width, bare)
