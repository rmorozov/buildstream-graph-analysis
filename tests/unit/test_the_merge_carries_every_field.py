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

import pages
from browser import NO_BROWSER, Browser, find_chrome

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
# `UX-450` split the section walk out of `app.js` when that file sat
# exactly on `UX-337`'s ceiling. What this reads - the section
# router and its declarations - moved to `sections.js`; the name
# here follows the code rather than the file it used to be in.
    source = (REPO / "bga/viewer/sections.js").read_text(encoding="utf-8")
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


#: `UX-829`: how a `data-joined` **signal** name surfaces once
#: `elementSignalTable` flattens it into row fields - a scalar signal
#: keeps its own name, a record contributes its members (an array
#: member is excluded, `structured.js`'s own rule, which is why
#: `fan_in.direct` needs no entry here at all). Mirrored rather than
#: imported, the way `CAPPED_TABLE_JS` mirrors `dev_page_census.py`.
_FLATTENS_TO = {
    "element_durations": {"element_durations"},
    "slack": {"slack"},
    "downstream_count": {"downstream_count"},
    "unweighted_depth": {"unweighted_depth"},
    "blast_radius": {"weighted_duration_us", "risk_score", "is_foundation"},
    "fan_in": {"direct_count", "transitive_count", "immediate_dominator",
               "is_foundation"},
    "criticality_probability": {"probability", "slack_us"},
}

_ELEMENTS_COVERAGE_JS = r"""
(() => {
  const box = document.querySelector('[data-section="elements"] .map-table');
  const joined = box ? (box.getAttribute('data-joined') || '')
    .split(',').filter(Boolean) : [];
  const select = document.querySelector('select[data-table="elements"]');
  const columns = new Set();
  const collect = () => {
    document.querySelectorAll('[data-section="elements"] th[data-column]')
      .forEach((th) => columns.add(th.getAttribute('data-column')));
  };
  collect();
  for (const option of select ? [...select.options] : []) {
    select.value = option.value;
    select.dispatchEvent(new Event('change'));
    collect();
  }
  return { joined, columns: [...columns],
          lead: box?.querySelector('p.muted')?.textContent || '' };
})()
"""

_CLICK_INSPECT_JS = r"""
(() => {
  for (const link of document.querySelectorAll('a.inspect')) link.click();
  return [...document.querySelectorAll('[data-list="direct"]')].map((n) => ({
    element: n.closest('section')?.getAttribute('data-element'),
    text: n.textContent,
  }));
})()
"""


@pytest.fixture(scope="module")
def scale_page(tmp_path_factory):
    """`UX-829`'s own population: the scale run, where the table's
    width budget (§3d) actually bites - the two committed fixtures are
    small enough that every column would fit in "All elements"."""
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("elements-joined-scale")
    run = pages.scale_run(into)
    page = into / "scale.html"
    view.export(str(run), str(page))
    return page.as_uri()


@needs_browser
@pytest.mark.medium
class TestEveryJoinedFieldOnTheElementsTableDrawsAColumn:
    """UX-829 (styleguide §1b, §3a): a different `data-joined` from
    `element_join` above - the element-keyed *signals* `UX-268` merged
    into the `elements` table's own rows, against `presetTable`'s
    views rather than against one rendered table."""

    def test_every_signal_reaches_a_column_or_the_lead_names_it(
            self, browser, scale_page):
        out = browser.measure(scale_page, _ELEMENTS_COVERAGE_JS, 1440, 900)
        assert out["joined"], "no data-joined signals on the scale export"
        columns = set(out["columns"])
        uncovered = [signal for signal in out["joined"]
                     if not (_FLATTENS_TO.get(signal, {signal}) & columns)
                     and signal not in out["lead"]]
        assert uncovered == [], (
            f"joined field(s) with no column in any preset and not named "
            f"in the lead sentence: {uncovered} (columns seen: "
            f"{sorted(columns)})")


@needs_browser
@pytest.mark.medium
class TestTheElementCardListsDirectFanIn:
    """UX-829: `fan_in[uid].direct` - drawn on the element card because
    a table cell does not survive forty names (§3c)."""

    def test_an_element_with_direct_dependencies_lists_them(
            self, browser, scale_page):
        out = browser.measure(scale_page, _CLICK_INSPECT_JS, 1440, 900)
        assert out, "no element card named its direct dependencies"
        for entry in out:
            assert entry["text"].startswith("Depends on: "), entry


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
