"""UX-612: `wall_clock.start_us` says which clock produced it.

Two measurements wore one name. Measured on this tree at `5343bd6`,
before the fix:

```text
--format raw       start_us 1786665600000000 == the log file's mtime
--format wrapped   start_us 1786611600000000, mtime 1788497049826867
run-context keys   identical either way; nothing said which
```

So `UX-594`'s queue wait subtracted a request instant from a file's
last-write time and published the difference: `queue_wait_us`
1200000000 on the raw path above, a figure with no measurement behind
it.

The rule under test is the **refusal**, not the label: a consumer that
needs a real instant gates on the source, and the wait publishes an
absence naming the clock rather than a number that is wrong by however
long the build ran before the file was last written.
"""
import json
import os
import pathlib

import pytest

from tools import _run_context_common as common
from tools.bst_log_to_chrome_trace import (START_FILE_MTIME,
                                           START_LOG_TIMESTAMP,
                                           START_OPERATOR_DECLARED,
                                           WrapperTraceConverter,
                                           _resolve_start_time_source,
                                           _resolve_start_time_us)
from tools.bst_run_context import build_run_context

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPED = str(REPO / "tests/fixtures/synthetic_multi_subproject/wrapper_log.txt")

# The wrapped fixture's own bst-invocation start, and an instant twenty
# minutes before it - the queue this capture would have sat in.
WRAPPED_START_US = 1786611600000000
REQUESTED_AT = "2026-08-13T08:40:00Z"
WAIT_US = 1200000000

# 2026-08-14T00:00:00Z, as an mtime and as the `--start-time` spelling.
ANCHOR = 1786665600.0
ANCHOR_ISO = "2026-08-14T00:00:00+00:00"

RAW_LOG = (
    "    Maximum Build Tasks:     3\n"
    "[--:--:--][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log\n"
    "[00:00:05][4a9059d4][   build:base.bst] SUCCESS base/4a9059d4-build.log\n"
)


@pytest.fixture
def raw_log(tmp_path):
    """A raw capture whose file was last written long after the build it
    records - which is every raw capture, and the whole defect."""
    log = tmp_path / "raw.log"
    log.write_text(RAW_LOG)
    os.utime(log, (ANCHOR, ANCHOR))
    return str(log)


@pytest.fixture
def a_request_instant(monkeypatch):
    """A runner that publishes one, twenty minutes before the anchor."""
    monkeypatch.setenv("BGA_REQUESTED_AT", "2026-08-13T23:40:00Z")
    monkeypatch.delenv("CI_PIPELINE_CREATED_AT", raising=False)


@pytest.fixture
def no_ci_instant(monkeypatch):
    """A runner that publishes nothing - the state a laptop is in, and
    the one this suite must not inherit from its own CI."""
    for name, _ in common.REQUESTED_AT_ENV:
        monkeypatch.delenv(name, raising=False)


class TestTheAcceptanceTest:
    def test_a_raw_capture_refuses_the_wait_and_names_the_clock(
            self, raw_log, a_request_instant):
        """A raw-path capture, and the queue wait absent with a reason
        naming the clock rather than a figure. The figure it would have
        published is `WAIT_US`, and it is not a measurement of
        anything."""
        seam = build_run_context(raw_log, log_format="raw")["queue_seam"]

        assert seam["queue_wait_us"] is None, (
            f"published {seam['queue_wait_us']}, which is the gap to the "
            f"file's mtime and not to the build's start")
        assert seam["absent_reason"] == common.START_NOT_AN_INSTANT
        assert seam["started_at_source"] == START_FILE_MTIME
        assert seam["requested_at_us"] is not None, (
            "the instant it did learn was dropped with the wait")

    def test_the_raw_start_is_the_mtime_and_says_so(self, raw_log,
                                                    no_ci_instant):
        clock = build_run_context(raw_log, log_format="raw")["wall_clock"]
        assert clock["start_us"] == int(os.path.getmtime(raw_log) * 1e6)
        assert clock["start_us_source"] == START_FILE_MTIME


