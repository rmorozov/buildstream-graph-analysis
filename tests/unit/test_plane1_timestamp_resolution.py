"""UX-110: Plane 1's own durations, measured twice.

A wrapped log line is stamped when the wrapper *reads* it, and
BuildStream flushes in bursts, so both ends of every span carry a
read-lag. The same log carries a second, independent measurement of each
task - BuildStream's `[HH:MM:SS]` elapsed prefix, its own timing
truncated to whole seconds - and comparing the two turns an assumption
about precision into a number.

Measured on three real builds spanning 12s to 3261s: the wrapper's span
runs from 0.56s short of BuildStream's own figure to 1.50s long. Bounded,
not proportional - invisible on a real compile and 11% of a
three-second task. On `examples/01` it made two of eight *identical*
elements report 2.686s for a `sleep 3`.
"""
import pytest

from tools.bst_log_to_chrome_trace import WrapperTraceConverter


def _wrapped(converter, lines):
    for line in lines:
        converter.process_line_wrapped(line)
    return converter


def _task(start_ms, end_ms, elapsed, element="work.bst", h="4a9059d4"):
    return [
        f"[wrapper][2026-08-14 11:00:{start_ms}] INFO: "
        f"[--:--:--][{h}][   build:{element}] START   {element}/{h}-build.log",
        f"[wrapper][2026-08-14 11:00:{end_ms}] INFO: "
        f"[{elapsed}][{h}][   build:{element}] SUCCESS {element}/{h}-build.log",
    ]


class TestTheSecondMeasurement:
    def test_a_span_shorter_than_buildstream_own_timing_is_provably_wrong(self):
        """The `examples/01` case, in miniature: the wrapper timed the
        task at 2.7s and BuildStream timed it at 3s. One of those did not
        happen, and it is not BuildStream's."""
        converter = _wrapped(WrapperTraceConverter(), [
            "[wrapper][2026-08-14 11:00:00,000] INFO: Executing command: bst build w",
            *_task("00,300", "03,000", "00:00:03"),
        ])
        agreement = converter.get_timestamp_agreement()

        assert agreement["tasks_compared"] == 1
        assert agreement["tasks_shorter_than_bst"] == 1
        entry, = agreement["shorter_than_bst"]
        assert entry["element"] == "work.bst"
        assert entry["span_s"] == 2.7
        assert entry["bst_elapsed_s"] == 3.0
        assert entry["shortfall_s"] == 0.3
        assert agreement["worst_shortfall_s"] == -0.3

    def test_a_span_longer_than_the_elapsed_second_is_ordinary(self):
        """BuildStream truncates its elapsed to whole seconds, so a span
        up to a second longer says nothing - only the excess beyond that
        is lag, and it is recorded rather than flagged."""
        converter = _wrapped(WrapperTraceConverter(), [
            "[wrapper][2026-08-14 11:00:00,000] INFO: Executing command: bst build w",
            *_task("00,000", "03,900", "00:00:03"),
        ])
        agreement = converter.get_timestamp_agreement()

        assert agreement["tasks_shorter_than_bst"] == 0
        assert agreement["worst_excess_s"] == pytest.approx(0.9)

    def test_a_raw_log_has_no_second_measurement_and_says_so(self):
        """In raw mode the timestamps are *reconstructed from* the
        elapsed prefix, so comparing them would be a tautology. `None`
        rather than a clean bill of health - "not compared" and
        "compared and agreed" are different claims."""
        converter = WrapperTraceConverter(raw_start_time_us=1_000_000_000)
        for line in (
            "[--:--:--][4a9059d4][   build:work.bst] START   work.bst/4a9059d4-build.log",
            "[00:00:03][4a9059d4][   build:work.bst] SUCCESS work.bst/4a9059d4-build.log",
        ):
            converter.process_line_raw(line)

        assert converter.get_timestamp_agreement() is None

    def test_nested_sub_phases_are_not_separate_tasks(self):
        """BuildStream emits START/SUCCESS pairs for a task's internal
        phases under the same hash. Only the outer bracket carries the
        task's own elapsed, and only it is compared."""
        converter = _wrapped(WrapperTraceConverter(), [
            "[wrapper][2026-08-14 11:00:00,000] INFO: Executing command: bst build w",
            "[wrapper][2026-08-14 11:00:00,000] INFO: "
            "[--:--:--][4a9059d4][   build:work.bst] START   work.bst/4a9059d4-build.log",
            "[wrapper][2026-08-14 11:00:00,100] INFO: "
            "[--:--:--][4a9059d4][   build:work.bst] START   Staging dependencies",
            "[wrapper][2026-08-14 11:00:00,200] INFO: "
            "[00:00:00][4a9059d4][   build:work.bst] SUCCESS Staging dependencies",
            "[wrapper][2026-08-14 11:00:03,000] INFO: "
            "[00:00:03][4a9059d4][   build:work.bst] SUCCESS work.bst/4a9059d4-build.log",
        ])
        agreement = converter.get_timestamp_agreement()

        assert agreement["tasks_compared"] == 1
        assert agreement["tasks_shorter_than_bst"] == 0


