"""UX-1255: where Plane 2 covers the run, its costliest binary, waiting elements and configure share are findings.

holds: the binary finding's CPU is `by_binary[0]`'s; the waiting finding's cores are the capacity verdict's;
a Plane 1-only run emits none of the three.
"""

import contextlib
import io
import json
from types import SimpleNamespace

import pytest

from bga.cli import main
from bga.findings import FINDING_READERS, PLANE2_CONFIGURE_SHARE, _plane2_findings
from tests import pages

PLANE2_IDS = {"costliest-binary", "jobs-waiting", "configure-share"}


def _analyze(run):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run), "--format", "json"])
    return json.loads(buffer.getvalue())


@pytest.fixture(scope="module")
def heavy(tmp_path_factory):
    return _analyze(pages.heavy_binary_run(tmp_path_factory.mktemp("plane2-findings")))


def _by_id(document):
    return {finding["id"]: finding for finding in document["findings"]}


def test_the_binary_finding_cites_by_binary_row_zero(heavy):
    finding = _by_id(heavy)["costliest-binary"]
    top = heavy["by_binary"][0]
    assert finding["evidence"]["cpu_us"] == top["cpu_us"], (finding, top)
    assert finding["evidence"]["binary"] == top["binary"]
    assert finding["section"] == "by_binary" and finding["step"]["text"]


def test_the_waiting_finding_cites_the_capacity_sections_cores(heavy):
    finding = _by_id(heavy)["jobs-waiting"]
    capacity = heavy["capacity_recommendation"]
    per = capacity["cores_busy"] / capacity["builders"]
    assert finding["evidence"]["cores_per_element"] == round(per, 2)
    assert finding["title"].startswith(f"{per:.2f} cores")
    assert f"{per:.2f} cores" in capacity["verdict"], capacity["verdict"]


def test_a_graph_knee_below_the_builders_emits_no_waiting_finding(tmp_path):
    document = _analyze(pages.snapshot_copy(pages.FIXTURES["macro_micro"], tmp_path))
    capacity = document["capacity_recommendation"]
    knee = next(c["allows"] for c in capacity["constraints"] if c["name"] == "graph")
    assert knee < capacity["builders"], capacity["verdict"]
    assert "jobs-waiting" not in _by_id(document)


@pytest.mark.parametrize("share, fires", [(PLANE2_CONFIGURE_SHARE, True), (0.064, False)])
def test_configure_is_a_finding_from_its_line(share, fires):
    phase = {"available": True, "configure_share": share, "configure_cpu_us": 4_000_000}
    found = _plane2_findings(SimpleNamespace(plane2_report={"configure_phase": phase}))
    assert [f["id"] for f in found] == (["configure-share"] if fires else [])
    if fires:
        assert found[0]["section"] == "configure_phase" and found[0]["title"].startswith("10.0% of CPU")


def test_every_plane2_finding_has_a_reader():
    assert set(FINDING_READERS) >= PLANE2_IDS


def test_a_plane1_only_run_emits_none():
    document = _analyze(pages.FIXTURES["golden"])
    assert not PLANE2_IDS & set(_by_id(document)), sorted(_by_id(document))
