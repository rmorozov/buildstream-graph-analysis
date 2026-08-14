"""Tests for tools/bst_extract_run.py (P4-10): coordinates trace + graph +
run-context extraction into one bga-ready run directory from a single
real BuildStream project + log.

Two layers, matching tests/unit/test_bst_show_to_graph.py's convention:
1. Pure unit tests against the coordinator's own helper functions -
   fast, hermetic, always run.
2. A real end-to-end test that actually shells out to a real `bst`
   binary against tests/fixtures/bst_show_project/, capturing a fresh
   real log itself (not a checked-in sample) - skipped whenever `bst`
   isn't on PATH.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.bst_extract_run import _git_consistency_note, _parse_targets, extract_run

FIXTURE_PROJECT = Path(__file__).resolve().parents[1] / "fixtures" / "bst_show_project"

BST_AVAILABLE = shutil.which("bst") is not None


# --- Pure unit tests -----------------------------------------------------

def test_parse_targets_single():
    assert _parse_targets("app.bst") == ["app.bst"]


def test_parse_targets_multiple_comma_separated():
    """Real BuildStream header format: "Targets:       base.bst, base2.bst" """
    assert _parse_targets("base.bst, base2.bst") == ["base.bst", "base2.bst"]


def test_git_consistency_note_none_for_non_git_directory(tmp_path):
    assert _git_consistency_note(str(tmp_path)) is None


def test_git_consistency_note_none_for_clean_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("hi")
    subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

    assert _git_consistency_note(str(tmp_path)) is None


def test_git_consistency_note_warns_for_dirty_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("hi")
    subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("changed")

    note = _git_consistency_note(str(tmp_path))
    assert note is not None
    assert "uncommitted changes" in note


def test_extract_run_fails_loudly_without_a_targets_line(tmp_path):
    """Refuses to guess a target list from a hardcoded convention when
    the log doesn't carry BuildStream's own real "Targets:" line."""
    log = tmp_path / "no_targets.log"
    log.write_text("nothing resembling a buildstream log here\n")

    with pytest.raises(RuntimeError, match="Targets"):
        extract_run(str(FIXTURE_PROJECT), str(log), str(tmp_path / "out"),
                    log_format="raw", start_time="2026-08-14T00:00:00+00:00")


# --- Real end-to-end test --------------------------------------------------

@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_real_end_to_end_extraction_produces_a_complete_bga_ready_run(tmp_path):
    log_path = tmp_path / "real_build.log"

    proc = subprocess.run(
        ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "app.bst"],
        capture_output=True, text=True,
        env={"HOME": str(tmp_path), "PATH": __import__("os").environ["PATH"]},
    )
    log_path.write_text(proc.stdout + proc.stderr)

    out_dir = tmp_path / "run"
    summary = extract_run(str(FIXTURE_PROJECT), str(log_path), str(out_dir), log_format="auto")

    assert summary["targets"] == ["app.bst"]
    assert summary["elements"] == 4
    assert summary["dependencies"] == 3
    assert summary["spans"] > 0

    graph = json.loads((out_dir / "graph.json").read_text())
    trace = json.loads((out_dir / "trace.json").read_text())
    run_context = json.loads((out_dir / "run-context.json").read_text())

    assert {e["uid"] for e in graph["elements"]} == {
        "base.bst", "base2.bst", "subproj-junction.bst:libfoo.bst", "app.bst",
    }
    assert any(e["uid"] == "app.bst" and e["requested_target"] for e in graph["elements"])
    assert len(trace["spans"]) > 0
    assert run_context["resource_capacities"]["PROCESS"] > 0

    # The whole point: zero manual editing before bga can consume it.
    from bga import analyze_run
    result = analyze_run(out_dir)
    assert result is not None


@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_different_target_lists_produce_different_requested_targets(tmp_path):
    """Acceptance test (P4-10's own): using a *different* target list on
    two separate real builds produces two different, each-individually-
    correct requested_target sets - proving target derivation isn't
    hardcoded to a fixed convention."""
    import os

    def _build_and_extract(targets, out_name):
        log_path = tmp_path / f"{out_name}.log"
        proc = subprocess.run(
            ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build"] + targets,
            capture_output=True, text=True,
            env={"HOME": str(tmp_path), "PATH": os.environ["PATH"]},
        )
        log_path.write_text(proc.stdout + proc.stderr)
        out_dir = tmp_path / out_name
        summary = extract_run(str(FIXTURE_PROJECT), str(log_path), str(out_dir), log_format="auto")
        graph = json.loads((out_dir / "graph.json").read_text())
        requested = {e["uid"] for e in graph["elements"] if e["requested_target"]}
        return summary["targets"], requested

    targets_a, requested_a = _build_and_extract(["base.bst"], "run_a")
    targets_b, requested_b = _build_and_extract(["base2.bst"], "run_b")

    assert targets_a == ["base.bst"]
    assert requested_a == {"base.bst"}
    assert targets_b == ["base2.bst"]
    assert requested_b == {"base2.bst"}
    assert requested_a != requested_b
