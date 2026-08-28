"""UX-356: "drawn elsewhere" is a promise about fields.

`UX-338` gave the page `DRAWN_ELSEWHERE`: a population it deliberately
does not draw on its own, with a sentence saying where it went instead.
`element_join` - `correlate/v2`, the Plane 1 x Plane 2 join, and the
recipe author's whole answer - said:

> merged into the one element table (`elements`)

Round 55 measured that merge field by field, against the **rendered
DOM**. The merge named four columns. The join publishes twenty-eight
fields, and thirteen reached no rendered node:

```text
MISS  recommendations[].id                     23 values
MISS  recommendations[].text                   23 values
MISS  dominant_binary.binary / cpu_share / cpu_us / wall_us
MISS  serial_binary.cpu_us / wall_us
MISS  worst_redundancy.signature / example_cmd
      / total_duration_us / max_element_duration_us
MISS  cpu_coverage, saving_share, native_findings[]
```

The worst of them was `recommendations[].text` - the sentence the
analyzer writes, per element, for exactly this reader:

```text
holds 44% of the critical path and fixing it is worth 12.1s (26.1% of
the build), but runs at only 0.90 cores busy - it is waiting, not
computing, and its native build asked for -j1: remove `notparallel` /
raise its job count before touching its sources
```

`severity` was drawn for all twenty-three. `text` for none. Located in
the DOM, the sentence appeared exactly once, inside
`script#bga-report` - the payload the export inlines so the page can
boot from `file://`. A `grep` over `report.html` finds it and concludes
it reached the reader; it did not, which is why every clause here
reads the DOM and `_rendered_text` says so.

Three rules (styleguide §1b):

- **"Drawn elsewhere" means every field arrives elsewhere.** A merge
  that keeps four of twenty-eight is a *projection*, and a projection
  names what it dropped, in the sentence, where the next reviewer
  reads it.
- **A published sentence outranks a published number.** A severity chip
  beside a withheld sentence is that ordering inverted.
- **The embedded payload is not a reader.**
"""
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The one fixture that publishes a join. `golden` has four elements and
#: no Plane 2, so it publishes no `element_join` at all - which is the
#: honest 0-of-0 and the reason `test_the_population_is_the_join` exists
#: beside every clause here.
LABEL = "macro_micro"

_LOOK = """
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  for (const fold of document.querySelectorAll("details")) fold.open = true;
  const main = document.querySelector("main") || document.body;
  return {
    // Everything a *reader* can reach: rendered text plus the raw
    // values behind formatted ones. Not `document.body`, which would
    // include `script#bga-report` and make every field pass.
    text: main.textContent || "",
    raws: [...main.querySelectorAll("[data-raw]")]
      .map((n) => n.getAttribute("data-raw")),
    advice: [...main.querySelectorAll("p.advice")].map((p) => ({
      severity: p.getAttribute("data-severity"),
      text: (p.textContent || "").trim(),
      path: p.getAttribute("data-path"),
    })),
    folds: [...main.querySelectorAll("details.join-evidence")].map((f) => ({
      levels: f.getAttribute("data-levels"),
      rows: f.getAttribute("data-rows"),
      summary: (f.querySelector("summary")?.textContent || "").trim(),
      cells: f.querySelectorAll("dd").length,
    })),
    inScriptOnly: (() => {
      const needle = "is waiting, not computing";
      return !(main.textContent || "").includes(needle)
        && (document.body.textContent || "").includes(needle);
    })(),
  };
})()
"""


def _leaves(node, prefix=""):
    """`(field_path, value)` for every leaf, arrays collapsed to `[]`."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _leaves(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value, f"{prefix}[]")
    else:
        yield prefix, node


def _payload():
    from tools.bga_view import payloads

    return payloads(str(pages.FIXTURES[LABEL]))["report.json"]


def _drawn_elsewhere():
    """`app.js`'s declaration, read out of the module that holds it."""
    source = (REPO / "bga/viewer/app.js").read_text(encoding="utf-8")
    found = re.search(r"export const DRAWN_ELSEWHERE = \{(.*?)\n\};",
                      source, re.S)
    assert found, "app.js no longer declares DRAWN_ELSEWHERE"
    return found.group(1)


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    return pages.export_uri(pages.FIXTURES[LABEL],
                            tmp_path_factory.mktemp("merge"))


