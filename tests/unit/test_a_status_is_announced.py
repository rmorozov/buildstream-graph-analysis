"""UX-1176: what the page announces is mounted before it is said.

Chromium's own accessibility tree, on `macro_micro` and the 114-element
two-plane run at 1440, every door open: each table badge is a `status`
node at rest, each table has a name, and the Jump and Ask boxes name a
mounted node that carries their no-match line. The drawing-values clip
rule (`UX-1169`) is read as computed style.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_OPEN = pages.OPEN_EVERY_DOOR_JS + "  return ['status', 'table'];"

_TYPE = r"""
(async () => {
  const turn = () => new Promise((done) => setTimeout(done, 50));
  const type = async (box, text) => {
    box.value = text;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    await turn();
  };
  const described = (box) => (document.getElementById(box.getAttribute("aria-describedby") ?? "") ?? null);
  const out = {};
  for (const [name, box] of [["jump", document.getElementById("jump")],
                             ["ask", document.querySelector("[data-role=query-element]")]]) {
    if (!box) { out[name] = null; continue; }
    const target = described(box);
    const before = target;
    await type(box, "zzzq");
    out[name] = { mounted: Boolean(before) && before === described(box) && before.isConnected,
                  role: target?.getAttribute("role") ?? null,
                  says: (target?.textContent ?? "").trim() };
    await type(box, "");
  }
  const values = document.querySelector("[data-role=drawing-values]");
  const style = values ? getComputedStyle(values) : null;
  out.values = style ? { clip: style.clipPath, width: values.getBoundingClientRect().width,
                         height: values.getBoundingClientRect().height } : null;
  out.badges = document.querySelectorAll(".table-tools .badge").length;
  out.hiddenBadges = document.querySelectorAll(".table-tools .badge[hidden]").length;
  return out;
})()
"""


@pytest.fixture(scope="module")
def heard(tmp_path_factory):
    uris = pages.pages(tmp_path_factory, prefix="ux1176", labels=["golden", "macro_micro"])
    both = pages.two_plane_run(tmp_path_factory.mktemp("ux1176-both"), pages.REVIEW_SHAPE)
    page = tmp_path_factory.mktemp("ux1176-both-page") / "report.html"
    import tools.bga_view as view

    view.export(str(both), str(page))
    uris["two_plane"] = page.as_uri()
    with Browser(find_chrome()) as browser:
        return {
            label: {
                "tree": browser.ax(uri, "(() => {" + _OPEN + "})()", 1440, 900),
                "typed": browser.measure(uri, _TYPE, 1440, 900),
                "tables": browser.measure(
                    uri,
                    "(() => {"
                    + pages.OPEN_EVERY_DOOR_JS
                    + """
                  return [...document.querySelectorAll('table')].filter((t) => t.checkVisibility()).length;
                })()""",
                    1440,
                    900,
                ),
            }
            for label, uri in uris.items()
        }


@needs_browser
class TestAStatusIsAnnounced:
    def test_every_badge_is_a_live_region_at_rest(self, heard):
        for label, out in heard.items():
            badges = [n for n in out["tree"] if n["role"] == "status" and "badge" in n["attrs"].get("class", "")]
            assert out["typed"]["hiddenBadges"] == 0, (label, out["typed"])
            assert out["typed"]["badges"] > 10, (label, out["typed"])
            assert len(badges) == out["typed"]["badges"], (label, len(badges), out["typed"]["badges"])

    def test_no_table_has_an_empty_name(self, heard):
        for label, out in heard.items():
            tables = [n for n in out["tree"] if n["role"] == "table"]
            assert len(tables) == out["tables"] > 10, (label, len(tables), out["tables"])
            assert [t["attrs"].get("data-table") for t in tables if not t["name"].strip()] == [], label

    def test_a_table_name_tells_it_from_its_neighbours(self, heard):
        names = [n["name"] for n in heard["two_plane"]["tree"] if n["role"] == "table"]
        assert "What does everything wait on? › Choke points" in names, names

    def test_no_match_is_said_in_a_mounted_region_the_box_names(self, heard):
        for label, out in heard.items():
            for box in ("jump", "ask"):
                typed = out["typed"][box]
                if typed is None and box == "ask" and label == "golden":
                    continue
                assert typed["mounted"], (label, box, typed)
                assert typed["role"] == "status", (label, box, typed)
                assert "zzzq" in typed["says"] and typed["says"].startswith("Nothing"), (label, box, typed)

    def test_the_drawing_values_are_clipped_to_one_pixel(self, heard):
        for label, out in heard.items():
            values = out["typed"]["values"]
            if values is None:
                continue
            assert values["clip"] == "inset(50%)", (label, values)
            assert values["width"] <= 1 and values["height"] <= 1, (label, values)
        assert heard["two_plane"]["typed"]["values"] is not None, heard["two_plane"]["typed"]
