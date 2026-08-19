"""The reports read as one tool, or they do not.

`bga` prints six different report surfaces across three planes, written
at different times by different tasks. Each was checked on its own; none
was checked against the others. This is the cross-check: the properties
below are about *consistency* between reports and about numbers a reader
could misread, not about any single report's contents.
"""
from bga.cache_trend import format_trend_text
from bga.correlate import format_correlation
from bga.report.text import _attribution_label
from tools.bst_cache_logs import _elide_element, _pct


BANNER = "=" * 60

# The smallest coverage block `format_correlation` will render - these
# tests are about the frame around the rows, not about the rows.
_COVERAGE = {
    "joined_elements": 0,
    "plane1_elements": 0,
    "plane2_elements": 0,
    "plane1_only_with_impact": [],
    "undeclared_plane2_elements": [],
}
_NOTE = "the join's standing note"


def _correlation(**overrides) -> dict:
    """A minimal, valid correlation result. These tests are about the
    frame around the rows, not about the rows."""
    result = {
        "elements": [], "actionable": [], "coverage": dict(_COVERAGE),
        "attribution_unreliable": None, "attribution_partial": None,
        "note": _NOTE,
    }
    result.update(overrides)
    return result


class TestOneBannerWidth:
    """Two reports pasted into one issue should look like two reports
    from one tool. `bga cache-trend` was 78 columns wide while every
    other report was 60."""

    def test_the_trend_matches_the_others(self):
        text = format_trend_text({
            "runs": [], "findings": [], "insufficient_window": None,
            "note": "a note",
        })
        banners = [line for line in text.splitlines() if set(line) == {"="}]

        assert banners, "the trend report printed no banner at all"
        assert all(line == BANNER for line in banners), banners

    def test_the_correlation_matches_the_others(self):
        text = format_correlation(_correlation())
        banners = [line for line in text.splitlines() if set(line) == {"="}]

        assert banners and all(line == BANNER for line in banners), banners


class TestEveryReportSaysWhichRunItIs:
    """UX-95's rule - a report that names no run cannot be filed,
    compared, or trusted a week later - was applied to Plane 1 and to
    `bga compare`, and to nothing else."""

    def test_the_correlation_carries_plane_1s_identity(self):
        text = format_correlation(_correlation(
            run_id="f12a845e2327de7a",
            run_instance={"started_at": "2026-08-19 06:34:51 UTC",
                          "run_dir": "capture/run"},
        ))

        assert "Run: f12a845e2327de7a" in text
        assert "Instance: 2026-08-19 06:34:51 UTC  capture/run" in text

    def test_and_omits_it_rather_than_inventing_one(self):
        """A join of artifacts that carry no identity says nothing about
        identity - it does not print an empty `Run:` line."""
        text = format_correlation(_correlation())

        assert "Run:" not in text
        assert "Instance:" not in text


class TestNumbersThatCouldBeMisread:
    def test_a_unit_suffix_never_survives_into_a_label(self):
        """`execution_on_chain_us` titled naively is "Execution On Chain
        Us" - a label naming microseconds beside a value printed in
        seconds."""
        assert _attribution_label("execution_on_chain_us") == "Execution On Chain"
        assert _attribution_label("idle_us") == "Idle"
        # A category without the suffix is untouched.
        assert _attribution_label("retry_wait") == "Retry Wait"

    def test_a_nonzero_share_never_renders_as_zero(self):
        """A 1.0s toll on a 594.0s element is 0.17%. Printed as `0%`
        beside a real number, it says the toll was not paid."""
        assert _pct(1.0 / 594.0) == "<1%"
        assert _pct(0.0) == "0%"
        assert _pct(0.08) == "8%"
        assert _pct(1.0) == "100%"

    def test_an_elided_element_keeps_the_half_that_identifies_it(self):
        """A fixed slice truncates the head, and on a real project that
        turns two different elements into two names that differ only past
        the cut - with nothing saying they were cut."""
        long_a = "components/_private/cmake-stage1.bst"
        long_b = "components/_private/git-minimal.bst"

        assert _elide_element(long_a) != _elide_element(long_b)
        assert _elide_element(long_a).endswith("cmake-stage1.bst")
        assert _elide_element(long_a).startswith("…")
        assert len(_elide_element(long_a)) == 28
        # Short enough to fit is left exactly as it is.
        assert _elide_element("components/icu.bst") == "components/icu.bst"


class TestTheSameSentenceIsNotPrintedFourTimes:
    def test_findings_sharing_a_rationale_state_it_once(self):
        """Four split candidates used to mean four verbatim copies of the
        same three-sentence caveat - 1300 characters saying one thing."""
        rationale = "Evidence, not a recommendation: a split's shape is a human decision"
        text = format_correlation(_correlation(granularity=[
            {"severity": "info", "id": "split-candidate",
             "title": f"{name} holds 20% of the critical path",
             "rationale": rationale}
            for name in ("a.bst", "b.bst", "c.bst", "d.bst")
        ]))

        assert text.count(rationale) == 1
        for name in ("a.bst", "b.bst", "c.bst", "d.bst"):
            assert name in text

    def test_findings_with_different_rationales_keep_both(self):
        text = format_correlation(_correlation(granularity=[
            {"severity": "info", "id": "split-candidate",
             "title": "a.bst is big", "rationale": "because of one thing"},
            {"severity": "info", "id": "merge-candidate",
             "title": "b.bst is small", "rationale": "because of another"},
        ]))

        assert "because of one thing" in text
        assert "because of another" in text


class TestEveryReportNamesItself:
    """Six report surfaces across three planes. Five opened with a banner
    saying what they were; Plane 2's opened with a process count, so a
    native report pasted anywhere was unidentifiable as one."""

    def test_the_native_report_names_its_plane(self):
        from tools.bst_native_build_tracer import _format_text

        text = _format_text({
            "process_count": 24, "matched_count": 24, "open_count": 0,
            "max_concurrency": 4, "wall_span_s": 12.0, "by_binary": {},
            "by_element": {}, "element_attribution": {"reliable": True},
            "cpu_time": {"available": False, "note": "n"},
            "peak_memory": {"available": False, "note": "n"},
            "binary_cost": {}, "per_element_parallelism": [],
            "redundant_operations": [], "opens_captured": {},
            "open_records_note": "n", "static_binary_disclaimer": "n",
            "processes": [], "matched": [],
        })
        lines = text.splitlines()

        assert lines[0] == BANNER
        assert "Plane 2" in lines[1]
        assert lines[2] == BANNER
        # ...and closed, so a truncated paste is visibly truncated.
        assert lines[-1] == BANNER

    def test_a_task_citation_never_interrupts_the_line_it_annotates(self):
        """Notes across this tool cite their task in trailing parentheses.
        One line put `UX-61:` mid-sentence, in the primary output a reader
        has to understand before any number below means anything."""
        from tools.bst_native_build_tracer import _format_text

        text = _format_text({
            "process_count": 1, "matched_count": 1, "open_count": 0,
            "max_concurrency": 1, "wall_span_s": 1.0, "by_binary": {},
            "by_element": {}, "element_attribution": {"reliable": True},
            "cpu_time": {"available": False, "note": "n"},
            "peak_memory": {"available": False, "note": "n"},
            "binary_cost": {}, "per_element_parallelism": [],
            "redundant_operations": [], "opens_captured": {},
            "open_records_note": "n", "static_binary_disclaimer": "n",
            "processes": [], "matched": [],
        })
        concurrency = next(
            line for line in text.splitlines() if "Max observed concurrency" in line
        )

        assert "(UX-61)" in concurrency
        assert "UX-61:" not in concurrency
