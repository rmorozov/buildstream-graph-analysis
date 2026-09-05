"""UX-368: the finding in front of you carries the query that shows it.

The tool's distinguishing claim is that it hands a build to Perfetto
with both planes on one clock. The report states findings. Round 58
measured the join between them and found none:

```text
macro_micro: 11 findings
finding keys: copy_text, detail, elements, evidence, id, indent,
              severity, title
findings carrying trace_query: 0 / 11
```

**The mapping was not missing. It was one join away, and the joiner
read a key that no longer existed.** `UX-229` moved the finding ->
query table into `bga/provenance.py` and published it as
`provenance[].trace_query`; `trace_context.js` read
`finding.provenance.trace_query`, which was true then because the
record was written *into* each finding. `UX-344` moved the records out
into one list - correctly, that was its whole point - and this line was
not moved with them.

Measured on `tests/fixtures/with_timeline`, the one committed capture
whose handoff button actually works:

```text
findings whose id is in TRACE_QUERIES:  6
Investigate boxes drawn on the page:    0
```

Four rounds of a dead control on every report, with
`test_buttons_that_know_why.py` green throughout - because every clause
in it built its own finding object carrying the nested shape inline. A
guard that constructs its input cannot notice that the producer stopped
producing it. That gap is `TestTheShapeIsThePayloadsShape`, in that
file; this file is the other half, on the page.

**Why the query is on the finding rather than joined at read time.**
The finding is what `--format json` prints and what the CI comment
reads. A field a consumer has to resolve through a second list is a
field the consumer stops resolving, which is the defect above stated
as a rule.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_LOOK = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  const boxes = [...document.querySelectorAll(".investigate")];
  return {
    count: boxes.length,
    queries: boxes.map((n) => n.getAttribute("data-query-id")),
    elements: boxes.map((n) => n.getAttribute("data-element") || null),
    sql: boxes.map((n) => (n.querySelector("code") || {}).textContent || ""),
    // `UX-194`'s precondition. **Not `#perfetto`**: that button is in
    // `index.html` on every page, and only `wireTheHandoff` un-hides
    // the `#actions` paragraph around it. A probe on the button reads
    // true everywhere and would have made the two no-timeline
    // fixtures look like the defect.
    handoff: Boolean(document.getElementById("actions"))
             && !document.getElementById("actions").hidden,
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def timeline_page(tmp_path_factory):
    """`with_timeline` - the capture whose handoff works.

    The two in `pages.FIXTURES` have no build log, so `UX-194`'s
    dead-control rule correctly draws no button on either and a guard
    that measured only those would read zero and call it right. That is
    how the first pass at this measurement nearly went.
    """
    return pages.export_uri(pages.WITH_TIMELINE,
                            tmp_path_factory.mktemp("u368-wt"))


def _published(fixture):
    from tools.bga_view import payloads

    return payloads(str(fixture))["report.json"]["findings"]


class TestTheMappingReachesTheFinding:
    def test_a_finding_the_table_answers_carries_its_query(self):
        from bga.provenance import TRACE_QUERIES

        found = _published(pages.WITH_TIMELINE)
        answered = [f for f in found if f["id"] in TRACE_QUERIES]
        assert answered, "the fixture publishes no finding the table maps"
        for finding in answered:
            # `UX-448`: the table's value is a tuple of grains, and
            # `trace_query` is its first - what the button opens.
            declared = TRACE_QUERIES[finding["id"]]
            assert finding.get("trace_query") == declared[0], (
                f"{finding['id']} carries {finding.get('trace_query')!r} and "
                f"the table says {declared!r}")
            assert finding.get("trace_queries") == (
                list(declared) if len(declared) > 1 else None), (
                f"{finding['id']} carries "
                f"{finding.get('trace_queries')!r} for its other grains "
                f"and the table says {declared!r}")

    def test_a_finding_nothing_answers_says_so_rather_than_guessing(self):
        """`UX-321`: null is published, not omitted, and no query is
        invented for a claim the library has no question for."""
        from bga.provenance import TRACE_QUERIES

        found = _published(pages.WITH_TIMELINE)
        unmapped = [f for f in found if f["id"] not in TRACE_QUERIES]
        assert unmapped, "every finding is mapped; this clause proves nothing"
        for finding in unmapped:
            assert "trace_query" in finding, finding["id"]
            assert finding["trace_query"] is None, (
                f"{finding['id']} is not in the table and carries "
                f"{finding['trace_query']!r} - a guessed query is worse "
                f"than none")


@needs_browser
@pytest.mark.medium
class TestTheButtonIsDrawnWhereTheFindingIs:
    def test_the_findings_that_earn_a_button_get_one(self, browser,
                                                     timeline_page):
        """The defect, as a page. Zero before this item, over a capture
        whose handoff button works."""
        from bga.provenance import TRACE_QUERIES

        earned = [f["id"] for f in _published(pages.WITH_TIMELINE)
                  if f["id"] in TRACE_QUERIES]
        out = browser.measure(timeline_page, _LOOK, 1440, 900)
        assert out["handoff"], (
            "this fixture's handoff button is missing, so a count of "
            "zero investigate boxes would be the dead-control rule "
            "rather than this defect")
        assert out["count"] >= len(earned), (
            f"{out['count']} Investigate boxes for {len(earned)} findings "
            f"the table answers: {earned}")

    def test_the_queries_differ_between_findings(self, browser,
                                                 timeline_page):
        """The other direction, so the fix cannot be a decoration. One
        query pasted onto every finding passes a "has a query" clause
        and helps nobody."""
        out = browser.measure(timeline_page, _LOOK, 1440, 900)
        assert len(set(out["queries"])) > 1, out["queries"]
        assert len(set(out["sql"])) > 1, (
            "every Investigate box carries the same SQL")

    def test_an_element_scoped_query_names_this_run_s_element(
            self, browser, timeline_page):
        """`UX-369`'s substitution, reached from a finding. A query
        that takes an element gets the finding's own first element;
        one that does not is left alone rather than given a name its
        SQL never uses."""
        import json
        import subprocess

        out = browser.measure(timeline_page, _LOOK, 1440, 900)
        takes = json.loads(subprocess.run(
            [__import__("shutil").which("node"), "--input-type=module", "-e",
             'const q = await import("./bga/viewer/questions.js");'
             "console.log(JSON.stringify(q.QUESTIONS.filter(q.takesElement)"
             "  .map((x) => x.id)));"],
            capture_output=True, text=True, cwd=str(REPO),
            timeout=60).stdout)
        scoped = [(q, e, s) for q, e, s in
                  zip(out["queries"], out["elements"], out["sql"])
                  if q in takes]
        assert scoped, f"no element-scoped query is reachable: {out['queries']}"
        for query, element, sql in scoped:
            assert element, f"{query} takes an element and was given none"
            assert f"'{element}'" in sql, (query, element)
        for query, element, sql in zip(out["queries"], out["elements"],
                                       out["sql"]):
            assert "= ''" not in sql, (
                f"{query} renders an empty substitution - a query that "
                f"runs and returns nothing")
            if query not in takes:
                assert not element, (
                    f"{query} does not ask about an element and was given "
                    f"{element!r}")

    @pytest.mark.parametrize("label", sorted(pages.FIXTURES))
    def test_no_timeline_still_means_no_button(self, browser,
                                               tmp_path_factory, label):
        """`UX-194`'s dead-control rule, unbroken by this item: the
        query exists on the finding either way, and the button does not
        appear where there is nothing to open."""
        uri = pages.export_uri(pages.FIXTURES[label],
                               tmp_path_factory.mktemp(f"u368-{label}"))
        out = browser.measure(uri, _LOOK, 1440, 900)
        assert not out["handoff"], f"{label} unexpectedly has a timeline"
        assert out["count"] == 0, out["queries"]
        assert any(f.get("trace_query")
                   for f in _published(pages.FIXTURES[label])), (
            "the finding should still carry its query - the button is "
            "what is conditional, not the mapping")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
