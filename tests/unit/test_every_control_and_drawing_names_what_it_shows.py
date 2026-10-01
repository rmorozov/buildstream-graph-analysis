"""UX-1162: a table's tools, the inspect links, the copy and twin controls
name what they act on; a drawing's `aria-details` carries its values;
a published strip's name leads with what it shows. UX-1169: each
drawing's `aria-details` reaches a node the tree exposes (6 of 17 before),
"View as JSON" is named by its question, not its key (46 before), the
chapter fold's name holds its visible label, the filter badge is `status`.

Read from Chromium's accessibility tree (`cdp.mjs --ax`). Measured on the
two-plane review page before the fix: 77 `a.inspect` in one name, 17
`copy-markdown` in one, 17 `copy-rows` in 8, 14 `copy-sql` in one, 6
`twin-toggle` in one, 4 `top-n` in one, 3 `table-filter` in one; 10 of 16
drawings routed to a bare range.
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
    "inspect": ("a.inspect", "c.getAttribute('href')"),
    "copy-sql": ("button.copy-sql", "c.dataset.copy"),
    "twin-toggle": ("button.twin-toggle", "null"),
    "copy-markdown": ("input.copy-markdown", "null"),
    "copy-rows": ("button.copy-rows", "null"),
    "top-n": ("select.top-n", "null"),
    "table-filter": ("input.table-filter", "null"),
}

#: A range and a count and nothing else: "0 ms → 8.1 min across 6 rows."
BARE_RANGE = re.compile(r"^-?[\d.,%]+(?: [^\s\d→]+)? → -?[\d.,%]+(?: \S+)?(?: across [\d,]+ rows?)?\.?$")

#: What a strip shows, then its numbers: "Fanin: 0 → 113, ...".
LEADS = re.compile(r"^[A-Za-z][^:]*: ")

_TAG = (
    pages.FULL_LAYOUT_JS
    + """
