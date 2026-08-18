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

from ._bst_env import isolated_bst_env

from tools.bst_extract_run import (
    _compute_run_identity,
    _git_consistency_note,
    _parse_targets,
    extract_run,
)
from tools._run_context_common import host_cpu_count as _host_cpu_count

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


# --- _compute_run_identity (P1-37) ---------------------------------------

def test_run_identity_is_deterministic_for_identical_inputs(tmp_path):
    scheduler = {"builders": 4, "fetchers": 10, "pushers": 4}
    a = _compute_run_identity(str(tmp_path), ["app.bst"], scheduler, None)
    b = _compute_run_identity(str(tmp_path), ["app.bst"], scheduler, None)
    assert a["manifest_hash"] == b["manifest_hash"]


def test_run_identity_changes_with_targets(tmp_path):
    scheduler = {"builders": 4, "fetchers": 10, "pushers": 4}
    a = _compute_run_identity(str(tmp_path), ["app.bst"], scheduler, None)
    b = _compute_run_identity(str(tmp_path), ["other.bst"], scheduler, None)
    assert a["manifest_hash"] != b["manifest_hash"]


def test_run_identity_target_order_does_not_matter(tmp_path):
    """Same real target set, different list order (e.g. a different `bst
    build` invocation order) - the manifest is about *what* was
    requested, not the order it appeared in the log."""
    scheduler = {"builders": 4, "fetchers": 10, "pushers": 4}
    a = _compute_run_identity(str(tmp_path), ["app.bst", "base.bst"], scheduler, None)
    b = _compute_run_identity(str(tmp_path), ["base.bst", "app.bst"], scheduler, None)
    assert a["manifest_hash"] == b["manifest_hash"]


def test_run_identity_changes_with_scheduler_config(tmp_path):
    a = _compute_run_identity(
        str(tmp_path), ["app.bst"], {"builders": 4, "fetchers": 10, "pushers": 4}, None,
    )
    b = _compute_run_identity(
        str(tmp_path), ["app.bst"], {"builders": 2, "fetchers": 10, "pushers": 4}, None,
    )
    assert a["manifest_hash"] != b["manifest_hash"]


def test_run_identity_changes_with_project_refs_provenance(tmp_path):
    scheduler = {"builders": 4, "fetchers": 10, "pushers": 4}
    a = _compute_run_identity(str(tmp_path), ["app.bst"], scheduler, None)
    b = _compute_run_identity(
        str(tmp_path), ["app.bst"], scheduler, {"path": "project.refs", "sha256": "deadbeef"},
    )
    assert a["manifest_hash"] != b["manifest_hash"]


def test_run_identity_changes_with_native_max_jobs(tmp_path):
    """UX-12: native_max_jobs affects real observed concurrency/scheduling
    the same way builders/fetchers/pushers already do - same precedent as
    test_run_identity_changes_with_scheduler_config above."""
    scheduler = {"builders": 4, "fetchers": 10, "pushers": 4}
    a = _compute_run_identity(str(tmp_path), ["app.bst"], scheduler, None, native_max_jobs=4)
    b = _compute_run_identity(str(tmp_path), ["app.bst"], scheduler, None, native_max_jobs=8)
    assert a["manifest_hash"] != b["manifest_hash"]


def test_run_identity_native_max_jobs_defaults_to_none(tmp_path):
    """Omitting native_max_jobs (the common case today - most captures
    won't have it) must not raise and must be reflected in the manifest
    as an explicit None, not silently absent."""
    scheduler = {"builders": 4, "fetchers": 10, "pushers": 4}
    identity = _compute_run_identity(str(tmp_path), ["app.bst"], scheduler, None)
    assert identity["scheduler"]["native_max_jobs"] is None


