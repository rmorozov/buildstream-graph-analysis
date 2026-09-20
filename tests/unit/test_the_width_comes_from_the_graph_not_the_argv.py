"""UX-894: an element is scored against the width it was granted.

`requested_jobs` is `-j(\\d+)` matched against the argv of `make`,
`gmake` and `ninja`, highest wins. The denominator is a per-invocation
flag, so the published ratio could exceed 1.0 on an element BuildStream
declared `notparallel`: `core.bst` on `tests/fixtures/macro_micro` is
`notparallel`, ran two overlapping work processes, and scored 2.0
against a width of one.

The element's resolved `max-jobs` was in the same snapshot the whole
time - `UX-377` put it in `graph.json` per element, because
`--max-jobs` reaches a command line on exactly one of its three routes.
"""
import json
import subprocess
import sys
from pathlib import Path

from bga.plane2 import (
    GRAPH_DENOMINATOR,
    OVERLAP_FINDING,
    apply_resolved_widths,
    resolved_widths,
)

FIXTURE = Path("tests/fixtures/macro_micro")


def _disagreeing(tmp_path):
    """The case `tests/fixtures/macro_micro` cannot make: an element
    resolved to 8 whose recipe writes `make -j2`. Every element of that
    fixture agrees, which is why the regex survived."""
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"elements": [
        {"uid": "wide.bst", "max_jobs": 8, "notparallel": None},
        {"uid": "pinned.bst", "max_jobs": 4, "notparallel": True},
        {"uid": "cmake.bst", "max_jobs": 4, "notparallel": None},
        {"uid": "unknown.bst", "max_jobs": None, "notparallel": None},
    ]}))
    report = {"per_element_parallelism": [
        # The recipe asked for two; BuildStream granted eight.
        {"element": "wide.bst", "requested_jobs": 2,
         "peak_work_concurrency": 4, "findings": []},
        # Declared `notparallel`, so a width of one whatever `max_jobs`
        # says - and it overlapped two processes anyway.
        {"element": "pinned.bst", "requested_jobs": 1,
         "peak_work_concurrency": 2, "findings": []},
        # Neither make nor ninja ran, so there is no recipe request at
        # all - and the ratio is still computed.
        {"element": "cmake.bst", "requested_jobs": None,
         "peak_work_concurrency": 2, "findings": []},
        # No resolved width: no ratio, rather than a ratio of one.
        {"element": "unknown.bst", "requested_jobs": 4,
         "peak_work_concurrency": 4, "findings": []},
    ]}
    apply_resolved_widths(report, resolved_widths(str(graph)))
    return {entry["element"]: entry
            for entry in report["per_element_parallelism"]}


def test_the_graph_wins_where_the_two_disagree(tmp_path):
    """Both numbers are published and the ratio says which it used."""
    wide = _disagreeing(tmp_path)["wide.bst"]

    assert wide["resolved_jobs"] == 8
    assert wide["requested_jobs"] == 2
    assert wide["jobs_denominator"] == GRAPH_DENOMINATOR
    assert wide["achieved_vs_requested"] == 4 / 8


def test_notparallel_is_a_width_of_one_and_not_a_missing_value(tmp_path):
    """And the overlap it was never granted is a finding, not a score."""
    pinned = _disagreeing(tmp_path)["pinned.bst"]

    assert pinned["resolved_jobs"] == 1
    assert pinned["achieved_vs_requested"] == 1.0
    assert OVERLAP_FINDING in pinned["findings"]


def test_no_resolved_width_is_no_ratio(tmp_path):
    """An element the graph cannot answer for scores nothing - the
    recipe's own `-j4` is not promoted into a width it was never
    granted."""
    unknown = _disagreeing(tmp_path)["unknown.bst"]

    assert unknown["requested_jobs"] == 4
    assert unknown["resolved_jobs"] is None
    assert unknown["jobs_denominator"] is None
    assert unknown["achieved_vs_requested"] is None


def test_an_element_running_neither_make_nor_ninja_still_scores(tmp_path):
    """The recipe request is absent; the ratio is not."""
    cmake = _disagreeing(tmp_path)["cmake.bst"]

    assert cmake["requested_jobs"] is None
    assert cmake["achieved_vs_requested"] == 2 / 4
    assert cmake["jobs_denominator"] == GRAPH_DENOMINATOR


def test_the_pinned_element_of_the_real_capture_is_no_longer_two(tmp_path):
    """`core.bst` end to end: `bga analyze` on the committed snapshot,
    through the read-time join the CLI applies."""
    out = tmp_path / "report.json"
    argv = ["analyze", str(FIXTURE / "run"), "--plane2",
            str(FIXTURE / "plane2.json"), "-f", "json", "-o", str(out)]
    proc = subprocess.run(
        [sys.executable, "-c",
         f"from bga.cli import main; raise SystemExit(main({argv!r}))"],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    rows = {row["element"]: row
            for row in json.loads(out.read_text())["element_join"]}

    core = rows["core.bst"]
    assert core["requested_jobs"] == 1 and core["resolved_jobs"] == 1
    assert core["jobs_denominator"] == GRAPH_DENOMINATOR
    assert OVERLAP_FINDING in core["native_findings"]
