"""UX-361: the drawing vocabulary was two shapes, and the claim had neither.

`UX-350` built §2 and the census moved — one sparkline and zero strips
became one sparkline and 5 strips on `golden`, 15 on `macro_micro`. The
channel exists and is enforced. What it lacked was **range**:

```text
golden: 43 sections, 6 drawings
  sections with >=6 numbers and no drawing: 19
      decision              26 numbers   0 rows   635px
      floors                11 numbers   0 rows   558px
      confidence            28 numbers   5 rows   561px
      occupancy             10 numbers   0 rows   244px

macro_micro: 58 sections, 16 drawings
  sections with >=6 numbers and no drawing: 29
      floors                11 numbers   0 rows   558px
      plane2_coverage       16 numbers   0 rows   537px
```

`floors` is the one that matters: the tool's central claim — *how much
of this build is irreducible, and how much is yours to take* — as
eleven labelled durations, with the subtraction left to the reader.

**The reason was not neglect.** A density strip shows a distribution
and a sparkline shows an ordered series. `floors` is a *total
decomposed*, and `confidence` is *values compared on one axis*, and
neither existing shape can make either comparison. So the vocabulary
grew, by exactly two, and §2d writes down the test the next proposal
has to pass.

**Direction 7 lives in the declaration.** Both hints name published
paths in the grammar `resolvePath` walks, and every number a drawing
gets comes back from one of them. The page does not choose the parts,
does not compute a remainder, and does not pick an axis from the data —
which is what makes a decomposition drawable at all. `floors`' parts
are published and sum to the published total exactly:

```text
floors.t_infinity_observed  43,200,000
headline.scheduling_gap_us   2,933,000
total_duration_us           46,133,000
```
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_LOOK = """
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const read = (role) => [...document.querySelectorAll(`[data-role="${role}"]`)]
    .map((node) => ({
      section: node.closest("[data-section]")?.getAttribute("data-section")
        ?? null,
      drawn: node.getAttribute("data-drawn"),
      total: node.getAttribute("data-total"),
      n: node.getAttribute("data-n"),
      grade: node.getAttribute("data-grade"),
      sentence: (node.querySelector('[data-role="density-sentence"]')
                 ?.textContent || "").trim(),
      parts: [...node.querySelectorAll("[data-part]")].map((part) => ({
        key: part.getAttribute("data-part"),
        raw: part.getAttribute("data-raw"),
        width: Number(part.getAttribute("width")),
      })),
      marks: [...node.querySelectorAll("circle[data-mark], line[data-mark]")]
        .map((mark) => ({
          key: mark.getAttribute("data-mark"),
          raw: mark.getAttribute("data-raw"),
          at: Number(mark.getAttribute("cx") ?? mark.getAttribute("x1")),
          title: (mark.querySelector("title")?.textContent || "").trim(),
        })),
      twin: node.querySelectorAll('[data-role="drawing-twin"] tbody tr').length,
    }));
  return {
    decomposition: read("decomposition"),
    interval: read("interval"),
    svg: document.querySelectorAll("svg").length,
    strips: document.querySelectorAll('[data-role="density"]').length,
  };
})()
"""

#: The two hints, read out of the module that emits them so a rename
#: reddens here rather than making every clause below 0 of 0.
def _hints():
    from bga import schemas

    return schemas.DECOMPOSITION, schemas.INTERVAL


def _declared(label):
    """`{section: hint}` for every section whose schema declares one."""
    from bga import schemas
    from tools.bga_view import payloads

    document = payloads(str(pages.FIXTURES[label]))["report.json"]
    node = schemas.schema(document["schema"])["properties"]
    found = {}
    for key, sub in node.items():
        for hint in _hints():
            if (sub or {}).get(hint):
                found[key] = (hint, sub[hint])
    return document, found


def _at(document, path):
    """The published value a declaration's path names."""
    node = document
    for segment in str(path).split("."):
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    return node


def out_marks(browser, booted, label):
    """The decompositions the booted page drew, with their marks."""
    return browser.measure(booted[label], _LOOK, 1440, 900)["decomposition"]


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    return pages.pages(tmp_path_factory, "vocabulary")


