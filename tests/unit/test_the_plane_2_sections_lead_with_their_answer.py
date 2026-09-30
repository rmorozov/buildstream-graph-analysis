"""UX-1151: each Plane 2 section opens with its answer, and says each number once.

Booted on the two-plane page the view review read (114 elements), `golden`
and `macro_micro`: the first block under each Plane 2 heading is a sentence;
no section draws two pairs with one value and near-identical labels; the two
concurrency measures carry two names; `binary_cost` ranks by a column it
draws and names its share column; "Plane 1"/"Plane 2" and "CPU" have one
spelling.
"""

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
NO_PLANE_2 = "this page carries no Plane 2 report"
ONE_CONCURRENCY = "this page draws fewer than two concurrencies"
NO_BINARY_COST = "this page has no binary_cost section"

PLANE2 = ("plane2_coverage", "binary_cost", "peak_memory", "element_join_coverage")

_MEASURE = (
    pages.FULL_LAYOUT_JS
    + r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) box.setAttribute("data-open", "true");
  const stem = (w) => (w.endsWith("sses") ? w.slice(0, -2) : /[^s]s$/.test(w) ? w.slice(0, -1) : w);
  const words = (label) => new Set(label.toLowerCase().match(/[a-z0-9]+/g).map(stem));
  // Near-identical: the two differ only by a word that names a count, not a measure.
  const FILLER = new Set(["count", "number", "total", "of"]);
  const alike = (a, b) => [...a, ...b].every((w) => (a.has(w) && b.has(w)) || FILLER.has(w));
  const value = (dt) => {
    const dd = dt.nextElementSibling;
    const num = dd && dd.querySelector(":scope > .num");
    return num ? num.getAttribute("data-raw") : (dd ? dd.textContent.trim() : "");
  };
  const out = { sections: {}, repeats: [], concurrency: {}, spelling: [] };
  for (const id of __PLANE2__) {
    const section = document.getElementById(id);
    if (!section) continue;
    const first = [...section.children].find(
      (child) => child.tagName !== "H3" && !child.classList.contains("section-head"));
    const text = first ? first.textContent.trim() : "";
    out.sections[id] = { first: first ? first.tagName + "." + first.className : null, text };
    const pairs = [...section.querySelectorAll(":scope > dl.pairs > dt")].map(
      (dt) => ({ label: dt.textContent.trim(), value: value(dt) }));
    for (let i = 0; i < pairs.length; i++) {
      for (let j = i + 1; j < pairs.length; j++) {
        const a = pairs[i], b = pairs[j];
        if (a.value !== b.value) continue;
        const wa = words(a.label), wb = words(b.label);
        if (alike(wa, wb)) out.repeats.push([id, a.label, b.label, a.value]);
      }
    }
  }
  for (const key of ["max_concurrency", "max_observed_concurrency"]) {
    const dt = document.querySelector(`dt[data-key="${key}"]`);
    if (dt) out.concurrency[key] = dt.textContent.trim();
  }
  const cost = document.getElementById("binary_cost");
  if (cost) {
    const drawn = [...cost.querySelectorAll("table[data-table] > thead th")];
    const select = cost.querySelector("select.top-n");
    out.cost = {
      heads: drawn.map((th) => th.textContent.trim()),
      columns: drawn.map((th) => th.getAttribute("data-column")),
      ranked: select ? select.value.split(":")[1] || null : null,
      offered: select ? [...select.options].map((o) => o.value.split(":")[1]).filter(Boolean) : [],
      text: cost.textContent,
    };
  }
  const main = document.querySelector("main");
  for (const found of (main.textContent.match(/\bPlane[12]\b|\bCpus?\b/g) || [])) out.spelling.push(found);
  return out;
})()
""".replace("__PLANE2__", json.dumps(list(PLANE2)))
)


def _two_plane(into):
    run = pages.two_plane_run(into, ("--layers", "8", "--width", "14"))
    page = pathlib.Path(into) / "report.html"
    import tools.bga_view as view

    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1151-{request.param}")
    uri = _two_plane(into) if request.param == "two_plane" else pages.export_uri(pages.FIXTURES[request.param], into)
    with Browser(chrome) as opened:
        result = opened.measure(uri, _MEASURE)
    result["label"] = request.param
    return result


@needs_browser
class TestThePlane2SectionsLeadWithTheirAnswer:
    def test_the_two_plane_pages_carry_every_plane_2_section(self, measured):
        if measured["label"] == "golden":
            pytest.skip(NO_PLANE_2)
        assert sorted(measured["sections"]) == sorted(PLANE2), measured["sections"]

    def test_each_plane_2_section_opens_with_a_sentence(self, measured):
        bad = {
            key: seen
            for key, seen in measured["sections"].items()
            if not (seen["first"] or "").startswith("P.") or not seen["text"].endswith(".")
        }
        assert bad == {}, (measured["label"], bad)

    def test_no_section_says_one_number_twice(self, measured):
        assert measured["repeats"] == [], (measured["label"], measured["repeats"])

    def test_the_two_concurrencies_carry_two_names(self, measured):
        seen = measured["concurrency"]
        if len(seen) < 2:
            pytest.skip(ONE_CONCURRENCY)
        words = [set(label.lower().split()) for label in seen.values()]
        assert not (words[0] <= words[1] or words[1] <= words[0]), seen

    def test_binary_cost_ranks_by_a_column_it_draws(self, measured):
        cost = measured.get("cost")
        if not cost:
            pytest.skip(NO_BINARY_COST)
        assert set(cost["offered"]) <= set(cost["columns"]), cost["offered"]
        if cost["ranked"]:
            assert cost["ranked"] in cost["columns"], cost

    def test_binary_cost_names_its_share_column(self, measured):
        cost = measured.get("cost")
        if not cost:
            pytest.skip(NO_BINARY_COST)
        assert len(set(cost["heads"])) == len(cost["heads"]), cost["heads"]
        assert "Share of CPU" in cost["text"], cost["heads"]

    def test_plane_and_cpu_have_one_spelling(self, measured):
        assert measured["spelling"] == [], (measured["label"], sorted(set(measured["spelling"])))