class TestThePopulationIsTheJoin:
    """The instrument. Every clause below is about `element_join`; if
    the fixture stopped publishing one, they would all pass over an
    empty list."""

    def test_the_fixture_publishes_a_join(self):
        joined = _payload().get("element_join") or []
        assert len(joined) >= 10, len(joined)

    def test_it_publishes_the_sentences_this_is_about(self):
        written = [advice for entry in _payload()["element_join"]
                   for advice in (entry.get("recommendations") or [])
                   if advice.get("text")]
        assert len(written) >= 20, len(written)

    def test_the_join_is_declared_drawn_elsewhere(self):
        assert "element_join" in _drawn_elsewhere()


@needs_browser
@pytest.mark.medium
class TestEveryPublishedFieldReachesAReader:
    def test_no_field_is_withheld_without_being_named(self, browser, page):
        """The rule. A field either reaches a rendered node, or the
        redirect sentence names it - and this is asserted against the
        payload's own field set, so a field added to `correlate/v3`
        joins the check with no edit here.
        """
        out = browser.measure(page, _LOOK, 1440, 900)
        reachable = set(out["raws"])
        text = out["text"]
        declared = _drawn_elsewhere()

        withheld = {}
        for entry in _payload()["element_join"]:
            for field, value in _leaves(entry):
                if value is None or isinstance(value, bool):
                    continue
                spelled = str(value)
                if len(spelled) < 2:
                    continue
                if spelled in reachable or spelled in text:
                    continue
                withheld.setdefault(field, 0)
                withheld[field] += 1

        unnamed = {field: count for field, count in withheld.items()
                   if field.split(".")[-1].rstrip("[]") not in declared}
        assert unnamed == {}, (
            "field(s) of a `DRAWN_ELSEWHERE` population that reach no "
            "rendered node and are not named in its redirect sentence: "
            + json.dumps(unnamed, indent=2))

    def test_the_sentence_names_what_it_drops(self):
        """The other direction: a redirect sentence that named every
        field would satisfy the clause above and say nothing. What it
        names has to be *withheld*, not merely mentioned."""
        declared = _drawn_elsewhere()
        assert "recommendations[].id" in declared, declared
        # And it says why, rather than listing a name and stopping.
        assert "slug" in declared, declared


@needs_browser
@pytest.mark.medium
class TestThePublishedSentenceIsPrinted:
    def test_every_recommendation_is_on_the_page(self, browser, page):
        """§1b's second clause, on the field it was filed for."""
        out = browser.measure(page, _LOOK, 1440, 900)
        written = [advice["text"] for entry in _payload()["element_join"]
                   for advice in (entry.get("recommendations") or [])
                   if advice.get("text")]
        missing = [text for text in written if text not in out["text"]]
        assert missing == [], (
            f"{len(missing)} of {len(written)} recommendation sentences "
            f"reach no rendered node: {missing[:2]}")

    def test_the_severity_travels_with_the_sentence(self, browser, page):
        """The inversion this item was filed on was `severity` rendered
        and `text` withheld. Both, or the chip is decoration."""
        out = browser.measure(page, _LOOK, 1440, 900)
        assert len(out["advice"]) >= 20, len(out["advice"])
        for advice in out["advice"]:
            assert advice["severity"], advice
            assert advice["path"].startswith("element_join["), advice
            assert len(advice["text"]) > len(advice["severity"]) + 10, advice

    def test_the_sentence_is_not_only_in_the_embedded_payload(
            self, browser, page):
        """The instrument clause, named. This whole file would pass on
        a page that rendered nothing if it read `document.body`, because
        `script#bga-report` carries every value the payload has."""
        out = browser.measure(page, _LOOK, 1440, 900)
        assert out["inScriptOnly"] is False, (
            "the recommendation reaches `document.body` and not `main` - "
            "it is in the embedded payload and nowhere a reader looks")


@needs_browser
@pytest.mark.medium
class TestTheEvidenceFoldAnnouncesItsDepth:
    """The Plane 2 evidence is folded, and §3a.1 applies to it like
    every other value fold - which is the rule `UX-359` found this page
    breaking one fold at a time."""

    def test_each_fold_counts_what_is_behind_it(self, browser, page):
        out = browser.measure(page, _LOOK, 1440, 900)
        assert out["folds"], "no join-evidence fold on the page"
        for fold in out["folds"]:
            assert fold["levels"] == "1", fold
            assert int(fold["rows"]) == fold["cells"], fold
            assert f"{fold['rows']} row" in fold["summary"], fold

    def test_the_evidence_is_the_plane_two_half(self, browser, page):
        """Named, because a fold that counted correctly and held the
        wrong thing would pass the clause above."""
        out = browser.measure(page, _LOOK, 1440, 900)
        text = out["text"]
        for entry in _payload()["element_join"]:
            binary = (entry.get("dominant_binary") or {}).get("binary")
            if binary:
                assert binary in text, binary


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
