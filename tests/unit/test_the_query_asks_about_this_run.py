"""UX-369: the query library substitutes *this* run's element.

Three of the thirteen canned queries ask about one element, and each
carried the same literal:

```javascript
{ id: "element-commands", example: "core.bst", ... }
{ id: "dependency-wait",  example: "core.bst", ... }
{ id: "waited-on-flow",   example: "core.bst", ... }
```

`core.bst` is a real element - **of `tests/fixtures/macro_micro`**. It
is one fixture's element name compiled into a library shipped to every
project, so a reader on any other build pasted a query into Perfetto,
got zero rows, and had nothing on the page telling them which token to
change. Measured on the seeded 1,202-element synthetic run before this
item: `core.bst` appears 3 times on a page whose elements are all
called `layer08/mod099.bst`.

**What the filing named as the falsifying capture was wrong, and this
file uses a different one.** `UX-369` proposed `with_timeline`; that
capture *has* an element called `core.bst` (40 occurrences on its
page), so it cannot tell the substitution from the coincidence.
`golden` can - `base/extra/lib/app.bst`, no `core` - and it is already
committed and already cheap. It is the fixture the page-level clauses
below run on, with the synthetic run kept for the one claim only scale
can make.

**The population is the run's, not the report's.** The first draft read
`elementFacts`, which is built from the published top-N arrays, and
gave a picker with 26 entries beside a sentence reading "26 in this
run" - `UX-366`'s defect committed again one control over.
`TestThePopulationIsTheRunsOwn` is that clause, and it is why
`elementUids` unions the duration map in.
"""
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The name that must not survive. One fixture's element, and the whole
#: reason this item exists.
FOREIGN = "core.bst"