class TestAWrappedCaptureStillPublishesItsWait:
    def test_a_real_instant_is_not_refused_by_the_new_gate(
            self, monkeypatch, no_ci_instant):
        """The other half: the gate must let through the path that
        always had a real instant, or it is a gate that refuses
        everything."""
        monkeypatch.setenv("CI_PIPELINE_CREATED_AT", REQUESTED_AT)
        seam = build_run_context(WRAPPED, log_format="wrapped")["queue_seam"]

        assert seam["queue_wait_us"] == WAIT_US
        assert seam["started_at_source"] == START_LOG_TIMESTAMP
        assert "absent_reason" not in seam

    def test_the_wrapped_start_is_not_the_files_mtime(self, no_ci_instant):
        """The two numbers the premise is about, on the same file."""
        clock = build_run_context(WRAPPED, log_format="wrapped")["wall_clock"]
        assert clock["start_us"] == WRAPPED_START_US
        assert clock["start_us"] != int(os.path.getmtime(WRAPPED) * 1e6)


class TestAnOperatorDeclaredAnchorIsAnInstant:
    def test_start_time_publishes_the_wait_a_raw_capture_refuses(
            self, raw_log, a_request_instant):
        """`--start-time` is an operator saying when the build began,
        which is a claim about a real instant - the same tier
        `native_max_jobs_source` gives an operator-declared value."""
        context = build_run_context(raw_log, log_format="raw",
                                    start_time=ANCHOR_ISO)

        assert context["wall_clock"]["start_us_source"] == START_OPERATOR_DECLARED
        assert context["queue_seam"]["queue_wait_us"] == WAIT_US

    def test_the_source_agrees_with_the_anchor_it_describes(self, raw_log):
        """`_resolve_start_time_source` answers for the same argument
        `_resolve_start_time_us` resolved, so the two cannot drift into
        describing different anchors."""
        assert (_resolve_start_time_us(None, raw_log)
                == int(ANCHOR * 1e6))
        assert _resolve_start_time_source(None) == START_FILE_MTIME
        assert (_resolve_start_time_us(ANCHOR_ISO, raw_log)
                == int(ANCHOR * 1e6))
        assert _resolve_start_time_source(ANCHOR_ISO) == START_OPERATOR_DECLARED


class TestTheSourceIsTheEventsAndNotTheFlags:
    def test_the_earliest_invocation_is_the_one_sourced(self):
        """`invocation_wall_clock` takes `min(begins)`, so the source
        has to be that event's. `auto` decides per line and a log can
        open one invocation each way, which is why this is keyed on the
        event rather than on `--format`."""
        converter = WrapperTraceConverter(raw_start_time_us=1_000_000,
                                          raw_start_time_source=START_FILE_MTIME)
        converter.process_line(
            "[--:--:--][4a9059d4][   build:base.bst] START   base/x-build.log")
        converter.process_line(
            "[wrapper][2026-08-14 11:00:00,000] INFO: "
            "Executing command: bst build w")

        begins = [event["ts"] for event in converter.trace_events
                  if event.get("cat") == "bst-invocation"
                  and event.get("ph") == "B"]
        assert len(begins) == 2 and min(begins) == 1_000_000, begins
        assert converter.invocation_start_source() == START_FILE_MTIME

    def test_a_log_with_no_invocation_sources_nothing(self):
        """`wall_clock` is omitted there, and a source for a field that
        is not there would be a claim about nothing."""
        converter = WrapperTraceConverter(raw_start_time_us=0)
        converter.process_line("not a buildstream log at all")
        assert converter.invocation_start_source() is None

    def test_no_wall_clock_gets_no_source(self, tmp_path, no_ci_instant):
        log = tmp_path / "empty.log"
        log.write_text("not a buildstream log at all\n")
        context = build_run_context(str(log), log_format="raw",
                                    start_time=ANCHOR_ISO)
        assert "wall_clock" not in context
        assert context["queue_seam"]["started_at_source"] is None
        assert context["queue_seam"]["absent_reason"] == common.NO_REQUEST_INSTANT


