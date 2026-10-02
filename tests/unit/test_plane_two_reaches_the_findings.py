"""UX-1255: where Plane 2 covers the run, its costliest binary, waiting elements and configure share are findings.

holds: the binary finding's CPU is `by_binary[0]`'s; the waiting finding counts the `element_join` rows under
correlate's compute-bound line, with their median; a Plane 1-only run emits none of the three.
"""

import contextlib
import io
import json
import statistics
from types import SimpleNamespace

import pytest

from bga.cli import main
from bga.correlate import _COMPUTE_BOUND_CORES
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


def _waiting_rows(document):
    """`element_join` rows that asked for parallel jobs and ran under correlate's compute-bound line."""
    return [
        row
        for row in document["element_join"]
        if (row.get("requested_jobs") or 0) > 1
        and row.get("cores_busy") is not None
        and row["cores_busy"] < _COMPUTE_BOUND_CORES
    ]


def test_the_waiting_finding_counts_the_join_rows_and_their_median(heavy):
    finding = _by_id(heavy)["jobs-waiting"]
    rows = _waiting_rows(heavy)
    median = statistics.median(row["cores_busy"] for row in rows)
    assert finding["evidence"]["element_count"] == len(rows) > 0
    assert finding["evidence"]["median_cores_busy"] == round(median, 2)
    assert (
        finding["title"].startswith(f"{len(rows):,} elements asked for 4 jobs")
        and f"{median:.2f} cores" in finding["title"]
    )
    assert finding["section"] == "element_join"


def _report(*elements):
    """A Plane 2 report of `(uid, requested_jobs, cores_busy)` elements, one second of wall each."""
    return {
        "per_element_parallelism": [{"element": uid, "requested_jobs": jobs} for uid, jobs, _c in elements],
        "cpu_time": {
            "per_element": {
                uid: {"cpu_per_wall_second": cores, "wall_span_s": 1.0, "cpu_us": int(cores * 1e6)}
                for uid, _j, cores in elements
            }
        },
    }


def test_the_line_is_correlates_and_a_one_job_element_is_not_waiting():
    report = _report(
        ("under.bst", 4, _COMPUTE_BOUND_CORES - 0.01), ("at.bst", 4, _COMPUTE_BOUND_CORES), ("pinned.bst", 1, 0.5)
    )
    found = _plane2_findings(SimpleNamespace(plane2_report=report))
    assert [(f["id"], f["evidence"]["element_count"]) for f in found] == [("jobs-waiting", 1)]


def test_macro_micro_has_no_waiting_element(tmp_path):
    document = _analyze(pages.snapshot_copy(pages.FIXTURES["macro_micro"], tmp_path))
    assert _waiting_rows(document) == []
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
