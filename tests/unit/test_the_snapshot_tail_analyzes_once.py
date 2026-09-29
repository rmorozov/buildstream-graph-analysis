"""UX-1072: the snapshot tail's `_analyze` + `write_element_slice`
analyze the run once, not twice - 18.62s at 5,002 elements was a
second full pass over the same run (the audit).
"""

import os
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")


def _make_snapshot(tmp_path, name):
    snap = tmp_path / name
    snap.mkdir()
    run_dir = snap / "run"
    shutil.copytree(GOLDEN, run_dir)
    os.remove(run_dir / "expected_output.json")
    return snap, run_dir


def test_the_tail_analyzes_the_run_once(tmp_path, monkeypatch):
    from bga.analyzer import BuildEfficiencyAnalyzer
    from tools.bga_snapshot import _analyze, write_element_slice

    snap, run_dir = _make_snapshot(tmp_path, "snap")
    calls = []
    real_analyze = BuildEfficiencyAnalyzer.analyze

    def counting_analyze(self, *a, **k):
        calls.append(1)
        return real_analyze(self, *a, **k)

    monkeypatch.setattr(BuildEfficiencyAnalyzer, "analyze", counting_analyze)

    publish_to = str(snap / "analysis.json")
    _, analyzed_result = _analyze(str(run_dir), str(snap / "plane2.json"), publish_to=publish_to)
    written = write_element_slice(str(snap), str(run_dir), analysis_result=analyzed_result)

    assert len(calls) == 1, (
        f"expected exactly 1 BuildEfficiencyAnalyzer.analyze() call across "
        f"_analyze + write_element_slice, got {len(calls)}"
    )
    assert written is not None


def test_the_reused_slice_is_byte_identical_to_a_fresh_analysis(tmp_path):
    """The slice from `_analyze`'s reused result is what a from-scratch
    `section='graph'` analysis on the same run would have written."""
    from tools.bga_snapshot import SLICE_NAME, _analyze, write_element_slice

    reused_snap, reused_run = _make_snapshot(tmp_path, "reused")
    fresh_snap, fresh_run = _make_snapshot(tmp_path, "fresh")

    _, analyzed_result = _analyze(
        str(reused_run), str(reused_snap / "plane2.json"), publish_to=str(reused_snap / "analysis.json")
    )
    write_element_slice(str(reused_snap), str(reused_run), analysis_result=analyzed_result)
    write_element_slice(str(fresh_snap), str(fresh_run))  # no reuse: old path

    reused_bytes = (reused_snap / SLICE_NAME).read_bytes()
    fresh_bytes = (fresh_snap / SLICE_NAME).read_bytes()
    assert reused_bytes == fresh_bytes
