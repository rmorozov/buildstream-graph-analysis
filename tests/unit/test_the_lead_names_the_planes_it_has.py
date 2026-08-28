"""UX-364: the handoff's lead names the planes the trace actually has.

`UX-348` gave the Perfetto section a lead sentence. It opened:

> **Both planes of this run land in one trace: Plane 1's element spans
> and Plane 2's process lanes**, on one clock, joined by the element uid
> this report prints.

Unconditionally. `UX-362`'s sweep booted `tests/fixtures/with_timeline`
- Plane 1, no Plane 2 - and found the sentence promising process lanes
that are not in that trace, three sections from the absence sentence
saying the plane was never captured. The same defect as `UX-362` with
the sign reversed: a sentence claiming a plane it does not own.

**Why it was not one string.** The honest predicate is neither of the
two the page already had:

* `has_timeline` is true for a Plane 1 trace and a two-plane trace
  alike - `with_timeline` has one and has no Plane 2.
* `plane2_absence` answers a different question and reads a different
  file. It is about whether Plane 2 is in this **analysis** - it looks
  for the report beside the run - while the lead is about whether Plane
  2 is in this **trace**, which the renderer decides from the raw log.
  The two-plane snapshot below has them disagreeing outright: the
  absence sentence says the plane was never captured, and the trace
  carries it. `TestTheAbsenceSentenceIsNotThePredicate` holds that, and
  the source-level reason it can happen at all.

  The filing named `DECLINED` as the discriminating case. It is one, and
  it is not the one demonstrated here: constructing it needs a Plane 2
  *report* beside the run, which is a 46 KB analysis product this guard
  would have to fake. The disagreement below needs nothing faked and
  refutes the same predicate, so it is what the file argues from.

So the renderer publishes what it already knew and threw away:
`render` returns `planes` - `["1"]` or `["1", "2"]` - and
`run.trace_planes` carries it to the page.
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

#: The clause a reader acts on: what they will find when they press the
#: button. Both halves are quoted from the rendered sentence rather than
#: from the source, so a reworded lead has to keep meaning them.
_PROMISES_PLANE2 = "Plane 2's process lanes"
_DENIES_PLANE2 = "Plane 2 is not in it"
_LANDS_IN_A_TRACE = "land in this run's trace"

_LOOK = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  const lead = document.querySelector(
    '[data-section="perfetto-questions"] p.muted');
  return {
    exists: Boolean(lead),
    planes: lead ? lead.getAttribute("data-planes") : null,
    text: lead ? (lead.textContent || "").replace(/\s+/g, " ").trim() : "",
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    """Every trace state the page can be in, as pages.

    Three, and the third is the one that did not exist until this item:
    no trace, a Plane 1 trace, and a trace with both planes.
    """
    made = pages.pages(tmp_path_factory, "planes")
    made["with_timeline"] = pages.export_uri(
        pages.WITH_TIMELINE, tmp_path_factory.mktemp("planes-p1"))
    both = pages.two_plane_snapshot(tmp_path_factory.mktemp("planes-src"))
    made["two_plane"] = pages.export_uri(
        both, tmp_path_factory.mktemp("planes-p12"))
    return made


class TestTheRendererPublishesWhatItRendered:
    """Before the page: the fact it needs has to exist and be right."""

    def test_a_two_plane_snapshot_renders_two_planes(self, tmp_path):
        from tools import bga_view

        run = pages.two_plane_snapshot(tmp_path)
        trace, planes = bga_view.trace_with_planes(str(run))
        assert trace, "the constructed two-plane snapshot renders nothing"
        assert planes == ["1", "2"], planes

    def test_a_plane_one_capture_renders_one(self):
        from tools import bga_view

        trace, planes = bga_view.trace_with_planes(str(pages.WITH_TIMELINE))
        assert trace, "the committed Plane 1 capture renders nothing"
        assert planes == ["1"], planes

    def test_a_capture_with_no_timeline_reports_no_planes(self):
        """`None`, not `[]`: there is no trace to describe, which is a
        different answer from a trace with nothing in it."""
        from tools import bga_view

        for label, fixture in pages.FIXTURES.items():
            trace, planes = bga_view.trace_with_planes(str(fixture))
            assert (trace, planes) == (None, None), (label, planes)


class TestTheAbsenceSentenceIsNotThePredicate:
    """The discriminating case, and the reason this is not a one-liner.

    `plane2_absence` answers "is Plane 2 in this **analysis**"; the lead
    sentence asks "is Plane 2 in this **trace**". They read different
    files - `absence` looks for the Plane 2 report beside the run, the
    renderer reads the raw log - so a fix keyed on the absence sentence
    is keyed on the wrong fact, and the two-plane snapshot shows them
    disagreeing outright.
    """

    def test_the_two_disagree_on_the_same_run(self, tmp_path):
        from bga import plane2
        from tools import bga_view

        run = pages.two_plane_snapshot(tmp_path)
        said = plane2.absence(str(run))
        _, planes = bga_view.trace_with_planes(str(run))
        assert planes == ["1", "2"], planes
        assert said == plane2.NOT_CAPTURED, said
        # Both are right about their own question, which is the point:
        # a lead sentence driven by `said` would tell this page's reader
        # that Plane 2 was never captured, over a trace that has it.

    def test_the_renderer_never_reads_the_plane_two_report(self):
        """Why they can disagree, from the source rather than from one
        fixture: the render path does not consult the report at all, so
        no amount of agreeing on other captures makes one predicate
        stand in for the other."""
        import inspect

        from tools import bga_timeline, bga_view

        source = (inspect.getsource(bga_view.trace_render)
                  + inspect.getsource(bga_timeline.render))
        assert "PLANE2_NAME" not in source and "plane2.json" not in source, (
            "the render path now reads the Plane 2 report; if that is "
            "deliberate, this file's whole argument needs restating")
        assert "RAW_LOG_NAME" in source or "raw" in source, (
            "the render path no longer mentions the raw log it branches "
            "on - which is the fact `trace_planes` is derived from")

    def test_absence_reads_the_report_and_not_the_raw_log_alone(
            self, tmp_path):
        """The other half of the same claim, at the boundary: dropping
        the raw log from a snapshot with no report changes nothing about
        the absence sentence, because it was never reading it."""
        from bga import plane2

        run = pages.two_plane_snapshot(tmp_path)
        before = plane2.absence(str(run))
        (run.parent / "plane2.log.gz").unlink()
        assert plane2.absence(str(run)) == before, (
            "the absence sentence moved when only the raw log did")


@needs_browser
@pytest.mark.medium
class TestTheLeadNamesWhatTheReaderWillFind:
    def test_two_planes_are_promised_only_where_there_are_two(
            self, browser, booted):
        out = browser.measure(booted["two_plane"], _LOOK, 1440, 900)
        assert out["exists"], "no lead sentence on the two-plane page"
        assert out["planes"] == "1+2", out
        assert _PROMISES_PLANE2 in out["text"], out["text"]
        assert _DENIES_PLANE2 not in out["text"], out["text"]

    def test_a_plane_one_trace_says_so_instead(self, browser, booted):
        """The defect, as a clause. This page renders a working button
        over a Plane 1 trace and used to promise process lanes."""
        out = browser.measure(booted["with_timeline"], _LOOK, 1440, 900)
        assert out["planes"] == "1", out
        assert _PROMISES_PLANE2 not in out["text"], (
            f"a Plane 1 trace still promises Plane 2's lanes: {out['text']}")
        assert _DENIES_PLANE2 in out["text"], out["text"]

    @pytest.mark.parametrize("label", sorted(pages.FIXTURES))
    def test_no_trace_claims_nothing_lands_in_one(self, browser, booted,
                                                  label):
        """The third shape, and the one the first draft of this fix got
        wrong: branching on the planes alone left the old "lands in this
        run's trace" opener on two captures that have no trace at all.
        One false claim traded for another, caught by measuring."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        assert out["planes"] == "none", out
        assert _PROMISES_PLANE2 not in out["text"], out["text"]
        assert _LANDS_IN_A_TRACE not in out["text"], (
            f"{label} has no timeline and the lead says something lands "
            f"in its trace: {out['text']}")
        assert "no timeline to open here" in out["text"], out["text"]


@needs_browser
@pytest.mark.medium
class TestTheThreeShapesAreThree:
    """A population clause rather than three examples: a lead that said
    one thing everywhere would pass any two of the classes above that
    happened to agree."""

    def test_each_state_reads_differently(self, browser, booted):
        seen = {}
        for label in ("two_plane", "with_timeline", "golden"):
            out = browser.measure(booted[label], _LOOK, 1440, 900)
            seen[label] = (out["planes"], out["text"])
        planes = [value[0] for value in seen.values()]
        assert sorted(planes) == ["1", "1+2", "none"], seen
        assert len({value[1] for value in seen.values()}) == 3, (
            "two of the three trace states render the same sentence")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
