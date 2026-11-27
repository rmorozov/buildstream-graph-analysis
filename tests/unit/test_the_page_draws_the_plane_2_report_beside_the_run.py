"""UX-1389: a stored analysis that saw no Plane 2 is not served once one sits beside the run.

The terminal's "Plane 2 was captured - its report is beside this run" and the
page's "Plane 2 was not captured" came from two sources: the filesystem and a
stored `analyze.json` written before `plane2.json` arrived.
"""

import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2
from tools import bga_view as view

FIXTURE = REPO / "tests/fixtures/macro_micro"


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
