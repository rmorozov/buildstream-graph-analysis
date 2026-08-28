"""UX-358: a capability the page advertises is exercised by a fixture.

`UX-348` moved the Perfetto handoff up the page, gave it a lead
sentence and a worked example. Round 55 went to press the button, on
the page an export produces, and could not:

```text
                     #perfetto in the DOM   rendered (box height > 0)
golden                                  1                         no
macro_micro                             1                         no
```

`wireTheHandoff` returns before it wires anything, because `export`
had no trace to inline. `trace_bytes` calls `bga timeline`, which
renders from the wrapped BuildStream log, and the refusal says why:

```text
FileNotFoundError: tests/fixtures/macro_micro: no build.log. This is a
snapshot directory - it has a `run/` - but `bga timeline` needs the
wrapped BuildStream log the build wrote, and this capture kept none.
```

None of `tests/fixtures/`'s three captures holds one. So the one
capability no other BuildStream tool offers was the only user-visible
path in a 4,500-test suite with no end-to-end exercise: every guard,
screenshot and review for four rounds had seen the **absence** path,
which is correct, well worded, and the wrong half of a pair.

**The fixture already existed.** `examples/06-macro-micro-optimization`
carries a real capture - `build.log`, `plane2.log.gz`, `plane2.json`
and its run - and four guards already read its *trace*. None exported a
page from it. The filing said no committed fixture could render a
timeline; what was true is that no fixture **used to build a page**
could, which is a smaller claim and the one this file fixes.

The rule the pair states, in `TestBothStatesAreReachable`: a capability
the page advertises is exercised by at least one committed fixture. A
capability with no fixture is not tested and not testable, and four
rounds of reasoning about this one from its source is what that cost.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_LOOK = """
(() => {
  const box = (el) => el ? Math.round(el.getBoundingClientRect().height) : null;
  const button = document.getElementById("perfetto");
  const actions = document.getElementById("actions");
  const main = document.querySelector("main") || document.body;
  const text = main.textContent || "";
  return {
    inDom: Boolean(button),
    height: box(button),
    label: (button?.textContent || "").trim(),
    actionsHidden: actions ? Boolean(actions.hidden) : null,
    // `UX-299` inlines the trace as its own script so the export can
    // hand it over from `file://`. Present exactly when there is one.
    traceScript: Boolean(document.getElementById("bga-trace")),
    absence: absenceOn(text),
  };
  function absenceOn(text) {
    for (const [name, needle] of [
        ["NOT_CAPTURED", "Plane 2 was not captured for this run"],
        ["CAPTURED_NO_RAW_LOG", "the raw trace log it was built from was not"],
        ["DECLINED", "asked not to read it"]]) {
      if (text.includes(needle)) return name;
    }
    return "none";
  }
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    """The three captures, exported. `WITH_TIMELINE` is the one that
    renders a timeline; the other two are the absence path."""
    made = pages.pages(tmp_path_factory, "handoff")
    made["with_timeline"] = pages.export_uri(
        pages.WITH_TIMELINE, tmp_path_factory.mktemp("handoff-timeline"))
    return made


class TestTheFixtureCanRenderATimeline:
    """Before the page: the command the page depends on."""

    def test_the_capture_has_the_log_the_renderer_reads(self):
        wrapped = pages.WITH_TIMELINE.parent / "build.log"
        assert wrapped.is_file(), (
            f"{wrapped} is gone; `bga timeline` renders from the wrapped "
            f"BuildStream log and there is no other committed capture "
            f"that has one")

    def test_the_timeline_renders(self):
        import tools.bga_view as view

        rendered = view.trace_bytes(str(pages.WITH_TIMELINE))
        assert rendered is not None, (
            "`bga timeline` refuses on the one fixture that is supposed "
            "to render; the handoff is unexercisable again")
        assert len(rendered) > 1000, len(rendered)

    def test_the_committed_page_fixtures_still_cannot(self):
        """The other side, and the reason a third capture was needed
        rather than a change to the two. If `tests/fixtures/` gains a
        `build.log` later this reddens, and the pair below should then
        be re-pointed rather than left asserting an absence that has
        moved."""
        import tools.bga_view as view

        able = [label for label, fixture in pages.FIXTURES.items()
                if view.trace_bytes(str(fixture)) is not None]
        assert able == [], (
            f"{able} can render a timeline now; this file's absence half "
            f"is measuring the wrong fixtures")


@needs_browser
@pytest.mark.medium
class TestTheHandoffRendersWhereThereIsATrace:
    def test_the_button_has_a_box(self, browser, booted):
        """The clause four rounds of review could not check."""
        out = browser.measure(booted["with_timeline"], _LOOK, 1440, 900)
        assert out["inDom"], out
        assert out["height"], (
            f"`#perfetto` is in the DOM and renders no box: {out}")
        assert out["actionsHidden"] is False, out
        assert out["traceScript"], out

    def test_the_page_says_which_plane_is_missing(self, browser, booted):
        """The fixture found a defect the moment it existed, and this
        clause records it rather than asserting it away.

        This capture has Plane 1 and no Plane 2, so the page renders
        `NOT_CAPTURED` - *"Plane 2 was not captured for this run, so
        there is no per-process detail and no timeline"* - **while
        carrying a Plane 1 timeline and a working Perfetto button.**
        Whether there is a timeline is not Plane 2's fact alone, and
        `UX-329` split that grammar one level too high.

        Filed as `UX-362`. Asserted here as what is true today, so the
        contradiction is visible in the suite rather than only in a
        reader's eye - and so the clause reddens when `UX-362` fixes
        it, which is where the wording change should be argued.
        """
        out = browser.measure(booted["with_timeline"], _LOOK, 1440, 900)
        assert out["height"], "the button does not render on this capture"
        assert out["absence"] == "NOT_CAPTURED", (
            "the Plane 2 absence sentence has changed on a capture that "
            "has Plane 1 and no Plane 2 - if `UX-362` landed, this clause "
            "is what it should have moved")

    def test_the_label_says_what_the_press_does(self, browser, booted):
        out = browser.measure(booted["with_timeline"], _LOOK, 1440, 900)
        assert "Perfetto" in out["label"], out


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheAbsenceRendersWhereThereIsNone:
    """The other half, in the same file on purpose. A change that made
    the button render unconditionally would pass every clause above; it
    reddens here."""

    def test_the_button_does_not_render(self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        assert out["inDom"], "the button left the document entirely"
        assert not out["height"], (
            f"{label}: `#perfetto` renders a box on a run with no "
            f"timeline: {out}")
        assert out["actionsHidden"] is True, out
        assert not out["traceScript"], out

    def test_the_absence_is_stated_and_says_which_one(
            self, browser, booted, label):
        """`UX-329`'s split, held: `golden` never captured Plane 2 and
        `macro_micro` captured it and kept no raw log, and those are a
        broken machine and a fine measurement."""
        expected = {"golden": "NOT_CAPTURED",
                    "macro_micro": "CAPTURED_NO_RAW_LOG"}[label]
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        assert out["absence"] == expected, out


@needs_browser
@pytest.mark.medium
class TestBothStatesAreReachable:
    """The rule this item generalises to, asserted as a population
    rather than as two examples: the page advertises a capability, and
    every state that capability has is reachable from a committed
    fixture. A guard that only ever saw one state is what four rounds
    of this looked like.
    """

    def test_the_two_states_differ_where_it_matters(self, browser, booted):
        with_trace = browser.measure(booted["with_timeline"], _LOOK, 1440, 900)
        without = browser.measure(booted["macro_micro"], _LOOK, 1440, 900)
        assert with_trace != without, (
            "the page renders identically with and without a timeline; "
            "the probe cannot see the capability it is guarding")
        for field in ("height", "actionsHidden", "traceScript", "absence"):
            assert with_trace[field] != without[field], (field, with_trace,
                                                         without)

    def test_every_state_has_a_fixture(self):
        """Stated as the count rather than by name, so the clause is
        about coverage rather than about these three captures."""
        import tools.bga_view as view

        captures = dict(pages.FIXTURES, with_timeline=pages.WITH_TIMELINE)
        states = {label: view.trace_bytes(str(path)) is not None
                  for label, path in captures.items()}
        assert set(states.values()) == {True, False}, (
            f"the committed captures reach only one of the handoff's two "
            f"states: {states}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
