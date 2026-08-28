"""UX-350: §2 is one of the visual contract's longest sections, and it was unbuilt.

§2 adopts the sparkline for ordered series and the density strip for
distributions, sets the geometry, requires `n` beside every strip, and
requires a strip **beside every table whose primary column is a
quantity** — "the reader sees the shape of 1,202 rows before scrolling
any of them". Measured on a real boot when this was filed:

```text
                sparklines   density strips   svg elements   page height
golden                   1                0              1     11,286 px
macro_micro              1                0              3     18,148 px
```

Three drawings in twenty screens, and the element table — the report's
central table, and the one §2 names — with no strip above it.

Two things kept it that way, and neither was the renderer: `columnStrip`
and `strip` were both written and both correct.

- **The row cap.** `distributionStrip` returned `null` below
  `TABLE_OPENS_BOUNDED_ABOVE`, forty, on the argument that a table a
  reader can see whole is apparatus for nothing. Both fixtures' element
  tables are under it — eleven rows and four — so the report's central
  table never drew one. The cap decides whether a table is *paged*;
  whether its shape is worth showing is a different question.
- **The namespaces.** The two published distributions sat under
  `signals`, so `app.js`'s "a section whose whole value is a
  distribution" branch never saw them. `UX-344` lifted them and they
  began to draw, which is why the census below differs from the one in
  the filing.

And one defect in what *was* drawn: coincident marks printed on top of
each other, `19.1 s (p95)` over `19.1 s max`, because on an eleven-
element population the 95th percentile is the largest value.
"""
import json
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}
chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_LOOK = """
(() => {
  // `UX-347`'s chapters fold; a claim about the document is a claim
  // about all of it.
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const strips = [...document.querySelectorAll('[data-role="density"]')];
  const axes = [...document.querySelectorAll('[data-role="draw-axis"]')].map(
    (axis) => {
      const ticks = [...axis.querySelectorAll(".draw-tick")].map((tick) => {
        const box = tick.getBoundingClientRect();
        return { mark: tick.getAttribute("data-mark"),
                 text: (tick.textContent || "").trim(),
                 left: box.left, right: box.right };
      });
      let overlaps = 0;
      for (let i = 0; i < ticks.length; i += 1) {
        for (let j = i + 1; j < ticks.length; j += 1) {
          if (ticks[i].left < ticks[j].right && ticks[j].left < ticks[i].right) {
            overlaps += 1;
          }
        }
      }
      return { ticks, overlaps,
               section: axis.closest("[data-section]")
                 ?.getAttribute("data-section") ?? null };
    });
  return {
    sparklines: document.querySelectorAll('[data-role="sparkline"]').length,
    axes,
    strips: strips.map((strip) => ({
      section: strip.closest("[data-section]")?.getAttribute("data-section")
        ?? null,
      self: strip.className.includes("density-self"),
      drawn: strip.getAttribute("data-drawn"),
      n: strip.getAttribute("data-n"),
      sentence: (strip.querySelector('[data-role="density-sentence"]')
        ?.textContent || "").trim(),
    })),
    tables: [...document.querySelectorAll("table[data-table]")].length,
  };
})()
"""


