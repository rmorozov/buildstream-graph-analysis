"""UX-1366 (b): a flag on every traced element is one finding; requested_jobs stays the observed request."""

import contextlib
import io
import json
import pathlib
import shutil
import sys
from types import SimpleNamespace

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import findings
from bga.cli import main
from bga.plane2 import OVERLAP_FINDING, apply_resolved_widths, run_wide_findings

FIXTURE = REPO / "tests/fixtures/macro_micro"
ID = "native-finding-on-every-element"


def _entry(name, requested, peak=8, findings_=()):
    return {
        "element": name,
        "requested_jobs": requested,
        "peak_work_concurrency": peak,
        "findings": list(findings_),
    }


def _applied(entries, widths):
    report = {"per_element_parallelism": entries}
    apply_resolved_widths(report, widths)
    return report


def test_the_granted_width_is_resolved_jobs_and_never_rewrites_the_request():
    """`make -j1 install` beside a `make` that inherits `--max-jobs 4`: 1 requested, 4 resolved."""
    report = _applied(
        [_entry("a.bst", 1), _entry("pinned.bst", 1), _entry("wide.bst", 2), _entry("none.bst", None)],
        {"a.bst": 4, "pinned.bst": 1, "wide.bst": 8, "none.bst": 4},
    )
    got = {e["element"]: (e["requested_jobs"], e["resolved_jobs"]) for e in report["per_element_parallelism"]}
    assert got == {"a.bst": (1, 4), "pinned.bst": (1, 1), "wide.bst": (2, 8), "none.bst": (None, 4)}


def test_a_finding_every_traced_element_carries_is_summarised():
    report = _applied([_entry(f"e{i}.bst", 1) for i in range(3)], {f"e{i}.bst": 4 for i in range(3)})
    entries = report["per_element_parallelism"]
    assert run_wide_findings(entries) == {OVERLAP_FINDING: 3}
    entries[1]["findings"].remove(OVERLAP_FINDING)
    assert run_wide_findings(entries) == {}
    assert run_wide_findings(entries[:1]) == {}


def test_an_element_that_ran_no_work_is_not_traced():
    report = _applied(
        [_entry("a.bst", 1), _entry("b.bst", 1), _entry("idle.bst", None, peak=0)],
        {"a.bst": 4, "b.bst": 4, "idle.bst": 4},
    )
    assert run_wide_findings(report["per_element_parallelism"]) == {OVERLAP_FINDING: 2}


def _said(entries):
    return [
        f
        for f in findings._plane2_findings(SimpleNamespace(plane2_report={"per_element_parallelism": entries}))
        if f["id"] == ID
    ]


def test_the_finding_is_one_card_and_carries_the_ids():
    report = _applied([_entry(f"e{i}.bst", 1) for i in range(3)], {f"e{i}.bst": 4 for i in range(3)})
    (card,) = _said(report["per_element_parallelism"])
    assert card["title"].startswith("3 of 3 traced elements") and OVERLAP_FINDING in card["title"]
    assert card["evidence"]["finding_ids"] == [OVERLAP_FINDING]
    report["per_element_parallelism"][0]["findings"].remove(OVERLAP_FINDING)
    assert _said(report["per_element_parallelism"]) == []


def _analysed(tmp_path, peaks):
    """macro_micro with Plane 2's per-element peak work concurrency set to `peaks[i]`, as `analyze` publishes it."""
    snap = tmp_path / "snap"
    shutil.copytree(FIXTURE / "run", snap / "run")
    report = json.loads((FIXTURE / "plane2.json").read_text())
    for entry, peak in zip(report["per_element_parallelism"], peaks, strict=False):
        entry["peak_work_concurrency"] = peak
    (snap / "plane2.json").write_text(json.dumps(report))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(snap / "run"), "--format", "json"])
    return json.loads(buffer.getvalue())


def test_the_published_rows_do_not_repeat_what_the_finding_says(tmp_path):
    data = _analysed(tmp_path, [99] * 9)
    (card,) = [f for f in data["findings"] if f["id"] == ID]
    assert OVERLAP_FINDING in card["evidence"]["finding_ids"]
    rows = [row for row in data["element_join"] if row.get("jobs_denominator")]
    assert rows and all(OVERLAP_FINDING not in row["native_findings"] for row in rows)


def test_a_finding_on_only_some_elements_stays_on_its_rows(tmp_path):
    data = _analysed(tmp_path, [99, 1, 1, 1, 1, 1, 1, 1, 1])
    assert not [f for f in data["findings"] if f["id"] == ID]
    assert any(OVERLAP_FINDING in row["native_findings"] for row in data["element_join"])
