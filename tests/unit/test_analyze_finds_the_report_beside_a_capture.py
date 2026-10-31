"""UX-1365: a published capture is `run/` next to `native-report.json`; analyze names it.

Page: styleguide §1b, a published field reaches a reader.
"""

import contextlib
import io
import json
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import Browser, find_chrome

FIXTURE = REPO / "tests/fixtures/macro_micro"
chrome = find_chrome()
NO_CHROME = "no chrome/chromium for the geometry guards (set BGA_CHROME)"


def _analyze(run, *extra):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run), *extra])
    return buffer.getvalue()


def _published(tmp_path, where):
    """`where` is the folder that holds native-report.json, relative to the run dir."""
    top = tmp_path / "capture"
    shutil.copytree(FIXTURE / "run", top / "run")
    target = (top / "run" / where).resolve()
    shutil.copy(FIXTURE / "plane2.json", target / "native-report.json")
    return top / "run", target / "native-report.json"


@pytest.mark.parametrize("where", [".", "..", "../.."])
def test_the_report_is_named_with_the_correlate_command(tmp_path, where):
    run, report = _published(tmp_path, where)
    text = _analyze(run)
    assert "was not captured" not in text
    assert f"`bga correlate {run} {report}`" in text
    assert json.loads(_analyze(run, "--format", "json"))["plane2_absence"].count(str(report)) == 2


def test_no_report_anywhere_still_says_not_captured(tmp_path):
    shutil.copytree(FIXTURE / "run", tmp_path / "capture" / "run")
    assert "Plane 2 was not captured" in _analyze(tmp_path / "capture" / "run")


@pytest.mark.skipif(chrome is None, reason=NO_CHROME)
@pytest.mark.medium
def test_the_page_names_the_report_too(tmp_path):
    run, report = _published(tmp_path, "..")
    uri = pages.export_uri(run, tmp_path / "out")
    look = "document.body.textContent.replace(/\\s+/g, ' ')"
    with Browser(chrome) as browser:
        text = browser.measure(uri, look, 1440, 900)
    # the export copies the capture, so the paths are the copy's
    assert re.search(
        r"Plane 2 not attached to this run: a report exists at \S+/native-report\.json; `bga correlate \S+/run ", text
    )
