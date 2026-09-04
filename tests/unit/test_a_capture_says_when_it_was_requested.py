"""UX-594: a capture records when the build was *requested*.

bga's clock starts when the build does, so the half of turnaround a
contributor actually experiences - the queue - was outside every number
it published. The seam is one optional instant from the CI system and
the gap to the started-at bga already had.

The rule under test is the refusal, not the subtraction: an absent
request instant publishes as an absence with a named reason, never as a
zero, because zero is a real answer and a capture that never learned
the instant has not measured one.
"""
import datetime
import json
import os
import pathlib
import shutil
import time

import pytest

from tools import _run_context_common as common
from tools.bst_run_context import build_run_context


class _NoZoneSuffix(datetime.datetime):
    """`datetime` as 3.9 and 3.10 ship it: `fromisoformat` rejects the
    trailing `Z` every CI system publishes."""

    @classmethod
    def fromisoformat(cls, text):
        if text.endswith("Z"):
            raise ValueError(f"Invalid isoformat string: {text!r}")
        return datetime.datetime.fromisoformat(text)

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPED = str(REPO / "tests/fixtures/synthetic_multi_subproject/wrapper_log.txt")
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

# The fixture log's own bst-invocation start, and an instant twenty
# minutes before it - the queue this capture would have sat in.
STARTED_AT_US = 1786611600000000
REQUESTED_AT = "2026-08-13T08:40:00Z"
WAIT_US = 1200000000


@pytest.fixture
def no_ci_instant(monkeypatch):
    """A runner that publishes nothing - the state a laptop is in, and
    the one this suite must not inherit from its own CI."""
    for name, _ in common.REQUESTED_AT_ENV:
        monkeypatch.delenv(name, raising=False)


class TestTheAcceptanceTest:
    def test_a_capture_with_a_request_instant_publishes_the_wait(
            self, monkeypatch, no_ci_instant):
        monkeypatch.setenv("CI_PIPELINE_CREATED_AT", REQUESTED_AT)
        seam = build_run_context(WRAPPED)["queue_seam"]
        assert seam["queue_wait_us"] == WAIT_US
        assert seam["started_at_us"] == STARTED_AT_US
        assert "absent_reason" not in seam

    def test_a_capture_without_one_publishes_an_absence_not_a_zero(
            self, no_ci_instant):
        seam = build_run_context(WRAPPED)["queue_seam"]
        assert seam["queue_wait_us"] is None, (
            "a wait nobody measured was published as a number")
        assert seam["requested_at_us"] is None
        assert seam["absent_reason"] == common.NO_REQUEST_INSTANT

    def test_the_seam_is_written_even_when_there_is_nothing_in_it(
            self, no_ci_instant):
        """An absent `queue_seam` has to keep meaning "the producer had
        never heard of this", so a capture from before it is never read
        as one that looked and found nothing."""
        assert "queue_seam" in build_run_context(WRAPPED)


class TestZeroIsAnAnswerAndNotADefault:
    """`UX-612`: these starts declare `log_timestamp`, because the gate
    it added refuses a start that does not say it is a real instant -
    the subtraction below is only a measurement when it is."""

    def test_a_request_at_the_start_instant_is_a_measured_zero(self):
        context = {"wall_clock": {"start_us": STARTED_AT_US,
                                  "start_us_source": "log_timestamp"}}
        common.add_queue_seam(
            context, env={"BGA_REQUESTED_AT": "2026-08-13T09:00:00Z"})
        seam = context["queue_seam"]
        assert seam["queue_wait_us"] == 0
        assert "absent_reason" not in seam

    def test_a_request_after_the_start_is_refused_rather_than_signed(self):
        context = {"wall_clock": {"start_us": STARTED_AT_US,
                                  "start_us_source": "log_timestamp"}}
        common.add_queue_seam(
            context, env={"BGA_REQUESTED_AT": "2026-08-13T09:20:00Z"})
        seam = context["queue_seam"]
        assert seam["queue_wait_us"] is None
        assert seam["absent_reason"] == common.REQUEST_AFTER_START

    def test_a_capture_with_no_start_instant_has_no_wait_either(self):
        context = {}
        common.add_queue_seam(
            context, env={"BGA_REQUESTED_AT": REQUESTED_AT})
        seam = context["queue_seam"]
        assert seam["queue_wait_us"] is None
        assert seam["started_at_us"] is None
        assert seam["absent_reason"] == common.NO_START_INSTANT
        assert seam["requested_at_us"] is not None, (
            "the instant it did learn was dropped with the wait")


