"""UX-1186 (styleguide §1, §3k): a population's key column is declared.

Every table declaring `bga:keyed_by` marks each mounted row (`data-element`
with an Inspect link, `data-binary`), a keyed map is never a `dl`, Focus on
an element dims such a table's other rows and never folds its section, and
the jump box finds a binary no mounted row holds. Chromium on `golden`,
`macro_micro` and `UX-1182`'s heavy-binary page, at 1440.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_LOOK = r"""
(async () => {
  const turn = () => new Promise((done) => setTimeout(done, 80));
  const own = (table) => [...table.querySelectorAll(":scope > tbody > tr")];
  const keyed = () => [...document.querySelectorAll("table[data-keyed-by]")];
  const tables = keyed().map((table) => {
    const kinds = table.getAttribute("data-keyed-by").split(" ");
    const rows = own(table);
    return {
      key: table.getAttribute("data-table"), kinds, rows: rows.length,
      element: rows.filter((tr) => tr.hasAttribute("data-element")
        && tr.querySelector(":scope > td > a.inspect")).length,
      binary: rows.filter((tr) => tr.hasAttribute("data-binary")).length,
    };
  });
  const maps = [...document.querySelectorAll("section[data-section]")]
    .filter((s) => ["wall_clock_share_us", "by_binary"].includes(s.getAttribute("data-section")))
    .map((s) => [s.getAttribute("data-section"), s.querySelectorAll("dl").length]);
  const mountedIn = (key) => new Set([...document.querySelectorAll(`table[data-table="${key}"] tr[data-element]`)]
    .map((tr) => tr.getAttribute("data-element")));
  const inElements = mountedIn("elements");
  const everywhere = [...document.querySelectorAll("[data-element]")].map((n) => n.getAttribute("data-element"));
  const uid = everywhere.find((u) => !inElements.has(u)) ?? everywhere[0];
  const type = async (value) => {
    const box = document.getElementById("jump");
    box.value = value;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    await turn();
  };
  await type(uid);
  document.querySelector('.jump-hits button[data-action="focus"]')?.click();
  await turn();
  const focused = document.documentElement.closest("[data-focus]") ?? document.querySelector("[data-focus]");
  const underFocus = keyed().map((table) => {
    const rows = own(table).filter((tr) => tr.hasAttribute("data-element"));
    return {
      key: table.getAttribute("data-table"),
      folded: table.closest("section[data-section]")?.getAttribute("data-unfocused") === "true",
      undimmedOthers: rows.filter((tr) => tr.getAttribute("data-element") !== uid
        && tr.getAttribute("data-dimmed") !== "true").length,
    };
  });
  const binary = __BINARY__;
  const mounted = Boolean(binary && document.querySelector(`tr[data-binary="${CSS.escape(binary)}"]`));
  let found = null, hash = null;
  if (binary) {
    await type(binary);
    const hit = document.querySelector(`.jump-hits button[data-jump="${CSS.escape(binary)}"]`);
    found = hit ? hit.closest("li").previousElementSibling?.getAttribute("data-group")
      ?? [...document.querySelectorAll(".jump-hits li[data-group]")].map((g) => g.getAttribute("data-group")).join(",") : null;
    hit?.click();
    await turn();
    hash = location.hash;
  }
  return { tables, maps, uid, focus: focused?.getAttribute("data-focus") ?? null, underFocus,
           binary, mounted, found, hash };
})()
"""


def _least_run_binary(run):
    by_binary = json.loads((run.parent / "plane2.json").read_text(encoding="utf-8"))["by_binary"]
    return min(by_binary, key=lambda name: (by_binary[name], name))


@pytest.fixture(scope="module")
def looked(tmp_path_factory):
    import tools.bga_view as view

    uris = pages.pages(tmp_path_factory, prefix="ux1186", labels=["golden", "macro_micro"])
    run = pages.heavy_binary_run(tmp_path_factory.mktemp("ux1186-heavy"))
    page = tmp_path_factory.mktemp("ux1186-heavy-page") / "report.html"
    view.export(str(run), str(page))
    binaries = {"golden": None, "macro_micro": None, "heavy": _least_run_binary(run)}
    uris["heavy"] = page.as_uri()
    with Browser(find_chrome()) as browser:
        return {
            label: browser.measure(uri, _LOOK.replace("__BINARY__", json.dumps(binaries[label])), 1440, 900)
            for label, uri in uris.items()
        }


@needs_browser
class TestAPopulationKeyIsDeclared:
    def test_the_populations_declare_their_key(self, looked):
        for label, out in looked.items():
            declared = {table["key"] for table in out["tables"]}
            assert "elements" in declared, (label, sorted(declared))
            assert "wall_clock_share_us" in declared, (label, sorted(declared))
            if label != "golden":
                assert {"binary_cost", "by_binary"} <= declared, (label, sorted(declared))

    def test_every_mounted_row_carries_its_key(self, looked):
        for label, out in looked.items():
            for table in out["tables"]:
                assert table["rows"] > 0, (label, table)
                if {"element", "task_uid"} & set(table["kinds"]):
                    assert table["element"] == table["rows"], (label, table)
                if "binary" in table["kinds"]:
                    assert table["binary"] == table["rows"], (label, table)

    def test_a_keyed_map_is_never_a_dl(self, looked):
        for label, out in looked.items():
            assert out["maps"] and all(dls == 0 for _key, dls in out["maps"]), (label, out["maps"])

    def test_focus_dims_a_keyed_table_and_never_folds_it(self, looked):
        for label, out in looked.items():
            assert out["focus"] == out["uid"], (label, out["focus"], out["uid"])
            for table in out["underFocus"]:
                assert not table["folded"], (label, out["uid"], table)
                assert table["undimmedOthers"] == 0, (label, out["uid"], table)

    def test_the_jump_box_finds_a_binary_off_the_page(self, looked):
        out = looked["heavy"]
        assert not out["mounted"], f"{out['binary']} is mounted - the clause would read the DOM, not the payload"
        assert out["found"] == "BINARY", out
        assert out["hash"].lstrip("#").split("~")[0] in {"by_binary", "binary_cost"}, out
