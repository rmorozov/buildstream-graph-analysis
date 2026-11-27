"""UX-1389: a stored analysis that saw no Plane 2 is not served once one sits beside the run.

The terminal's "Plane 2 was captured - its report is beside this run" and the
page's "Plane 2 was not captured" came from two sources: the filesystem and a
stored `analyze.json` written before `plane2.json` arrived.
"""

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2
from tools import bga_view as view

FIXTURE = REPO / "tests/fixtures/macro_micro"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _scratch(tmp_path, stored_with_plane2):
    """The fixture's `run` with a stored analysis made with or without the sibling report."""
    shutil.copytree(FIXTURE / "run", tmp_path / "run")
    if stored_with_plane2:
        shutil.copy(FIXTURE / "plane2.json", tmp_path / "plane2.json")
    stored = view.payloads(str(tmp_path / "run"))["report.json"]
    (tmp_path / "analyze.json").write_text(json.dumps(stored), encoding="utf-8")
    shutil.copy(FIXTURE / "plane2.json", tmp_path / "plane2.json")
    return str(tmp_path / "run")


def test_a_stored_analysis_without_plane_2_is_reanalysed_beside_a_report(tmp_path):
    run = _scratch(tmp_path, stored_with_plane2=False)
    assert json.loads((tmp_path / "analyze.json").read_text()).get("plane2_absence") == plane2.NOT_CAPTURED
    assert plane2.attachable(run)[0]
    report = view.payloads(run)["report.json"]
    assert report.get("plane2_coverage"), report.get("plane2_absence")
    assert view.analysis_note(run)["source"] == view.ANALYSIS_FROM_VIEW


def test_a_stored_analysis_that_saw_plane_2_is_still_served(tmp_path):
    run = _scratch(tmp_path, stored_with_plane2=True)
    assert json.loads((tmp_path / "analyze.json").read_text()).get("plane2_absence") != plane2.NOT_CAPTURED
    assert view.analysis_note(run)["source"] == view.ANALYSIS_FROM_CAPTURE


def test_a_stored_analysis_that_joined_an_explicit_report_is_kept(tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    shutil.copy(FIXTURE / "plane2.json", outside / "report.json")
    snap = tmp_path / "snap"
    shutil.copytree(FIXTURE / "run", snap / "run")
    run = str(snap / "run")
    stored = view._capture(["analyze", run, "--format", "json", "--plane2", str(outside / "report.json")])
    assert stored.get("plane2_coverage") and stored.get("plane2_absence") == plane2.NOT_CAPTURED
    (snap / "analyze.json").write_text(json.dumps(stored), encoding="utf-8")
    (snap / "plane2.json").write_text(json.dumps({"schema": plane2.SCHEMA, "process_count": 0}), encoding="utf-8")
    assert plane2.attachable(run)[0]
    assert view.payloads(run)["report.json"].get("plane2_coverage")
    assert view.analysis_note(run)["source"] == view.ANALYSIS_FROM_CAPTURE


def test_a_report_over_the_size_bound_is_named_not_called_absent(tmp_path):
    run = _scratch(tmp_path, stored_with_plane2=False)
    pad = plane2.VIEW_MAX_BYTES + 1 - (tmp_path / "plane2.json").stat().st_size
    with open(tmp_path / "plane2.json", "ab") as handle:
        handle.write(b" " * pad)
    path, refusal = plane2.attachable(run, stored=True)
    assert path is None and refusal
    report = view.payloads(run)["report.json"]
    assert report["plane2_absence"] == refusal != plane2.NOT_CAPTURED
    assert "stored analysis was made without it" in refusal and "published no" not in refusal
    assert not report.get("plane2_coverage")
    assert view.analysis_note(run)["source"] == view.ANALYSIS_FROM_CAPTURE


def test_a_stored_analysis_that_joined_a_report_without_coverage_is_kept(tmp_path):
    report = json.loads((FIXTURE / "plane2.json").read_text(encoding="utf-8"))
    del report["stream_coverage"]
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "report.json").write_text(json.dumps(report), encoding="utf-8")
    snap = tmp_path / "snap"
    shutil.copytree(FIXTURE / "run", snap / "run")
    run = str(snap / "run")
    stored = view._capture(["analyze", run, "--format", "json", "--plane2", str(tmp_path / "elsewhere/report.json")])
    assert stored.get("capacity_recommendation") and not stored.get("plane2_coverage")
    assert stored.get("plane2_absence") == plane2.NOT_CAPTURED
    (snap / "analyze.json").write_text(json.dumps(stored), encoding="utf-8")
    (snap / "plane2.json").write_text(json.dumps({"schema": plane2.SCHEMA, "process_count": 0}), encoding="utf-8")
    assert plane2.attachable(run)[0]
    assert view.payloads(run)["report.json"].get("capacity_recommendation")
    assert view.analysis_note(run)["source"] == view.ANALYSIS_FROM_CAPTURE


_STATUS = """
const app = await import("./tests/viewer.mjs");
process.stdout.write(JSON.stringify(app.statusLine(JSON.parse(process.argv[1]))));
"""


def _status(payload):
    done = subprocess.run(
        [node, "--input-type=module", "-e", _STATUS, json.dumps(payload)],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


def _pad_past_the_bound(tmp_path):
    pad = plane2.VIEW_MAX_BYTES + 1 - (tmp_path / "plane2.json").stat().st_size
    with open(tmp_path / "plane2.json", "ab") as handle:
        handle.write(b" " * pad)


def _exported_page(tmp_path):
    out = tmp_path / "e.html"
    view.export(str(tmp_path / "run"), str(out), with_trace=False)
    return out.read_text(encoding="utf-8")


@needs_node
def test_the_status_line_says_the_report_is_too_large_not_that_it_is_not_captured(tmp_path):
    run = _scratch(tmp_path, stored_with_plane2=False)
    _pad_past_the_bound(tmp_path)
    line = _status(view.payloads(run)["report.json"])
    assert line.endswith("Plane 2 too large to join here"), line
    assert "not captured" not in line


def test_the_exported_page_says_the_report_is_too_large_in_the_sizing_sentence(tmp_path):
    _scratch(tmp_path, stored_with_plane2=False)
    _pad_past_the_bound(tmp_path)
    page = _exported_page(tmp_path)
    assert "Cores and memory need Plane 2, which is too large to join here." in page
    assert "did not capture" not in page


def _declined_run(tmp_path):
    """A stored `--no-plane2` analysis made while the sibling existed."""
    shutil.copytree(FIXTURE / "run", tmp_path / "run")
    shutil.copy(FIXTURE / "plane2.json", tmp_path / "plane2.json")
    stored = view._capture(["analyze", str(tmp_path / "run"), "--format", "json", "--no-plane2"])
    assert stored["plane2_absence"] == plane2.DECLINED
    (tmp_path / "analyze.json").write_text(json.dumps(stored), encoding="utf-8")
    return str(tmp_path / "run")


@needs_node
def test_the_status_line_says_a_declined_report_was_not_read_not_that_it_is_not_captured(tmp_path):
    line = _status(view.payloads(_declined_run(tmp_path))["report.json"])
    assert line.endswith("Plane 2 not read (--no-plane2)"), line
    assert "not captured" not in line


def test_the_exported_page_says_a_declined_report_was_not_read_in_the_sizing_sentence(tmp_path):
    _declined_run(tmp_path)
    page = _exported_page(tmp_path)
    assert "Cores and memory need Plane 2, which this report was asked not to read." in page
    assert "did not capture" not in page