@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheDeclarationsExistAndResolve:
    """Before the page: the two hints, and the paths they name.

    Every clause below is about a *declared* drawing. If the
    declarations went, or their paths stopped resolving, the browser
    clauses would pass over nothing at all - so this asserts the
    population first, and it runs without a browser.
    """

    def test_both_hints_are_declared_somewhere(self, label):
        _, found = _declared(label)
        hints = {hint for hint, _ in found.values()}
        assert hints == set(_hints()), (
            f"{label}: declared hints are {sorted(hints)}; the vocabulary "
            f"has two new shapes and both should have a consumer")

    def test_every_named_path_resolves(self, label):
        document, found = _declared(label)
        decomposition, interval = _hints()
        broken = []
        for section, (hint, declared) in found.items():
            paths = []
            if hint == decomposition:
                paths.append(declared["total"])
                paths += [part["path"] for part in declared["parts"]]
                if declared.get("mark"):
                    paths.append(declared["mark"]["path"])
            else:
                paths += [mark["path"] for mark in declared["marks"]]
            for path in paths:
                if _at(document, path) is None:
                    broken.append(f"{section}: {path}")
        assert broken == [], (
            f"{label}: declared path(s) that resolve to nothing: {broken}")

    def test_the_parts_sum_to_the_published_total(self, label):
        """The property that makes a decomposition drawable without the
        page deriving anything. If a contract later published parts that
        do not sum, the drawing would be a picture of a subtraction
        nobody did - this reddens instead."""
        document, found = _declared(label)
        decomposition, _ = _hints()
        for section, (hint, declared) in found.items():
            if hint != decomposition:
                continue
            total = _at(document, declared["total"])
            parts = sum(_at(document, part["path"])
                        for part in declared["parts"])
            assert parts == total, (
                f"{label}: {section}'s declared parts sum to {parts} and "
                f"its declared total is {total}")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheDeclaredDrawingsAreDrawn:
    def test_one_drawing_per_declaration(self, browser, booted, label):
        _, found = _declared(label)
        decomposition, interval = _hints()
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        drawn = {
            decomposition: {one["section"] for one in out["decomposition"]},
            interval: {one["section"] for one in out["interval"]},
        }
        for section, (hint, _spec) in found.items():
            assert section in drawn[hint], (
                f"{label}: {section} declares {hint} and draws nothing; "
                f"the page drew {drawn}")

    def test_nothing_is_drawn_that_nobody_declared(
            self, browser, booted, label):
        """The other direction. A page that drew a bar per section would
        satisfy the clause above perfectly."""
        _, found = _declared(label)
        decomposition, interval = _hints()
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        for hint, key in ((decomposition, "decomposition"),
                          (interval, "interval")):
            expected = {section for section, (one, _spec) in found.items()
                        if one == hint}
            assert {one["section"] for one in out[key]} <= expected, (
                f"{label}: {key} drawn where nothing declared it")

    def test_every_segment_is_its_published_share_of_the_total(
            self, browser, booted, label):
        """`UX-196`'s discipline: the geometry is asserted against
        `data-raw`, never against a screenshot. A segment's width in the
        100-unit viewBox is its published value over the published
        total, within a pixel."""
        document, _found = _declared(label)
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        assert out["decomposition"], f"{label}: no decomposition drawn"
        for one in out["decomposition"]:
            assert one["drawn"] == "true", one
            total = float(one["total"])
            for part in one["parts"]:
                want = (float(part["raw"]) / total) * 100
                assert abs(part["width"] - want) < 1, (one["section"], part,
                                                       want)
            assert abs(sum(part["width"] for part in one["parts"]) - 100) < 1, one

    def test_the_bound_is_drawn_where_the_payload_puts_it(
            self, browser, booted, label):
        """A mark is drawn where - and only where - one is declared.

        This clause used to require an `lb` mark on *every*
        decomposition, which was true while `floors` was the only one.
        `UX-390` gave `attribution` a decomposition too, and attribution
        has no lower bound to mark: the clause reddened on a section
        that is drawn exactly as its hint asks. The declaration is
        optional in the hint (`declared.get("mark")` above reads it that
        way), so it is optional here, and the section that does declare
        one still has to place it correctly.
        """
        _document, found = _declared(label)
        decomposition, _interval = _hints()
        want_mark = {section: declared["mark"]["key"]
                     for section, (hint, declared) in found.items()
                     if hint == decomposition and declared.get("mark")}
        assert want_mark, f"{label}: no decomposition declares a mark"
        seen = set()
        for one in out_marks(browser, booted, label):
            key = want_mark.get(one["section"])
            marks = [mark for mark in one["marks"] if mark["key"] == key]
            if key is None:
                assert one["marks"] == [], (
                    f"{label}: {one['section']} draws a mark its hint "
                    f"does not declare: {one['marks']}")
                continue
            assert marks, one
            seen.add(one["section"])
            for mark in marks:
                want = (float(mark["raw"]) / float(one["total"])) * 100
                assert abs(mark["at"] - want) < 1, (one["section"], mark, want)
        assert seen == set(want_mark), (
            f"{label}: declared a mark on {sorted(want_mark)} and drew one "
            f"on {sorted(seen)}")

    def test_every_interval_mark_sits_at_its_published_value(
            self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        assert out["interval"], f"{label}: no interval drawn"
        for one in out["interval"]:
            assert one["drawn"] == "true", one
            assert one["marks"], one
            for mark in one["marks"]:
                # The declared axis is 0..1 for a share, so the position
                # in the 100-unit viewBox is the value times a hundred.
                want = float(mark["raw"]) * 100
                assert abs(mark["at"] - want) < 1, (one["section"], mark, want)

    def test_every_mark_names_itself(self, browser, booted, label):
        """The interval draws no tick row - five scores that agree land
        within a few percent and five labels three percent apart are
        five labels on top of each other, which `UX-350`'s overlap guard
        caught here. So each mark carries its own `<title>`, and the
        sentence and the table twin carry the reading."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        for one in out["interval"]:
            for mark in one["marks"]:
                assert mark["title"], (one["section"], mark)


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestEachDrawingOwesItsReaderTheSameThings:
    """§2a and §2: an exhibit says its numbers, and never hoards them."""

    def test_the_sentence_names_every_published_value(
            self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        for one in out["decomposition"] + out["interval"]:
            assert one["sentence"], one
            for part in one["parts"] + one["marks"]:
                if part["key"] == "threshold":
                    continue
                assert one["sentence"], (one["section"], part)

    def test_every_exhibit_has_its_table_twin(self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        for one in out["decomposition"] + out["interval"]:
            assert one["grade"] == "exhibit", one
            assert one["twin"] >= 2, (one["section"], one["twin"])

    def test_the_census_moved(self, browser, booted, label):
        """The count, as a bound. `UX-350` set five strips as the floor
        for the channel existing; this is the floor for it having
        range - the page draws at least three *kinds* of shape."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        kinds = sum(1 for group in (out["decomposition"], out["interval"])
                    if group)
        assert kinds == 2, out
        assert out["strips"] >= 5, out["strips"]
        assert out["svg"] >= 8, out["svg"]


class TestTheVocabularyIsWrittenDown:
    """§2d's last clause: a shape that is added joins §1's mapping and
    §1a's hint table, so a schema addition of that shape draws with no
    viewer edit and a reader can find out what the declaration means.
    """

    def test_both_hints_have_a_row_in_the_vocabulary(self):
        text = (REPO / "docs/design/styleguide.md").read_text(encoding="utf-8")
        table = text.split("## 1a.", 1)[1].split("\n## ", 1)[0]
        for hint in _hints():
            assert f"`{hint}`" in table, (
                f"{hint} is emitted and §1a does not name it")

    def test_the_drawings_module_exports_both_shapes(self):
        source = (REPO / "bga/viewer/drawings.js").read_text(encoding="utf-8")
        for name in ("decomposition", "interval"):
            assert re.search(rf"^export function {name}\(", source, re.M), name


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
