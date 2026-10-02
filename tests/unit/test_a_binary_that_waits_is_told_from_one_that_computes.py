"""UX-1275: a binary's blocked time is its lifetime less its own CPU less the time a child of its was live.

Measured before, on the 2,402-element `--workload binaries` page: `make` read 2.9 h wall against 36.0 s CPU,
and the jobs-waiting step named no binary. Wall minus CPU is its children's lifetimes, not its wait.
"""

import contextlib
import io
import json

import pytest

from bga.cli import main
from bga.plane2 import binary_totals
from tests import pages
from tools.bst_native_build_tracer import summarize

SHAPE = ("--workload", "binaries", "--layers", "20", "--width", "60")


def _record(pid, ppid, start, end, cpu_us, cmd, invocation="i1"):
    return {
        "pid": pid,
        "ppid": ppid,
        "element": "e.bst",
        "invocation": invocation,
        "cmd": cmd,
        "start_ts": start,
        "end_ts": end,
        "duration_s": end - start,
        "open": False,
        "cpu_us": cpu_us,
        "src": "hook",
    }


def _blocked(records):
    entries = summarize(records)["binary_cost"]["e.bst"]["binaries"]
    return {entry["binary"]: entry.get("blocked_us") for entry in entries}


def test_make_waits_nine_seconds_not_ninety_nine():
    """make: 100 s alive, 1 s CPU, two overlapping children live 5-95 s -> 9 s blocked."""
    blocked = _blocked(
        [
            _record(10, 1, 0.0, 100.0, 1_000_000, "/usr/bin/make -j4"),
            _record(11, 10, 5.0, 50.0, 40_000_000, "cc1 a.c"),
            _record(12, 10, 40.0, 95.0, 50_000_000, "cc1 b.c"),
        ]
    )
    assert blocked == {"make": 9_000_000, "cc1": 10_000_000}, blocked


def test_a_recycled_pid_bills_the_occupant_alive_at_the_childs_start():
    """Two `sh` share pid 20, the earlier one recorded last; the child started inside the later one's span."""
    blocked = _blocked(
        [
            _record(20, 1, 20.0, 30.0, 0, "sh -c two"),
            _record(21, 20, 21.0, 29.0, 8_000_000, "cc1 x.c"),
            _record(20, 1, 0.0, 10.0, 0, "sh -c one"),
        ]
    )
    assert blocked == {"sh": 10_000_000 + 2_000_000, "cc1": 0}, blocked


def test_a_report_without_blocked_time_leaves_the_column_absent():
    report = {
        "by_binary": {"make": 1},
        "binary_cost": {
            "a.bst": {
                "available": True,
                "measured_cpu_us": 5,
                "binaries": [{"binary": "make", "count": 1, "cpu_us": 5, "wall_s": 1.0}],
            }
        },
    }
    (row,) = binary_totals(report)
    assert "blocked_us" not in row and "blocked_share" not in row, row


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    run = pages.two_plane_run(tmp_path_factory.mktemp("ux1275"), SHAPE, name="binaries")
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run), "--format", "json"])
    return json.loads(buffer.getvalue())


def test_makes_blocked_time_excludes_its_childrens_lifetimes(page):
    (make,) = [row for row in page["by_binary"] if row["binary"] == "make"]
    # make's children are live for over a tenth of its wall here; wall minus CPU counts that as waiting.
    assert 0 < make["blocked_us"] < 0.9 * (make["wall_us"] - make["cpu_us"]), make
    assert make["blocked_share"] == round(make["blocked_us"] / make["wall_us"], 3), make


def test_the_waiting_step_names_a_binary_from_the_blocked_ranking(page):
    (finding,) = [finding for finding in page["findings"] if finding["id"] == "jobs-waiting"]
    ranked = sorted((row for row in page["by_binary"] if "blocked_us" in row), key=lambda row: -row["blocked_us"])
    named = [row["binary"] for row in ranked[:3] if f"{row['binary']} (" in finding["step"]["text"]]
    assert named, (finding["step"], [row["binary"] for row in ranked[:3]])