(async () => {
  document.querySelector('[data-all="false"]')?.click();
  for (const more of document.querySelectorAll("button.show-all-cards")) more.click();
  // One question fold, not all: every fold's SQL at once overruns `cdp.mjs --ax` on the review page.
  for (const fold of document.querySelectorAll("#utilisation details, details.question-group:first-of-type")) fold.open = true;
  let n = 0;
  for (const b of document.querySelectorAll("button.chapter-open")) b.setAttribute("data-ax-text", b.textContent);
  const typed = document.querySelector(".table-tools:has(.badge) input.table-filter");
  if (typed) {
    typed.setAttribute("data-ax-typed", "1");
    typed.value = "zzzz";
    typed.dispatchEvent(new Event("input", { bubbles: true }));
  }
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
  for (const d of document.querySelectorAll("svg[aria-details]")) {
    const to = document.getElementById(d.getAttribute("aria-details"));
    d.setAttribute("data-ax-details", to ? to.getAttribute("aria-label") || to.textContent : "");
    d.setAttribute("data-ax-n", d.parentElement.dataset.n ?? "");
    if (d.closest("#utilisation")) d.setAttribute("data-ax-util", "1");
  }
  return ["button", "link", "checkbox", "combobox", "searchbox", "textbox", "image", "status"];
})()
"""
)


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def tree(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1162-{request.param}")
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


def _one_name_many_acts(nodes):
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


def _drawings(nodes):
    return [n for n in nodes if n["role"] == "image" and "data-ax-details" in n["attrs"]]


@needs_browser
class TestEveryControlAndDrawingNamesWhatItShows:
    def test_the_kinds_are_on_the_page(self, tree):
        label, by_width = tree
        found = {n["attrs"].get("data-ax-kind") for n in by_width[1440]}
        wanted = set(KINDS) if label == "two_plane" else {"inspect", "copy-rows", "copy-markdown"}
        assert wanted <= found, (label, found)

    def test_no_two_controls_of_a_kind_share_a_name_unless_they_act_alike(self, tree):
        label, by_width = tree
        for width, nodes in by_width.items():
            shared = _one_name_many_acts(nodes)
            assert shared == {}, (label, width, {k: v[:3] for k, v in shared.items()})

    def test_no_drawing_details_a_bare_range(self, tree):
        label, by_width = tree
        for width, nodes in by_width.items():
            drawn = _drawings(nodes)
            assert drawn, (label, width)
            bare = [n["attrs"]["data-ax-details"] for n in drawn if BARE_RANGE.match(n["attrs"]["data-ax-details"])]
            assert bare == [], (label, width, bare)

    def test_a_column_strip_details_every_row_it_plots(self, tree):
        label, by_width = tree
        strips = [n for n in _drawings(by_width[1440]) if n["attrs"].get("data-printed") == "rows"]
        assert strips, label
        short = [
            (n["name"], n["attrs"]["data-ax-n"], n["attrs"]["data-ax-details"][:60])
            for n in strips
            if len(n["attrs"]["data-ax-details"].split(", ")) != int(n["attrs"]["data-ax-n"])
        ]
        assert short == [], (label, short)

    def test_a_strip_name_leads_with_what_it_shows(self, tree):
        label, by_width = tree
        strips = [n for n in by_width[1440] if n["role"] == "image" and n["attrs"].get("data-role") == "density-strip"]
        assert strips, label
        unled = [n["name"] for n in strips if not LEADS.match(n["name"])]
        assert unled == [], (label, unled)

    def test_the_utilisation_strip_is_in_the_tree_once_its_fold_is_open(self, tree):
        label, by_width = tree
        if label != "two_plane":
            pytest.skip("the review page's #utilisation carries the buckets strip")
        for width, nodes in by_width.items():
            found = [n["name"] for n in nodes if n["role"] == "image" and n["attrs"].get("data-ax-util")]
            assert found, (label, width)

    def test_every_drawing_s_details_reach_a_node_the_tree_exposes(self, tree):
        label, by_width = tree
        for width, nodes in by_width.items():
            drawn = [n for n in nodes if n["role"] == "image" and "aria-details" in n["attrs"]]
            assert drawn, (label, width)
            unreached = [n["name"][:60] for n in drawn if not n["details"]]
            assert unreached == [], (label, width, len(drawn), unreached)

    def test_a_json_toggle_is_named_by_its_question_not_its_key(self, tree):
        label, by_width = tree
        toggles = [n for n in by_width[1440] if "data-json-toggle" in n["attrs"]]
        assert toggles, label
        keyed = [n["name"] for n in toggles if n["name"].endswith(n["attrs"]["data-json-toggle"])]
        assert keyed == [], (label, len(toggles), keyed[:3])
        assert all(n["name"].startswith("View as JSON: ") for n in toggles), (label, toggles[0]["name"])

    def test_a_chapter_fold_s_name_holds_its_visible_label(self, tree):
        label, by_width = tree
        folds = [n for n in by_width[1440] if "data-ax-text" in n["attrs"]]
        assert folds, label
        unheld = [
            (n["attrs"]["data-ax-text"], n["name"])
            for n in folds
            if n["attrs"]["data-ax-text"].split(" ", 1)[1] not in n["name"]
        ]
        assert unheld == [], (label, unheld)

    def test_a_filtered_table_s_count_is_a_live_region(self, tree):
        label, by_width = tree
        for width, nodes in by_width.items():
            filtered = any("data-ax-typed" in n["attrs"] for n in nodes)
            assert filtered or label != "two_plane", (label, width)
            counts = [
                n["name"] for n in nodes if n["role"] == "status" and "badge" in n["attrs"].get("class", "").split()
            ]
            # `UX-1176`: a badge is in the tree at rest too, empty - `test_a_status_is_announced.py` holds that half.
            assert counts or not filtered, (label, width, counts)
