"""UX-1275: a binary's blocked time is its lifetime less its own CPU less the time a child of its was live.

Measured before, on the 2,402-element `--workload binaries` page: `make` read 2.9 h wall against 36.0 s CPU,
and the jobs-waiting step named no binary. Wall minus CPU is its children's lifetimes, not its wait.
"""

import contextlib
import io
import json
import re
from types import SimpleNamespace

import pytest

from bga import shown
from bga.cli import main
from bga.findings import _plane2_findings
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
    root_only = summarize([_record(10, 1, 0.0, 100.0, 1_000_000, "/usr/bin/make -j4")])["binary_cost"]["e.bst"]
    assert "blocked_unparented" not in root_only, root_only


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


def test_a_child_whose_parent_was_missed_is_counted_where_blocked_time_is_published():
    """cc1's parent pid 11 was never recorded: make reads its whole life blocked, and the element says one was missed."""
    records = [
        _record(10, 1, 0.0, 100.0, 1_000_000, "/usr/bin/make -j4"),
        _record(12, 11, 10.0, 90.0, 80_000_000, "cc1 a.c"),
    ]
    cost = summarize(records)["binary_cost"]["e.bst"]
    assert {entry["binary"]: entry["blocked_us"] for entry in cost["binaries"]} == {"make": 99_000_000, "cc1": 0}
    assert cost["blocked_unparented"] == 1, cost


def _waiting_report():
    """Two waiting elements and one computing; CPU ranks cc1 first, blocked ranks make, sh, ld; the busy one blocks most."""
    costs = {
        "w1.bst": [("cc1", 100_000_000, 1_000_000), ("make", 1_000_000, 30_000_000), ("sh", 2_000_000, 20_000_000)],
        "w2.bst": [("make", 1_000_000, 20_000_000), ("ld", 5_000_000, 10_000_000)],
        "busy.bst": [("zzz", 1_000_000, 900_000_000)],
    }
    cores = {"w1.bst": 0.2, "w2.bst": 0.3, "busy.bst": 3.5}
    return {
        "per_element_parallelism": [{"element": uid, "requested_jobs": 4} for uid in costs],
        "cpu_time": {"per_element": {uid: {"cpu_per_wall_second": c, "wall_span_s": 1.0} for uid, c in cores.items()}},
        "binary_cost": {
            uid: {
                "available": True,
                "measured_cpu_us": sum(cpu for _b, cpu, _w in rows),
                "binaries": [
                    {"binary": b, "count": 1, "cpu_us": cpu, "wall_s": 1.0, "blocked_us": w} for b, cpu, w in rows
                ],
            }
            for uid, rows in costs.items()
        },
    }


def test_the_waiting_step_names_the_waiting_elements_top_three_by_blocked_time():
    (finding,) = [
        f for f in _plane2_findings(SimpleNamespace(plane2_report=_waiting_report())) if f["id"] == "jobs-waiting"
    ]
    assert re.findall(r"(\S+) \(", finding["step"]["text"]) == ["make", "sh", "ld"], finding["step"]


def test_the_waiting_step_says_its_figures_are_the_waiting_elements_own():
    """Round 165's walk: the step's blocked figures sum the waiting elements only, while by_binary's Blocked
    column sums the run - so the step names its scope, and make reads w1+w2's 50 s, not the run's 550 s."""
    report = _waiting_report()
    report["binary_cost"]["busy.bst"]["binaries"].append(
        {"binary": "make", "count": 1, "cpu_us": 1, "wall_s": 1.0, "blocked_us": 500_000_000}
    )
    (finding,) = [f for f in _plane2_findings(SimpleNamespace(plane2_report=report)) if f["id"] == "jobs-waiting"]
    text = finding["step"]["text"]
    assert f"make ({shown.duration(50_000_000)})" in text, text
    assert "across these 2 waiting elements" in text, text


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
