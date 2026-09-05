"""UX-56: Plane 2's per-element split is only per-element if the tags
are element names.

The tracer tags each traced process with bwrap's `--dir` last path
segment, which is the element under BuildStream's *default* build-root
layout - what every project in `examples/` uses. `freedesktop-sdk` sets
its own build root, `/buildstream-build`, and on a real 127,630-process
capture of it **126,871 processes (99.4%) landed in one bucket named
`buildstream-build`**, with zero tags that look like an element.

Everything per-element in that report was then a whole-build number
wearing an element's name: `peak_work_concurrency` 1019 against 4
requested jobs, `achieved_vs_requested` 254.75, and a single "redundant
operation" claiming 44,145 seconds of recoverable time inside a
2,796-second build.

The same tracer, on the same day, produced a fully reliable split on a
real `examples/06` capture (822 processes, 9 elements, every tag ending
in `.bst`) - so this is not the mechanism failing, it is the mechanism
resting on a convention a real project is free to override.
"""
import pytest

from bga.correlate import correlate, format_correlation
from tools.bst_native_build_tracer import assess_element_attribution


def test_real_element_names_are_reliable():
    """The real `examples/06` capture's tag distribution."""
    result = assess_element_attribution({"core.bst": 113, "app.bst": 80, "lib-a.bst": 70})

    assert result["reliable"] is True
    assert result["note"] is None
    assert result["recognized_processes"] == 263


def test_the_real_freedesktop_sdk_collapse_is_caught():
    result = assess_element_attribution(
        {"buildstream-build": 126871, "expat": 411, "unknown": 336, "flit_core": 12}
    )

    assert result["reliable"] is False
    assert result["largest_bucket"] == "buildstream-build"
    assert result["largest_bucket_processes"] == 126871
    assert result["recognized_processes"] == 0
    assert "buildstream-build" in result["note"]


def test_a_partial_attribution_is_usable_and_reports_its_coverage():
    """Deliberately replaces the original all-or-nothing rule (UX-66).

    That rule read: one un-element-like bucket means some processes are
    attributed to something that is not an element, and *there is no way
    to tell which of the rest are affected*. The second half was true
    before `UX-64` and is false after it: the residue is not mislabelled,
    it sits in a named unresolved bucket precisely because its sandbox
    could not be matched to exactly one element.

    Round 8 is what forced the change. 86.1% of a real build's processes
    were correctly named, every resolved name valid against the declared
    graph, and the report still refused - citing `components/bison.bst`,
    which is an element, as evidence that attribution had failed.
    """
    result = assess_element_attribution({"core.bst": 100, "buildstream-build": 1})

    assert result["reliable"] is True
    assert result["attributed_share"] == pytest.approx(100 / 101)
    assert result["unattributed_processes"] == 1
    assert result["unresolved_bucket"] == "buildstream-build"
    assert "cover the attributed share only" in result["note"]


def test_names_that_are_all_fiction_are_still_refused():
    """The case the original rule was written for, unchanged: when no
    bucket is an element name, every per-element figure is fiction."""
    result = assess_element_attribution({"buildstream-build": 1000})

    assert result["reliable"] is False
    assert "none of 1000 traced processes" in result["note"]


def test_a_fully_attributed_run_reports_no_shortfall():
    result = assess_element_attribution({"core.bst": 100, "app.bst": 50})

    assert result["reliable"] is True
    assert result["unattributed_processes"] == 0
    assert result["note"] is None


def test_no_tags_at_all_is_unreliable_and_says_so():
    result = assess_element_attribution({})

    assert result["reliable"] is False
    assert result["note"] == "no process carried an element tag at all"


def test_unknown_alone_is_not_mistaken_for_an_element():
    """`unknown` is the tracer's own placeholder for a process whose
    bwrap invocation carried no `--dir` - it must never count as a
    recognized element."""
    result = assess_element_attribution({"unknown": 50})

    assert result["reliable"] is False
    assert result["recognized_elements"] == []


def test_recognized_elements_are_listed_sorted():
    result = assess_element_attribution({"b.bst": 1, "a.bst": 2})

    assert result["recognized_elements"] == ["a.bst", "b.bst"]


# --- the consumer: refuse the join rather than render it ---------------


_ANALYSIS = {
    "signals": {"critical_path": ["core.bst"], "critical_path_detail": [], "blast_radius": {}},
    "structural": {"sensitivity": {"top_opportunities": []}},
    "floors": {},
}


def _native(attribution):
    return {
        "per_element_parallelism": [
            {"element": "buildstream-build", "requested_jobs": 4, "findings": []}
        ],
        "cpu_time": {"per_element": {}},
        "element_attribution": attribution,
    }


def test_correlate_refuses_an_unreliable_join():
    report = _native({"reliable": False, "note": "collapsed into buildstream-build"})

    result = correlate(_ANALYSIS, report)

    assert result["attribution_unreliable"] == "collapsed into buildstream-build"
    assert result["actionable"] == []


def test_the_refusal_is_the_whole_rendered_output():
    """A reader must not scroll past a warning into a table of rows that
    do not mean anything."""
    report = _native({"reliable": False, "note": "collapsed into buildstream-build"})

    text = format_correlation(correlate(_ANALYSIS, report))

    assert "NO USABLE JOIN" in text
    assert "collapsed into buildstream-build" in text
    assert "Joined" not in text


def test_a_reliable_report_correlates_as_before():
    report = _native({"reliable": True, "note": None})

    result = correlate(_ANALYSIS, report)

    assert result["attribution_unreliable"] is None
    assert "Joined" in format_correlation(result)


def test_a_report_without_the_field_correlates_as_before():
    """Native reports produced before UX-56 have no
    `element_attribution` key at all, and must keep working."""
    report = _native(None)
    report.pop("element_attribution")

    result = correlate(_ANALYSIS, report)

    assert result["attribution_unreliable"] is None
    assert "Joined" in format_correlation(result)
