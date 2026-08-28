"""UX-348: the two things this tool does that others do not, on the page.

Measured on the exported report - the shape a reader is most likely to
be handed - when this was filed:

```text
                        golden      macro_micro
perfetto-questions      216 px       216 px      4 details, 0 open
blast (the export's)    103 px       103 px      `bga blast <target> <run>`
rail entry                         "Blast offline"
```

The Perfetto section was one paragraph of instructions over thirteen
queries in four closed folds, and nothing on the page said what a query
*returns* - the one thing a reader cannot get from SQL they have not
run. The blast section was a placeholder command with angle brackets,
in a chapter titled "What if I change this?", under a rail entry
announcing the capability as unavailable - while two `next_steps`
entries on the first screen already printed a real
`bga blast core.bst <this run>` with a Copy button.

So: the query section leads with the handoff and one query worked
through, open, before any fold; and the export's blast section prints
the command the pipeline published for this run.
"""
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402
from pages import snapshot_copy    # noqa: E402

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
MACRO = REPO / "tests/fixtures/macro_micro/run"
chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: `UX-347`'s document bound, which is what "within the first N screens"
#: means here: the section a reader is told about must be inside the
#: page they land on, not past it.
DOCUMENT_SCREENS = 10.0

_LOOK = """
(() => {
  // The chapters fold (`UX-347`), so open them: this measures where a
  // section is in the document, not whether it is drawn right now.
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const vh = window.innerHeight;
  const at = (name) => document.querySelector(
    `main section[data-section="${name}"]`);
  const perfetto = at("perfetto-questions");
  const blast = at("blast");
  const worked = perfetto?.querySelector("[data-worked]") ?? null;
  const firstFold = perfetto?.querySelector("details") ?? null;
  const order = perfetto
    ? [...perfetto.querySelectorAll("[data-worked], details")]
        .map((n) => n.getAttribute("data-worked") ? "worked" : "fold")
    : [];
  return {
    document: document.documentElement.scrollHeight / vh,
    perfetto: perfetto === null ? null : {
      top: (perfetto.getBoundingClientRect().top + window.scrollY) / vh,
      px: Math.round(perfetto.getBoundingClientRect().height),
      order,
      folds: perfetto.querySelectorAll("details").length,
      openFolds: [...perfetto.querySelectorAll("details")]
        .filter((d) => d.open).length,
      workedQuery: worked?.querySelector("pre code")?.textContent ?? null,
      workedColumns: [...(worked?.querySelectorAll(
        '[data-role="answer-shape"] dt') ?? [])].map((n) => n.textContent),
      copies: worked?.querySelectorAll("button").length ?? 0,
      lead: (perfetto.querySelector("p")?.textContent ?? ""),
    },
    blast: blast === null ? null : {
      top: (blast.getBoundingClientRect().top + window.scrollY) / vh,
      heading: blast.querySelector("h2")?.textContent ?? "",
      command: blast.querySelector("code")?.textContent ?? "",
      copies: blast.querySelectorAll("button").length,
      text: blast.textContent ?? "",
    },
    rail: [...document.querySelectorAll("nav a")].map(
      (a) => (a.textContent || "").trim()),
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    import tools.bga_view as view

    made = {}
    for name, fixture in (("golden", GOLDEN), ("macro_micro", MACRO)):
        run = snapshot_copy(fixture, tmp_path_factory.mktemp(f"capability-{name}"))
        page = tmp_path_factory.mktemp(f"capability-page-{name}") / "report.html"
        view.export(str(run), str(page))
        # The run directory as well: the published command names the
        # run it was written for, and the page under test was exported
        # from this copy rather than from the fixture in the tree.
        made[name] = {"url": page.as_uri(), "run": run}
    return made


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", ["golden", "macro_micro"])
class TestTheTimelineIsPitchedBeforeItIsCatalogued:
    def test_a_worked_example_comes_before_any_fold(self, browser, pages, label):
        """The acceptance's first clause. A library of closed folds says
        nothing about what is behind them; one query in full says what
        the reader would get."""
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        section = out["perfetto"]
        assert section, f"{label}: the page draws no Perfetto section"
        assert section["order"][:1] == ["worked"], (
            f"{label}: the section opens with {section['order'][:2]} - the "
            f"worked example has to come before the library")
        assert section["workedQuery"], f"{label}: the example carries no SQL"
        assert section["copies"] >= 1, (
            f"{label}: the worked query cannot be copied")

    def test_the_example_says_what_comes_back(self, browser, pages, label):
        """What a reader cannot get from SQL they have not run. Declared
        columns, never a sample result - another run's numbers pasted
        into this page would be the lie every other guard here is
        about."""
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        columns = out["perfetto"]["workedColumns"]
        assert len(columns) >= 3, (
            f"{label}: the worked example declares {columns}")
        query = out["perfetto"]["workedQuery"]
        for column in columns:
            assert re.search(rf"\bas {re.escape(column)}\b", query), (
                f"{label}: `{column}` is not a column this query returns:"
                f"\n{query}")

    def test_the_library_stays_folded(self, browser, pages, label):
        """`UX-209`'s four category folds are the library, not the
        pitch: thirteen queries opened by default is the height this
        page spent `UX-347` recovering."""
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        assert out["perfetto"]["folds"] == 4, out["perfetto"]["folds"]
        assert out["perfetto"]["openFolds"] == 0, (
            f"{label}: {out['perfetto']['openFolds']} of the library's folds "
            f"open by default")

    def test_the_lead_says_how_to_open_the_timeline(self, browser, pages, label):
        """A section that catalogues queries for a trace and never says
        how to get the trace open is the fold this item was filed
        about, one level up."""
        lead = browser.measure(
            pages[label]["url"], _LOOK, 1440, 900)["perfetto"]["lead"]
        assert "one trace" in lead, lead
        # Both fixtures are snapshots without a build log, so the honest
        # lead names the absence rather than a button that is not there
        # (`UX-194`, `UX-329`). A run that has one is told where the
        # button is instead.
        assert "no build log" in lead or "Open timeline" in lead, lead

    def test_the_section_is_inside_the_document_a_reader_lands_on(
            self, browser, pages, label):
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        assert out["perfetto"]["top"] <= DOCUMENT_SCREENS, (
            f"{label}: the Perfetto section starts "
            f"{out['perfetto']['top']:.1f} screens down, against "
            f"{DOCUMENT_SCREENS}")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", ["golden", "macro_micro"])
class TestTheBlastSectionSpellsItsCommand:
    def test_the_command_names_this_run_and_no_placeholder(
            self, browser, pages, label):
        """The defect, exactly: `bga blast <target> <run>`. An export
        can spell the real command - two `next_steps` entries already
        do - and this section is the one named for the capability."""
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        blast = out["blast"]
        assert blast, f"{label}: the export drew no blast section"
        assert "<" not in blast["command"], (
            f"{label}: the command still carries a placeholder: "
            f"{blast['command']}")
        assert blast["command"].startswith("bga blast "), blast["command"]
        assert blast["copies"] >= 1, f"{label}: the command cannot be copied"

    def test_the_command_is_the_published_one(self, browser, pages, label):
        """Read, not composed. Which element to ask about is the
        pipeline's decision (`next_steps`), and a page that picked its
        own would be a second ranking."""
        from tools.bga_view import payloads

        steps = payloads(str(pages[label]["run"]))[
            "report.json"].get("next_steps") or []
        published = [" ".join(step["argv"]) for step in steps
                     if (step.get("argv") or [None, None])[1] == "blast"]
        assert published, f"{label}: the run publishes no blast step"
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        assert out["blast"]["command"] in published, (
            f"{label}: {out['blast']['command']!r} is not one of the "
            f"published steps {published}")

    def test_the_run_path_is_in_it(self, browser, pages, label):
        """`<run>` was the other half of the placeholder."""
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        assert str(pages[label]["run"]) in out["blast"]["command"], (
            f"{label}: the command does not name this run: "
            f"{out['blast']['command']}")

    def test_the_section_names_the_capability_not_its_absence(
            self, browser, pages, label):
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        assert out["blast"]["heading"].strip().endswith("Blast radius"), (
            out["blast"]["heading"])
        # `UX-282`'s rule: the served/exported difference is stated
        # inside the section, where a reader meets it.
        assert "server" in out["blast"]["text"], out["blast"]["text"][:200]

    def test_the_rail_names_the_capability_not_its_absence(
            self, browser, pages, label):
        """The navigation announced the capability as unavailable - and
        the key alone titles to "Blast", which names a verb rather than
        the question the section answers."""
        out = browser.measure(pages[label]["url"], _LOOK, 1440, 900)
        offline = [entry for entry in out["rail"] if "offline" in entry.lower()]
        assert offline == [], f"{label}: the rail still says {offline}"
        assert "Blast radius" in out["rail"], (
            f"{label}: the rail entries for this section are "
            f"{[e for e in out['rail'] if 'blast' in e.lower()]}")


class TestTheLeadQuotesAControlThatExists:
    """`UX-326`: the tool's own sentences are contracts. The lead tells a
    reader with a timeline to press a button by name, and a renamed
    button would make that sentence a dead pointer - the defect
    `UX-194` is about, one level of indirection away.

    Source-level, so it holds for the run shape neither fixture has:
    both committed fixtures are snapshots without a build log, so no
    browser measurement of this page can ever reach the branch that
    prints the label.
    """

    def test_the_quoted_button_label_is_the_one_the_page_draws(self):
        questions = (REPO / "bga/viewer/questions.js").read_text(
            encoding="utf-8")
        page = (REPO / "bga/viewer/index.html").read_text(encoding="utf-8")
        # The source spells the quotation marks as JS escapes, so
        # this reads what a reader will see, not the bytes.
        quoted = re.findall(r"\\u201c(.+?)\\u201d",
                            questions.replace("\n", " "))
        assert quoted, "the lead quotes no control at all"
        for label in quoted:
            assert f">{label}<" in page, (
                f"the lead sends the reader to {label!r}, which "
                f"index.html does not draw")