class TestTheReportStatesTheResolution:
    """A resolution line on a forty-minute compile is furniture. It has
    to speak where the number changes a reading and stay quiet where it
    does not."""

    @staticmethod
    def _result(**agreement):
        from bga.ingest.models import AnalysisResult

        result = AnalysisResult()
        result.timestamp_agreement = agreement
        return result

    def test_silent_when_every_task_dwarfs_the_lag(self):
        from bga.report.text import _format_timestamp_resolution

        lines = _format_timestamp_resolution(self._result(
            tasks_compared=25, tasks_shorter_than_bst=0, shorter_than_bst=[],
            resolution_s=1.5, shortest_task_s=600.0, tasks_measured=25,
            tasks_where_material=0, material_share=0.05,
        ))

        assert lines == []

    def test_silent_when_the_capture_has_only_one_measurement(self):
        from bga.report.text import _format_timestamp_resolution

        assert _format_timestamp_resolution(self._result()) == []

    def test_speaks_when_the_lag_is_a_material_share_of_a_task(self):
        from bga.report.text import _format_timestamp_resolution

        text = " ".join(_format_timestamp_resolution(self._result(
            tasks_compared=20, tasks_shorter_than_bst=0, shorter_than_bst=[],
            resolution_s=0.31, shortest_task_s=2.69, tasks_measured=8,
            tasks_where_material=8, material_share=0.05,
        )))

        assert "±0.31s" in text
        assert "more than 5% of the duration for 8 of 8" in text

    def test_and_names_a_duration_that_did_not_happen(self):
        from bga.report.text import _format_timestamp_resolution

        text = " ".join(_format_timestamp_resolution(self._result(
            tasks_compared=20, tasks_shorter_than_bst=2,
            shorter_than_bst=[{"element": "work-g.bst", "action": "build",
                               "span_s": 2.687, "bst_elapsed_s": 3.0,
                               "shortfall_s": 0.313}],
            resolution_s=0.31, shortest_task_s=2.69, tasks_measured=8,
            tasks_where_material=8, material_share=0.05,
        )))

        assert "SHORTER than BuildStream's own timing" in text
        assert "work-g.bst at 2.687s against 3s" in text
        assert "did not happen" in text


def test_it_survives_the_round_trip_from_log_to_report(tmp_path):
    """Converter -> run-context.json -> loader -> analyzer -> report.
    Four hand-offs, and the field is only worth anything if it makes all
    four."""
    import json

    from bga.ingest.loader import load_run_context

    converter = _wrapped(WrapperTraceConverter(), [
        "[wrapper][2026-08-14 11:00:00,000] INFO: Executing command: bst build w",
        *_task("00,300", "03,000", "00:00:03"),
    ])
    agreement = converter.get_timestamp_agreement()

    path = tmp_path / "run-context.json"
    path.write_text(json.dumps({"timestamp_agreement": agreement}))
    context = load_run_context(path)

    assert context.timestamp_agreement["tasks_shorter_than_bst"] == 1
    assert context.plane1_resolution_s == pytest.approx(0.3)


def test_a_capture_without_the_field_reports_no_resolution():
    """Every run directory extracted before this existed. `None` is the
    honest answer, and the report is silent on it."""
    from bga.ingest.models import RunContext

    assert RunContext().plane1_resolution_s is None
