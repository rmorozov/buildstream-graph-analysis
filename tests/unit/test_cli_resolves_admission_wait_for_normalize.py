"""UX-1005 track C: `bga.cli._resolve_admission_wait` is the bridge
between a Plane 2 report's `jobserver_ledger` and `Analyzer.normalize`,
resolved ahead of `analyze()` so the wait can leave the BUILD span
(`bga/normalize/timestamps.py::normalize_trace`) rather than reach the
page unadjusted."""
import argparse
import json

from bga.cli import _resolve_admission_wait


def _args(**overrides):
    base = {"plane2": None, "no_plane2": False, "directory": None}
    base.update(overrides)
    return argparse.Namespace(**base)


def test_reads_the_admission_wait_off_an_explicit_plane2_report(tmp_path):
    report = tmp_path / "plane2.json"
    report.write_text(json.dumps({
        "jobserver_ledger": [
            {"event": "admission_wait", "element": "a.bst", "wait_us": 300},
            {"event": "admission_wait", "element": "a.bst", "wait_us": 100},
        ],
    }))

    result = _resolve_admission_wait(_args(plane2=str(report)))

    assert result == {"a.bst": 400}


def test_no_plane2_report_is_a_no_op():
    assert _resolve_admission_wait(_args()) == {}


def test_no_plane2_declined_is_a_no_op(tmp_path):
    report = tmp_path / "plane2.json"
    report.write_text(json.dumps({"jobserver_ledger": [
        {"event": "admission_wait", "element": "a.bst", "wait_us": 300}]}))

    assert _resolve_admission_wait(_args(plane2=str(report), no_plane2=True)) == {}


def test_a_report_with_no_admission_rows_is_empty(tmp_path):
    report = tmp_path / "plane2.json"
    report.write_text(json.dumps({"jobserver_ledger": []}))

    assert _resolve_admission_wait(_args(plane2=str(report))) == {}
