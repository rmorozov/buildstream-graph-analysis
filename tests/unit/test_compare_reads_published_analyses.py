"""UX-1073: `compare` reads each side's published analysis when it is current.

A two-snapshot store of golden-run copies, each published by the
snapshot tail's own `_analyze`. The comparison read from the two
`analyze.json` files is byte-identical to `--reanalyse`, costs 0
`analyze` calls against 2, and every fingerprint term has a case that
changes only it and falls back.
"""

import contextlib
import io
import json
import os
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import producer
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.cli import main
from tools import bga_snapshot, bga_view

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"


def _plane2(wait_us):
    """A Plane 2 report whose admission wait moves `lib.bst`'s BUILD."""
    ledger = [{"event": "admission_wait", "element": "lib.bst", "wait_us": wait_us}]
    return {"jobserver_ledger": ledger if wait_us else [], "by_element": {"base.bst": 1, "lib.bst": 1}}


@pytest.fixture
def store(tmp_path):
    """`{side: snapshot}`, each with `run/`, `plane2.json`, `analyze.json`."""
    snapshots = {}
    for side, wait_us in (("baseline", 0), ("candidate", 1000)):
        snapshot = tmp_path / ".bga/runs" / side
        shutil.copytree(GOLDEN, snapshot / "run")
        (snapshot / "plane2.json").write_text(json.dumps(_plane2(wait_us)))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            bga_snapshot._analyze(
                str(snapshot / "run"), str(snapshot / "plane2.json"), publish_to=str(snapshot / "analyze.json")
            )
        snapshots[side] = snapshot
    return snapshots


@pytest.fixture
def analyze_calls(monkeypatch):
    """How many times `BuildEfficiencyAnalyzer.analyze` ran."""
    calls = []
    original = BuildEfficiencyAnalyzer.analyze

    def counted(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(BuildEfficiencyAnalyzer, "analyze", counted)
    return calls


def _compare(store, tmp_path, analyze_calls, *extra, candidate_plane2=None):
    """`(compare JSON text, analyze calls)` for the store's pair, as the tail runs it."""
    out = tmp_path / "compare.json"
    before = len(analyze_calls)
    argv = [
        "compare",
        str(store["baseline"] / "run"),
        str(store["candidate"] / "run"),
        "--baseline-plane2",
        str(store["baseline"] / "plane2.json"),
        "--candidate-plane2",
        str(candidate_plane2 or store["candidate"] / "plane2.json"),
        "--format",
        "json",
        "--output",
        str(out),
        *extra,
    ]
    with contextlib.redirect_stderr(io.StringIO()):
        main(argv)
    return out.read_text(encoding="utf-8"), len(analyze_calls) - before


class TestComparisonReadsThePublishedAnalyses:
    def test_the_published_comparison_is_the_reanalysed_one_byte_for_byte(self, store, tmp_path, analyze_calls):
        published, reads = _compare(store, tmp_path, analyze_calls)
        fresh, analyses = _compare(store, tmp_path, analyze_calls, "--reanalyse")
        assert (reads, analyses) == (0, 2)
        assert published == fresh
        assert json.loads(published)["deltas"]["lb"] == -1000, (
            "the candidate's admission wait must move the pair, or equal "
            "outputs prove nothing about which side was read"
        )

    def test_neither_published_analyzes_both(self, store, tmp_path, analyze_calls):
        published, _ = _compare(store, tmp_path, analyze_calls)
        for snapshot in store.values():
            (snapshot / "analyze.json").unlink()
        fresh, analyses = _compare(store, tmp_path, analyze_calls)
        assert analyses == 2
        assert fresh == published


class TestEachFingerprintTermFallsBack:
    def test_a_bumped_analyzer_version(self, store, tmp_path, analyze_calls, monkeypatch):
        monkeypatch.setattr(producer, "__version__", "999.0.0")
        assert _compare(store, tmp_path, analyze_calls)[1] == 2

    def test_a_changed_capacity(self, store, tmp_path, analyze_calls):
        assert _compare(store, tmp_path, analyze_calls, "--capacity", "3")[1] == 2

    def test_a_different_plane2_report_on_one_side(self, store, tmp_path, analyze_calls):
        other = tmp_path / "other-plane2.json"
        other.write_text(json.dumps(_plane2(2000)))
        assert _compare(store, tmp_path, analyze_calls, candidate_plane2=other)[1] == 1

    def test_a_changed_run_directory_input(self, store, tmp_path, analyze_calls):
        trace = store["candidate"] / "run" / "trace.json"
        trace.write_text(trace.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        assert _compare(store, tmp_path, analyze_calls)[1] == 1

    def test_a_changed_file_beside_the_run(self, store, tmp_path, analyze_calls):
        (store["candidate"] / "plane2.log.gz").write_bytes(b"")
        assert _compare(store, tmp_path, analyze_calls)[1] == 1

    def test_a_sibling_rewritten_at_the_same_size_and_mtime(self, store, tmp_path, analyze_calls):
        """`plane2.absence()` reads the sibling's `process_count` when the
        raw log is there; a rewrite that keeps size and forges mtime back
        changes `plane2_absence`, so the sibling's content is the term."""
        snapshot = store["candidate"]
        attached = tmp_path / "attached-plane2.json"
        attached.write_text(json.dumps(_plane2(1000)))
        sibling = snapshot / "plane2.json"
        sibling.write_text(json.dumps({"process_count": 1}))
        (snapshot / "plane2.log.gz").write_bytes(b"")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            bga_snapshot._analyze(str(snapshot / "run"), str(attached), publish_to=str(snapshot / "analyze.json"))
        assert _compare(store, tmp_path, analyze_calls, candidate_plane2=attached)[1] == 0
        before = sibling.stat()
        sibling.write_text(json.dumps({"process_count": 0}))
        os.utime(sibling, ns=(before.st_atime_ns, before.st_mtime_ns))
        assert sibling.stat().st_size == before.st_size
        assert _compare(store, tmp_path, analyze_calls, candidate_plane2=attached)[1] == 1

    def test_an_unclassified_option_is_never_reusable(self, store):
        from bga import fingerprint
        from bga.cli import create_parser

        args = create_parser().parse_args(["analyze", str(store["candidate"] / "run")])
        dests = fingerprint.analyze_dests()
        assert fingerprint.of(args, dests) is not None, "every option `bga analyze` parses today is classified"
        assert fingerprint.of(args, dests + ["a_new_option"]) is None

    def test_bga_view_reanalyse_reaches_the_comparison(self, store, analyze_calls):
        run = str(store["candidate"] / "run")
        baseline = str(store["baseline"] / "run")
        with contextlib.redirect_stderr(io.StringIO()):
            served = bga_view.payloads(run, baseline)
            reads = len(analyze_calls)
            bga_view.payloads(run, baseline, reanalyse=True)
        assert "compare.json" in served
        assert (reads, len(analyze_calls) - reads) == (0, 3), (
            "--reanalyse is the page's analysis and both sides of the comparison"
        )