class TestTheGateIsAMembershipAndNotADenyList:
    def test_an_unsourced_start_is_refused_rather_than_trusted(self):
        """A producer that published no source at all has not said the
        start is an instant, and a gate that read only `file_mtime`
        would trust every one of them."""
        context = {"wall_clock": {"start_us": WRAPPED_START_US}}
        common.add_queue_seam(context, env={"BGA_REQUESTED_AT": REQUESTED_AT})

        assert context["queue_seam"]["queue_wait_us"] is None
        assert (context["queue_seam"]["absent_reason"]
                == common.START_NOT_AN_INSTANT)

    def test_a_source_nobody_decided_about_is_refused_too(self):
        context = {"wall_clock": {"start_us": WRAPPED_START_US,
                                  "start_us_source": "a_clock_from_the_future"}}
        common.add_queue_seam(context, env={"BGA_REQUESTED_AT": REQUESTED_AT})

        assert (context["queue_seam"]["absent_reason"]
                == common.START_NOT_AN_INSTANT)

    def test_the_mtime_is_refused_before_the_orderings_are_compared(self):
        """A mtime is *after* the request instant in the ordinary case,
        so `request_after_start` would report a clock disagreement on
        every raw capture in a CI system - a named remedy for a fault
        that is not there."""
        context = {"wall_clock": {"start_us": WRAPPED_START_US,
                                  "start_us_source": START_FILE_MTIME}}
        common.add_queue_seam(
            context, env={"BGA_REQUESTED_AT": "2026-08-13T09:20:00Z"})

        assert (context["queue_seam"]["absent_reason"]
                == common.START_NOT_AN_INSTANT)

    def test_a_capture_with_no_start_at_all_still_says_so(self):
        """`no_start_instant` and `start_not_an_instant` are different
        claims: one has no number, the other has one and refuses it."""
        context = {}
        common.add_queue_seam(context, env={"BGA_REQUESTED_AT": REQUESTED_AT})
        assert context["queue_seam"]["absent_reason"] == common.NO_START_INSTANT


class TestBothProducersRecordIt:
    def test_the_source_goes_in_beside_the_seam(self):
        """`UX-18`'s rule: the two producer paths build the same
        run-context, so a field one of them records the other does."""
        source = (REPO / "tools/_run_context_common.py").read_text(
            encoding="utf-8")
        assert "def add_start_clock_source(" in source
        for name in ("tools/bst_extract_run.py", "tools/bst_run_context.py"):
            text = (REPO / name).read_text(encoding="utf-8")
            assert "add_start_clock_source(run_context," in text, name
            assert "_resolve_start_time_source(start_time)" in text, name


class TestTheRowDeclaresTheNewReason:
    def test_the_store_schema_permits_the_reason_the_capture_writes(self):
        """A reason the producer emits and the contract does not name is
        a value no consumer can key on - `UX-190`'s own defect."""
        from bga import schemas

        node = schemas.schema(schemas.STORE)
        row = (node["properties"]["snapshots"]["items"]["properties"]
               ["queue_wait_absent_reason"])
        assert common.START_NOT_AN_INSTANT in row["enum"], row["enum"]

    def test_every_reason_the_producer_can_write_is_in_the_enum(self):
        """The property, not the list: whatever `add_queue_seam` can
        put in `absent_reason` has to be declared."""
        from bga import schemas

        node = schemas.schema(schemas.STORE)
        declared = set((node["properties"]["snapshots"]["items"]["properties"]
                        ["queue_wait_absent_reason"])["enum"])
        emitted = set()
        for start, source, env in (
                (None, None, {}),
                (1, START_LOG_TIMESTAMP, {}),
                (1, None, {"BGA_REQUESTED_AT": REQUESTED_AT}),
                (1, START_FILE_MTIME, {"BGA_REQUESTED_AT": REQUESTED_AT}),
                (1, START_LOG_TIMESTAMP, {"BGA_REQUESTED_AT": REQUESTED_AT})):
            context = {} if start is None else {
                "wall_clock": {"start_us": start, "start_us_source": source}}
            common.add_queue_seam(context, env=env)
            emitted.add(context["queue_seam"].get("absent_reason"))
        assert emitted <= declared, sorted(emitted - declared)
        assert common.START_NOT_AN_INSTANT in emitted, (
            "the case this item is about was not reached")


class TestTheCaptureOnDiskCarriesIt:
    def test_the_written_run_context_holds_the_source(self, raw_log, tmp_path,
                                                      no_ci_instant):
        """Through `json.dump`, because a field a consumer reads off
        disk is the only one that reaches one."""
        out = tmp_path / "run-context.json"
        out.write_text(json.dumps(build_run_context(raw_log, log_format="raw")))
        assert (json.loads(out.read_text())["wall_clock"]["start_us_source"]
                == START_FILE_MTIME)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
