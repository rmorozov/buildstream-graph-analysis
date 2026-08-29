"""UX-373: one page behind the handoff, not two.

The viewer shipped three pages, and two of them were the same errand
split in half:

```text
bga/viewer/index.html      3,096 B   "bga report"
bga/viewer/perfetto.html   2,326 B   "bga → Perfetto"      how to open it
bga/viewer/sql.html        2,010 B   "bga → PerfettoSQL"   what to ask it
```

A reader who presses the button needs both, in that order. The export
never had the split — `app.js` inlines the one `perfetto-questions`
section into the report, because `UX-199` found the export dropping the
link and leaving nothing behind it — so the one-page arrangement already
existed and only the served path was divided.

**What the merge could quietly break, and these hold.** `UX-204` made
the page render `questions.js` rather than carry a copy of every query,
after the copy drifted; a merge is exactly the operation that
reintroduces a copy. `UX-281` made every satellite page reach the report
it is about; a merge is exactly the operation that leaves a published
URL pointing at nothing. So `sql.html` stays, as a redirect that says
where its content went.

**And what the merge made visible.** Served on
`tests/fixtures/macro_micro`, the merged page offered "Open in Perfetto"
at the top and said "This snapshot carries no build log, so there is no
timeline to open here" three inches below. Both sentences were true of
the page and only one was true of the run. `index.html` has gated its
own button on `run.has_timeline` since `UX-194`; the standalone handoff
page never had, and nothing on it contradicted the button until the
questions moved in. `TestTheButtonIsNotDead` is that gate.
"""
import json
import pathlib
import sys
import threading
import urllib.request

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

VIEWER = REPO / "bga/viewer"