_LOOK = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  const pick = document.querySelector('[data-role="query-element"]');
  const code = (id) => [...document.querySelectorAll("code[data-sql-for]")]
    .find((n) => n.getAttribute("data-sql-for") === id);
  const button = (id) => [...document.querySelectorAll("button[data-sql-for]")]
    .find((n) => n.getAttribute("data-sql-for") === id);
  const shown = code("dependency-wait");
  const copies = button("dependency-wait");
  const options = pick ? [...pick.options].map((o) => o.value) : [];
  const started = { sql: shown.textContent, copy: copies.getAttribute("data-copy") };
  // The control's own value, not the first option: on `golden` the
  // default is `base.bst`, which sorts second. A probe that assumed
  // `options[0]` read `null` here and reported the page's fault.
  const chosen = pick ? pick.value : null;
  // The option furthest from the default, so "it happened to already
  // be that one" cannot pass this.
  const target = options[options.length - 1] === chosen
    ? options[0] : options[options.length - 1];
  if (pick) { pick.value = target; pick.dispatchEvent(new Event("change")); }
  // What the reader actually gets. Reading `data-copy` is not enough:
  // `copyButton` closes over the text it was built with, and a button
  // still handing that over would leave the attribute correct and the
  // clipboard stale - which is the failure the item calls worse than
  // no builder at all. So the clipboard is stubbed and the control is
  // pressed, over `file://`, where the real one is unavailable anyway.
  let pasted = null;
  try {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: (t) => { pasted = t; return true; } },
    });
  } catch (error) { pasted = "could not stub the clipboard: " + error; }
  copies.click();
  return {
    pasted,
    chosen,
    chosenIsInTheSql: started.sql.includes("'" + chosen + "'"),
    options,
    note: (document.querySelector('[data-control="query-element"] p')
           ?.textContent ?? ""),
    startedMatched: started.sql === started.copy,
    target,
    afterSql: shown.textContent,
    afterCopy: copies.getAttribute("data-copy"),
    body: document.body.textContent,
  };
})()
"""


def _node(script):
    import json

    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=str(REPO),
                            timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def golden_page(tmp_path_factory):
    """`golden`, whose elements are `base/extra/lib/app.bst`."""
    return pages.export_uri(pages.FIXTURES["golden"],
                            tmp_path_factory.mktemp("q369-golden"))


@needs_node
class TestNoFixtureNameIsCompiledIn:
    def test_no_entry_carries_a_hard_coded_example(self):
        """The defect at its source. Read from the module rather than
        grepped out of the file, so a `example` reintroduced by any
        spelling is caught."""
        out = _node(
            'const q = await import("./bga/viewer/questions.js");'
            "console.log(JSON.stringify(q.QUESTIONS.map("
            "  (x) => [x.id, x.example ?? null]).filter((p) => p[1])));")
        assert out == [], f"entries still ship an element name: {out}"

    def test_an_unfilled_query_shows_the_token(self):
        """Not the empty string it used to collapse to. A visible
        `{element}` says there is a value to choose; `= ''` says the
        query is finished and returns nothing, which is this item's
        failure happening more quietly."""
        out = _node(
            'const q = await import("./bga/viewer/questions.js");'
            "const asks = q.QUESTIONS.filter(q.takesElement);"
            "console.log(JSON.stringify({ n: asks.length,"
            "  rendered: asks.map((x) => q.renderedSql(x)),"
            "  token: q.ELEMENT_TOKEN }));")
        # Four since `UX-448` added `executables-in-element`; three
        # before it. A count rather than a floor, so a query that stops
        # taking an element is a red rather than a silence - which is
        # what this clause is for.
        assert out["n"] == 4, out["n"]
        for sql in out["rendered"]:
            assert out["token"] in sql, sql
            assert FOREIGN not in sql, sql
            assert "= ''" not in sql, f"an empty substitution: {sql}"

    def test_a_filled_query_names_the_element_it_was_given(self):
        out = _node(
            'const q = await import("./bga/viewer/questions.js");'
            "console.log(JSON.stringify(q.QUESTIONS.filter(q.takesElement)"
            '  .map((x) => q.renderedSql(x, "zz/odd-name.bst"))));')
        for sql in out:
            assert "'zz/odd-name.bst'" in sql, sql
            assert "{element}" not in sql, sql


@needs_node
class TestThePopulationIsTheRunsOwn:
    """The clause the first draft failed.

    `elementFacts` knows the elements the *report* chose to talk about;
    a picker whose purpose is reaching an element the report did not
    rank needs the run's whole list. Asserted against a payload where
    the two differ by construction, because on an 11-element fixture
    they do not differ at all and the guard would pass either way.
    """

    def test_it_reaches_an_element_no_published_array_names(self):
        out = _node(
            'const e = await import("./bga/viewer/element.js");'
            "const durations = {};"
            "for (let i = 0; i < 100; i += 1) "
            '  durations["mod" + String(i).padStart(3, "0") + ".bst"] = 1000;'
            "console.log(JSON.stringify(e.elementUids({"
            "  elements: { element_durations: durations },"
            '  headline: { top_actions: ['
            '    { element_uid: "mod007.bst", saving_us: 1 }] } })));')
        assert len(out) == 100, (
            f"the picker's population is {len(out)} of 100 - it is reading "
            f"what the report ranked, not what the run built")
        assert out == sorted(out), "not sorted"

    def test_an_element_only_a_finding_names_is_still_reachable(self):
        """The other direction of the union: the duration map leads,
        but it does not get to be the only source."""
        out = _node(
            'const e = await import("./bga/viewer/element.js");'
            "console.log(JSON.stringify(e.elementUids({"
            '  elements: { element_durations: { "a.bst": 1 } },'
            '  headline: { top_actions: ['
            '    { element_uid: "only-here.bst", saving_us: 1 }] } })));')
        assert "only-here.bst" in out, out


@needs_browser
@pytest.mark.medium
class TestThePageSubstitutesThisRun:
    def test_no_query_on_the_page_names_another_projects_element(
            self, browser, golden_page):
        """The defect, as a page. `golden` has no element called
        `core.bst`; before this item its page said `core.bst` three
        times, once per element-scoped query."""
        out = browser.measure(golden_page, _LOOK, 1440, 900)
        assert FOREIGN not in out["body"], (
            "a foreign fixture's element name is still on the page")

    def test_the_default_is_an_element_this_run_has(self, browser,
                                                    golden_page):
        out = browser.measure(golden_page, _LOOK, 1440, 900)
        assert out["options"], "no element picker on a page with a run"
        # `headline.top_actions[0]` on `golden`. Read from the payload
        # rather than written here, so this stays a claim about where
        # the default comes from rather than about one fixture's data.
        from tools.bga_view import payloads

        report = payloads(str(pages.FIXTURES["golden"]))["report.json"]
        expected = report["headline"]["top_actions"][0]["element_uid"]
        assert out["chosen"] == expected, out
        assert expected in out["options"], out["options"]
        assert out["chosenIsInTheSql"], (
            "the control says one element and the SQL below it says "
            "another")

    def test_changing_it_moves_the_query_and_the_paste_together(
            self, browser, golden_page):
        """A builder that updates the display and copies the old text
        is worse than none - which is what the closure in `copyButton`
        would have done had the payload stayed the text it was built
        with."""
        out = browser.measure(golden_page, _LOOK, 1440, 900)
        assert out["startedMatched"], "display and payload differed at rest"
        assert out["target"] != out["chosen"], (
            "the fixture's population is too small to move the picker")
        assert f"'{out['target']}'" in out["afterSql"], out["afterSql"]
        assert f"'{out['target']}'" in out["afterCopy"], out["afterCopy"]
        assert out["afterSql"] == out["afterCopy"], (
            "the query shown and the query copied are no longer the same "
            "query")
        assert f"'{out['chosen']}'" not in out["afterCopy"], (
            "the paste still carries the element the reader moved off")

    def test_pressing_copy_hands_over_the_query_now_on_screen(
            self, browser, golden_page):
        """The attribute is not the deliverable - the clipboard is.
        `copyButton` closes over the text it was built with, so a
        button reading the closure would leave `data-copy` correct and
        hand the reader the query they moved off."""
        out = browser.measure(golden_page, _LOOK, 1440, 900)
        assert out["pasted"], f"nothing reached the clipboard: {out['pasted']}"
        assert out["pasted"] == out["afterCopy"], out["pasted"]
        assert f"'{out['target']}'" in out["pasted"], out["pasted"]
        assert f"'{out['chosen']}'" not in out["pasted"], (
            "the clipboard carries the element the reader moved off")


@needs_browser
@pytest.mark.medium
class TestItReachesEveryElementAtScale:
    """The one claim only the scale probe can make.

    Eleven elements cannot tell "the run's population" from "the eight
    rows the attribution table shows"; 1,202 can.
    """

    def test_the_picker_offers_the_whole_run(self, browser,
                                             tmp_path_factory):
        from tools.bga_view import payloads

        made = tmp_path_factory.mktemp("q369-scale")
        run = pages.scale_run(made)
        uri = pages.export_uri(run, made, name="scale.html")
        report = payloads(str(run))["report.json"]
        population = len(report["elements"]["element_durations"])
        out = browser.measure(uri, _LOOK, 1440, 900)
        assert population > 1000, population       # the probe, still a probe
        assert len(out["options"]) == population, (
            f"{len(out['options'])} of {population} elements are reachable "
            f"from the query picker")
        assert str(population) in out["note"], (
            f"the sentence beside the control does not say the count it "
            f"offers: {out['note']!r}")
        assert FOREIGN not in out["body"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