def _published_distributions(label):
    """Every `bga:distribution` in the payload, by path.

    Read off the schema and the payload together, which is what the
    acceptance means by "asserted against the payload rather than a
    list": a distribution added to a contract tomorrow joins this set
    without anybody editing this file.
    """
    from bga import schemas
    from tools.bga_view import payloads

    document = payloads(str(FIXTURES[label]))["report.json"]

    def walk(node, path=""):
        if not isinstance(node, dict):
            return
        if node.get(schemas.DISTRIBUTION):
            yield path
        for key, sub in (node.get("properties") or {}).items():
            yield from walk(sub, f"{path}.{key}" if path else key)

    declared = list(walk(schemas.schema(document["schema"])))
    return [path for path in declared
            if document.get(path.split(".")[0]) and "." not in path]


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    import tools.bga_view as view

    made = {}
    for name, fixture in FIXTURES.items():
        run = tmp_path_factory.mktemp(f"shape-{name}") / "run"
        shutil.copytree(fixture, run)
        (run / "expected_output.json").unlink(missing_ok=True)
        page = tmp_path_factory.mktemp(f"shape-page-{name}") / "report.html"
        view.export(str(run), str(page))
        made[name] = page.as_uri()
    return made


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestEveryPublishedDistributionIsDrawn:
    def test_each_one_renders_its_strip(self, browser, pages, label):
        """The acceptance's first clause. `golden` publishes none - it
        has four elements and is under the sample floor - so this is
        0 of 0 there, which is the honest answer and the reason the
        clause below exists beside it."""
        expected = _published_distributions(label)
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        drawn = {strip["section"] for strip in out["strips"]
                 if not strip["self"]}
        assert set(expected) <= drawn, (
            f"{label}: published but not drawn: "
            f"{sorted(set(expected) - drawn)}")

    def test_no_strip_is_drawn_for_a_distribution_nobody_published(
            self, browser, pages, label):
        """The other direction. A page that drew a strip per section
        whatever the payload said would satisfy the clause above
        perfectly."""
        expected = set(_published_distributions(label))
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        published = {strip["section"] for strip in out["strips"]
                     if not strip["self"]}
        assert published <= expected, (
            f"{label}: drawn as a published distribution and not in the "
            f"payload: {sorted(published - expected)}")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestTheTablesWearTheirShape:
    def test_the_element_table_carries_one(self, browser, pages, label):
        """§2's own requirement, and the one the row cap withheld from
        the table it was written about."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        beside = [strip for strip in out["strips"]
                  if strip["self"] and strip["section"] == "elements"]
        assert beside, (
            f"{label}: the element table has no strip; the page draws "
            f"{[s['section'] for s in out['strips']]}")

    def test_the_page_draws_more_than_a_handful(self, browser, pages, label):
        """The census, as a bound. One drawing in twenty screens was
        the finding; a page that quietly lost the channel again should
        redden here rather than in a reader's eye."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        assert out["sparklines"] >= 1, out["sparklines"]
        assert len(out["strips"]) >= 5, (
            f"{label}: {len(out['strips'])} strips over "
            f"{out['tables']} tables")

    def test_a_strip_below_the_sample_floor_states_it(
            self, browser, pages, label):
        """`UX-226`'s rule reaches every strip. A table too short to
        have a shape gets the sentence, not a range bar over two
        values - and both fixtures have such a table, so this is
        measured rather than argued."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        stated = [strip for strip in out["strips"]
                  if strip["drawn"] == "false"]
        assert stated, f"{label}: no strip is under the floor on this page"
        for strip in stated:
            assert "too few to have a shape" in strip["sentence"], strip


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestNoTwoLabelsSitOnTopOfEachOther:
    def test_no_axis_overlaps(self, browser, pages, label):
        """The acceptance's second clause, measured from the rendered
        geometry with `UX-257`'s instrument rather than by eye."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        assert out["axes"], f"{label}: no exhibit axis on the page"
        bad = [axis for axis in out["axes"] if axis["overlaps"]]
        assert bad == [], (
            f"{label}: {len(bad)} axis/axes with overlapping labels: "
            + json.dumps([{ "section": a["section"],
                            "ticks": [t["text"] for t in a["ticks"]]}
                          for a in bad]))

    def test_a_merged_label_names_the_marks_it_stands_for(
            self, browser, pages, label):
        """Not silence. Two marks at one value are one fact about the
        population, and *which* two is the interesting part - so the
        merged label says. Without this a fix that simply dropped the
        second label would pass the overlap clause."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        merged = [tick for axis in out["axes"] for tick in axis["ticks"]
                  if " " in (tick["mark"] or "")]
        assert merged, (
            f"{label}: no axis has coincident marks - both fixtures have "
            f"one (p95 == max, or peak at level 1), so the walk has broken")
        for tick in merged:
            # All but the first: the leading mark is carried by the
            # label itself - `level 1` *is* the first level, and
            # `level 1 (first, peak 2)` would be saying it twice.
            for name in tick["mark"].split()[1:]:
                assert name in tick["text"], (tick, name)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