def test_run_identity_changes_with_project_identity_across_sibling_projects(tmp_path):
    """UX-07 regression guard, real reproduction case: two different
    BuildStream projects living as sibling directories under the *same*
    git commit, with the same target name and scheduler config (e.g. a
    baseline project and its `optimized/` variant), must not collide -
    project_git_commit alone can't distinguish them, since it's identical
    for both. Confirmed real before this fix: manifest_hash was identical
    for examples/04-critical-path-optimization vs. its own optimized/
    subdirectory."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(repo_root), check=True)
    project_a = repo_root / "baseline"
    project_b = repo_root / "baseline" / "optimized"
    project_a.mkdir()
    project_b.mkdir()

    scheduler = {"builders": 4, "fetchers": 10, "pushers": 4}
    a = _compute_run_identity(str(project_a), ["all.bst"], scheduler, None)
    b = _compute_run_identity(str(project_b), ["all.bst"], scheduler, None)

    assert a["manifest_hash"] != b["manifest_hash"]
    assert a["project_git_commit"] == b["project_git_commit"]  # same commit - the real collision cause
    assert a["project_identity"] != b["project_identity"]


def test_project_identity_is_relative_to_git_repo_root(tmp_path):
    """Portable across clones: two different checkouts of the same repo
    at the same relative project path must report the same
    project_identity, not an absolute-path value that would differ
    per-checkout for no real reason."""
    from tools.bst_extract_run import _project_identity

    repo_root = tmp_path / "repo"
    project_dir = repo_root / "sub" / "project"
    project_dir.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=str(repo_root), check=True)

    assert _project_identity(str(project_dir)) == "sub/project"


def test_project_identity_falls_back_to_absolute_path_outside_a_git_repo(tmp_path):
    """No git repo at all - _git_commit already returns None for this
    case; project_identity must still produce *something* real and
    distinguishing, not crash or silently return an empty value."""
    from tools.bst_extract_run import _project_identity

    project_dir = tmp_path / "no_git_here"
    project_dir.mkdir()

    assert _project_identity(str(project_dir)) == str(project_dir.resolve())


def test_host_cpu_count_returns_a_positive_int():
    """Real, best-effort host CPU core count (UX-12) - this test host
    genuinely has at least one core, so this is a real, not synthetic,
    assertion."""
    count = _host_cpu_count()
    assert isinstance(count, int)
    assert count >= 1


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

@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/spec/ingestion-pipeline.md")
def test_real_end_to_end_extraction_produces_a_complete_bga_ready_run(tmp_path):
    log_path = tmp_path / "real_build.log"

    proc = subprocess.run(
        ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "app.bst"],
        capture_output=True, text=True,
        env=isolated_bst_env(tmp_path),
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
    # P1-33: cpu_accounting is not fabricated from builders - real CPU
    # measurement doesn't exist in this ingestion pipeline, so it's
    # honestly omitted rather than populated with a synthetic number.
    assert "cpu_accounting" not in run_context

    # P1-37: the same real run-identity manifest hash is embedded in all
    # three files, produced by one real extraction.
    manifest_hash = run_context["run_identity"]["manifest_hash"]
    assert manifest_hash
    assert graph["run_identity_hash"] == manifest_hash
    assert trace["run_identity_hash"] == manifest_hash

    # The whole point: zero manual editing before bga can consume it.
    from bga import analyze_run
    result = analyze_run(out_dir)
    assert result is not None
    assert result.run_id == manifest_hash
    assert result.confidence["hard_gates"]["run_identity_consistent"] is True
    assert result.confidence["run_identity_available"] is True
    assert not any(v.get("type") == "run_identity_mismatch" for v in result.violations)
    # P1-33, re-baselined by UX-84 against a live bst 2.7. This used to
    # assert `cpu_accounting_available is False`. `UX-17` widened that
    # flag: it no longer means "a cpu_accounting block was present", it
    # means "a *real* capacity value is available at all", and a detected
    # host core count is one (see bga/utilisation/__init__.py:225-238,
    # which says so in as many words). Measured here:
    # `effective_cpus = 4.0`, `effective_cpus_source =
    # detected_host_cpu_count`.
    #
    # P1-33's actual rule survives that widening intact and is what is
    # asserted now: capacity is never fabricated from a *scheduling
    # parameter*. `builders` is 4 in this run too, so a regression that
    # went back to reading it would produce the same 4.0 - only the
    # source string separates the honest answer from the fabricated one,
    # which is why it is the assertion.
    assert "cpu_accounting" not in run_context
    assert result.utilisation["effective_cpus_source"] == "detected_host_cpu_count"
    assert result.utilisation["cpu_accounting_available"] is True
    assert result.utilisation["potential_oversubscription"] is False
    assert result.utilisation["oversubscription_evidence"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/spec/ingestion-pipeline.md")
def test_different_target_lists_produce_different_requested_targets(tmp_path):
    """Acceptance test (P4-10's own): using a *different* target list on
    two separate real builds produces two different, each-individually-
    correct requested_target sets - proving target derivation isn't
    hardcoded to a fixed convention."""

    def _build_and_extract(targets, out_name):
        log_path = tmp_path / f"{out_name}.log"
        proc = subprocess.run(
            ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build"] + targets,
            capture_output=True, text=True,
            env=isolated_bst_env(tmp_path),
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


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/spec/ingestion-pipeline.md")
def test_pipeline_overhead_extracted_from_a_real_cached_rebuild(tmp_path):
    """P4-14: rebuilding an already-built project logs a real "Query
    cache" pipeline-level activity (see docs/spec/ingestion-pipeline.md fact
    11) - confirm it round-trips into run-context.json's
    `pipeline_overhead` field and that bga's own report picks it up, even
    though `bst`'s own per-element FETCH/BUILD queues are entirely empty
    for a fully-cached rebuild (fact 9)."""

    env = isolated_bst_env(tmp_path)

    # First build populates the cache.
    subprocess.run(
        ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "app.bst"],
        capture_output=True, text=True, env=env,
    )
    # Second build is fully cached - this is the log we extract from.
    proc = subprocess.run(
        ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "app.bst"],
        capture_output=True, text=True, env=env,
    )
    log_path = tmp_path / "cached_rebuild.log"
    log_path.write_text(proc.stdout + proc.stderr)

    out_dir = tmp_path / "run"
    extract_run(str(FIXTURE_PROJECT), str(log_path), str(out_dir), log_format="auto")

    run_context = json.loads((out_dir / "run-context.json").read_text())
    phases = {e["phase"] for e in run_context.get("pipeline_overhead", [])}
    assert "Query cache" in phases
    assert "Build" not in phases

    from bga import analyze_run
    from bga.report.text import format_text
    result = analyze_run(out_dir)
    assert "Pipeline Overhead" in format_text(result)