class TestWhereTheInstantCameFrom:
    def test_the_source_names_the_variable_and_not_only_the_system(self):
        instant, source = common.requested_at(
            {"CI_PIPELINE_CREATED_AT": REQUESTED_AT})
        assert instant is not None
        assert source == "gitlab_ci:CI_PIPELINE_CREATED_AT"

    def test_the_generic_variable_is_tried_first(self):
        """`BGA_REQUESTED_AT` is the route a CI system bga has never
        heard of takes, and an operator correcting one takes it too."""
        _, source = common.requested_at(
            {"BGA_REQUESTED_AT": REQUESTED_AT,
             "CI_PIPELINE_CREATED_AT": "2026-08-13T08:00:00Z"})
        assert source == "env:BGA_REQUESTED_AT"

    def test_an_unreadable_instant_falls_through_rather_than_raising(self):
        """A three-hour capture must not fail because its runner
        published a timestamp in a shape bga cannot read."""
        instant, source = common.requested_at(
            {"BGA_REQUESTED_AT": "last tuesday",
             "CI_PIPELINE_CREATED_AT": REQUESTED_AT})
        assert source == "gitlab_ci:CI_PIPELINE_CREATED_AT"
        assert instant == 1786610400000000

    def test_an_empty_variable_is_not_an_instant(self):
        assert common.requested_at({"BGA_REQUESTED_AT": ""}) == (None, None)

    def test_a_trailing_z_reads_as_the_offset_it_means(self, monkeypatch):
        """`fromisoformat` only learned `Z` in 3.11 and this package
        supports 3.9, so the form every CI system publishes would parse
        on a developer's machine and not on the runner. Read against a
        `fromisoformat` narrowed to what 3.9 accepts, because on this
        interpreter the wide one hides the whole question."""
        monkeypatch.setattr(common, "datetime", _NoZoneSuffix)
        assert (common.parse_instant("2026-08-13T08:40:00Z")
                == 1786610400000000)

    def test_a_naive_instant_reads_as_utc(self, monkeypatch):
        """Read under a non-UTC zone, because a runner in one is where
        the difference between "UTC" and "whatever this machine is"
        stops being invisible."""
        monkeypatch.setenv("TZ", "Asia/Tokyo")
        time.tzset()
        try:
            assert (common.parse_instant("2026-08-13T08:40:00")
                    == 1786610400000000)
        finally:
            monkeypatch.undo()
            time.tzset()

    def test_an_offset_instant_is_not_read_as_utc(self):
        assert (common.parse_instant("2026-08-13T08:40:00+02:00")
                == common.parse_instant("2026-08-13T06:40:00Z"))


class TestBothProducersRecordIt:
    def test_the_seam_goes_in_beside_the_host_manifest(self):
        """`UX-18`'s rule: the two producer paths build the same
        run-context, so a field one of them records the other does."""
        common_source = (REPO / "tools/_run_context_common.py").read_text(
            encoding="utf-8")
        assert "def add_queue_seam(" in common_source
        for name in ("tools/bst_extract_run.py", "tools/bst_run_context.py"):
            text = (REPO / name).read_text(encoding="utf-8")
            assert "add_queue_seam(run_context)" in text, name


def _store(tmp_path, seams):
    """A project store of one snapshot per entry in `seams`, each a
    `queue_seam` value to write into that run's context (or `None` for a
    capture from before the field existed)."""
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    for nth, seam in enumerate(seams, start=1):
        run = tmp_path / ".bga" / "runs" / f"2026010{nth}T000000Z" / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        context = json.loads((run / "run-context.json").read_text())
        if seam is not None:
            context["queue_seam"] = seam
        (run / "run-context.json").write_text(json.dumps(context))
    return str(tmp_path)


class TestTheStoreRowCarriesIt:
    def test_the_row_publishes_the_wait_the_capture_recorded(self, tmp_path):
        from tools.bga_snapshot import store_listing

        rows = store_listing(_store(tmp_path, [
            {"requested_at_us": 1, "requested_at_source": "env:BGA_REQUESTED_AT",
             "started_at_us": 1 + WAIT_US, "queue_wait_us": WAIT_US},
        ]))["snapshots"]
        assert [row["queue_wait_us"] for row in rows] == [WAIT_US]
        assert [row["queue_wait_absent_reason"] for row in rows] == [None]

    def test_a_measured_absence_and_a_capture_that_never_looked_differ(
            self, tmp_path):
        """Two nulls with different meanings, and the reason is what
        tells them apart - the same distinction `UX-324` drew between
        "never started" and "started and produced nothing"."""
        from tools.bga_snapshot import store_listing

        rows = store_listing(_store(tmp_path, [
            None,
            {"requested_at_us": None, "requested_at_source": None,
             "started_at_us": 5, "queue_wait_us": None,
             "absent_reason": common.NO_REQUEST_INSTANT},
        ]))["snapshots"]
        assert [row["queue_wait_us"] for row in rows] == [None, None]
        assert [row["queue_wait_absent_reason"] for row in rows] == [
            None, common.NO_REQUEST_INSTANT]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