#: What the merged page is: the handoff, then the library, then the
#: substitution control - and, where the run has no timeline, no dead
#: button. Read after the fetches settle, which `Browser.measure` waits
#: for.
_LOOK = r"""
(() => {
  const line = document.getElementById("line");
  const picker = document.querySelector("[data-role=query-element]");
  const section = document.querySelector("#questions section[data-section]");
  const order = [...document.querySelectorAll("#status, #questions")]
    .map((n) => n.id);
  return {
    button: Boolean(document.getElementById("open")),
    absent: line ? line.getAttribute("data-handoff") : null,
    line: line ? (line.textContent || "").trim() : null,
    section: section ? section.getAttribute("data-section") : null,
    questions: document.querySelectorAll("#questions h4").length,
    categories: [...document.querySelectorAll("#questions details")]
      .map((d) => d.getAttribute("data-category")),
    options: [...document.querySelectorAll(
      "[data-role=query-element] option")].map((o) => o.value),
    chosen: picker ? picker.value : null,
    sql: [...document.querySelectorAll("#questions code")]
      .map((c) => c.textContent || ""),
    order,
    home: Boolean(document.querySelector("[data-home]")),
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def served():
    from tools.bga_view import serve

    made = []

    def start(run):
        httpd, url = serve(str(run))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        made.append(httpd)
        return url

    yield start
    for httpd in made:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(scope="module")
def looked(browser, served):
    """The merged page on both shapes of run: one with a timeline
    behind it and one without. Two runs, because the whole of
    `TestTheButtonIsNotDead` is a difference between them."""
    return {
        "no_timeline": browser.measure(
            served(pages.FIXTURES["macro_micro"]) + "perfetto.html",
            _LOOK, 1440, 900),
        "with_timeline": browser.measure(
            served(pages.WITH_TIMELINE) + "perfetto.html", _LOOK, 1440, 900),
    }


def _get(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.status, response.read().decode("utf-8")


class TestThereIsOnePage:
    def test_the_questions_are_on_the_handoff_page(self):
        """The merge itself, read off the shipped markup rather than a
        render: the page that opens the trace carries the slot the
        library lands in."""
        page = (VIEWER / "perfetto.html").read_text(encoding="utf-8")
        assert 'id="questions"' in page, (
            "perfetto.html has no slot for the query library")
        assert 'id="open"' in page, (
            "perfetto.html has stopped being the handoff page")

    def test_the_module_that_renders_them_is_the_shared_one(self):
        """`UX-204`'s single source, which a merge is exactly the
        operation that breaks."""
        script = (VIEWER / "perfetto_page.js").read_text(encoding="utf-8")
        assert 'from "./questions.js"' in script

    def test_nothing_writes_a_query_out_by_hand(self):
        """The drift `UX-204` closed, re-checked over every file this
        item touched - including the redirect, which is the one place a
        merge could leave a copy behind."""
        titles = json.loads(_node(
            'const { QUESTIONS } = await import("./bga/viewer/questions.js");'
            'console.log(JSON.stringify(QUESTIONS.map(q => q.title)));'))
        assert len(titles) >= 4, titles
        text = "".join(
            (VIEWER / name).read_text(encoding="utf-8")
            for name in ("perfetto.html", "perfetto_page.js", "sql.html"))
        spelled = [title for title in titles if title in text]
        assert spelled == [], (
            f"query title(s) written out instead of rendered: {spelled}")

    def test_the_page_that_moved_is_gone(self):
        """`sql.js` was fourteen lines that now live in
        `perfetto_page.js`. A second renderer of one list is the thing
        this item removes."""
        assert not (VIEWER / "sql.js").exists(), (
            "sql.js is back; the list has two renderers again")


class TestTheOldUrlStillGoesSomewhere:
    """`UX-281`: a satellite page is not a dead end. The URL is
    published — the store's older exports and anything pasted into an
    issue name it — so it stays a page that says where its content
    went."""

    def test_it_is_still_served(self, served):
        code, _body = _get(served(pages.FIXTURES["golden"]) + "sql.html")
        assert code == 200

    def test_it_names_where_the_content_went(self, served):
        _code, body = _get(served(pages.FIXTURES["golden"]) + "sql.html")
        assert 'url=perfetto.html' in body, (
            "sql.html no longer redirects; a published URL now dead-ends")
        assert 'href="perfetto.html"' in body, (
            "the redirect has no link a reader can follow when their "
            "browser has meta-refresh disabled - which is the whole "
            "reason the link is there as well")

    def test_it_redirects_without_script(self):
        """The server sends `default-src 'self'`, which refuses inline
        script - which is exactly how this page rendered nothing before
        `UX-266`. A script-driven redirect would be the same defect
        wearing a new hat."""
        page = (VIEWER / "sql.html").read_text(encoding="utf-8")
        assert 'http-equiv="refresh"' in page
        assert "<script" not in page, (
            "the redirect uses script, which this page's own CSP refuses")

    def test_the_report_points_at_the_merged_page(self):
        page = (VIEWER / "index.html").read_text(encoding="utf-8")
        assert '<a href="perfetto.html">Questions to ask it</a>' in page, (
            "the report still sends readers to the half of the errand")

    def test_the_export_still_strips_that_link(self):
        """The export inlines the section, so the link would be a
        network reach from a `file://` page. It matched by literal, and
        the literal changed."""
        source = (REPO / "tools/bga_view.py").read_text(encoding="utf-8")
        link = '<a href="perfetto.html">Questions to ask it</a>'
        assert link in source, (
            "the export's strip no longer matches the link index.html "
            "draws, so an exported report reaches the network for a page "
            "that is not in it")


@needs_browser
@pytest.mark.medium
class TestTheServedPageCarriesBoth:
    def test_the_handoff_comes_first(self, looked):
        out = looked["with_timeline"]
        assert out["order"] == ["status", "questions"], (
            f"the reader needs how-to-open before what-to-ask: {out['order']}")

    def test_the_library_renders(self, looked):
        out = looked["with_timeline"]
        assert out["section"] == "perfetto-questions", out["section"]
        assert out["questions"] >= 4, out["questions"]
        assert len(out["categories"]) >= 3, out["categories"]

    def test_the_way_home_survived(self, looked):
        """`UX-281`, on the merged page."""
        assert looked["with_timeline"]["home"] is True

    def test_the_substitution_control_is_here(self, looked):
        """The Required Fix's third element, and the one `sql.html`
        could never have: that page had no run behind it, so `UX-369`'s
        picker had no population and the queries showed the bare token.
        This page is served beside `report.json`."""
        out = looked["with_timeline"]
        assert len(out["options"]) > 1, (
            f"the merged page offers {len(out['options'])} element(s); it is "
            f"served beside report.json and should offer the run's own")
        assert out["chosen"] in out["options"], out

    def test_the_queries_name_the_chosen_element(self, looked):
        """Not just that the control exists: the SQL under it asks
        about what it says."""
        out = looked["with_timeline"]
        asking = [sql for sql in out["sql"] if out["chosen"] in sql]
        assert asking, (
            f"the picker says {out['chosen']!r} and no query asks about it")
        assert not [sql for sql in out["sql"] if "{element}" in sql], (
            "a query still shows the token on a page that has a population "
            "to substitute")


@needs_browser
@pytest.mark.medium
class TestTheButtonIsNotDead:
    """`UX-194`, applied to the page that is *about* the button.

    Measured on the two runs: `with_timeline` has a trace behind it and
    `macro_micro` has none. Before this, both got the button."""

    def test_a_run_with_a_timeline_gets_the_button(self, looked):
        out = looked["with_timeline"]
        assert out["button"] is True
        assert out["absent"] is None, out

    def test_a_run_without_one_does_not(self, looked):
        out = looked["no_timeline"]
        assert out["button"] is False, (
            "the page offers a handoff for a snapshot that has nothing to "
            "hand over - and says so itself, one section below")
        assert out["absent"] == "absent", out

    def test_the_absence_is_said_and_not_just_shown(self, looked):
        """`UX-321`: a control that is not there is a fact to publish,
        not a gap to infer. The page still says something in the place
        the button was."""
        line = looked["no_timeline"]["line"]
        assert line and "no timeline" in line.lower(), line
        assert "bga capture" in line, (
            f"the absence names no way out of it: {line!r}")

    def test_the_questions_are_still_there_without_a_timeline(self, looked):
        """The half that must not be gated. The queries are what to ask
        a trace once there is one, and a reader deciding whether to
        capture one is exactly who wants to read them."""
        assert looked["no_timeline"]["questions"] >= 4, (
            "the library went with the button; it is not the button's")


def _node(script):
    import os
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True,
                            cwd=os.getcwd(), timeout=60)
    assert result.returncode == 0, result.stderr
    return result.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
