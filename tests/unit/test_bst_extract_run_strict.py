"""Tests for tools/bst_extract_run.py's `--strict` mode (P4-13): a real,
opt-in guarantee that graph.json's cache keys reflect the same project
state the analyzed build actually ran against, via BuildStream's own
`project.refs` mechanism. See
docs/backlog/tasks/P4-13-strict-mode-project-refs-consistency.md.

Three layers:
1. Pure unit tests against `_read_ref_storage`/`_check_project_refs_strict` -
   fast, hermetic (real `git` subprocess, no real `bst` needed at all -
   these functions never shell out to `bst`), always run.
2. A real, `bst`-gated end-to-end test against
   `tests/fixtures/bst_show_project/` (confirmed to use the default
   `ref-storage: inline`) - `--strict` must fail loudly for it. No
   `buildstream-plugins` needed (the fixture is `kind: local`-only).
3. A real, `bst` + `buildstream-plugins`-gated end-to-end test building a
   genuine `ref-storage: project.refs` project with a real `kind: git`
   source inline (not checked into the repo) - exercises the full real
   acceptance scenarios (clean succeeds, dirtied project.refs fails
   loudly). Skipped whenever `buildstream-plugins` isn't importable (a
   separate, heavier optional dependency - see
   docs/spec/ingestion-pipeline.md fact 7) - this was verified manually
   against a real BuildStream 2.7.0 + buildstream-plugins install; see
   the task file's Verification Log for that real run's output.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.bst_extract_run import (
    _check_project_refs_strict,
    _read_ref_storage,
    extract_run,
)

from ._bst_env import isolated_bst_env

FIXTURE_PROJECT = Path(__file__).resolve().parents[1] / "fixtures" / "bst_show_project"
BST_AVAILABLE = shutil.which("bst") is not None
try:
    import buildstream_plugins  # noqa: F401
    BUILDSTREAM_PLUGINS_AVAILABLE = True
except ImportError:
    BUILDSTREAM_PLUGINS_AVAILABLE = False


def _git_init(path, env=None):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, env=env)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=path, check=True, env=env)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True, env=env)


def _git_commit_all(path, message, env=None):
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True, env=env)


# --- Pure unit tests: _read_ref_storage -----------------------------------

def test_read_ref_storage_defaults_to_inline_when_absent(tmp_path):
    (tmp_path / "project.conf").write_text("name: t\nmin-version: 2.0\n")
    assert _read_ref_storage(str(tmp_path)) == "inline"


def test_read_ref_storage_reads_project_refs_value(tmp_path):
    (tmp_path / "project.conf").write_text(
        "name: t\nmin-version: 2.0\nref-storage: project.refs\n"
    )
    assert _read_ref_storage(str(tmp_path)) == "project.refs"


def test_read_ref_storage_fails_loudly_without_project_conf(tmp_path):
    with pytest.raises(RuntimeError, match="no project.conf"):
        _read_ref_storage(str(tmp_path))


# --- Pure unit tests: _check_project_refs_strict --------------------------

def test_strict_fails_when_ref_storage_is_not_project_refs(tmp_path):
    (tmp_path / "project.conf").write_text("name: t\nmin-version: 2.0\n")
    with pytest.raises(RuntimeError, match="ref-storage: project.refs"):
        _check_project_refs_strict(str(tmp_path))


def test_strict_fails_when_project_refs_file_is_missing(tmp_path):
    (tmp_path / "project.conf").write_text(
        "name: t\nmin-version: 2.0\nref-storage: project.refs\n"
    )
    with pytest.raises(RuntimeError, match="no project.refs file exists"):
        _check_project_refs_strict(str(tmp_path))


def test_strict_fails_when_not_a_git_repository(tmp_path):
    (tmp_path / "project.conf").write_text(
        "name: t\nmin-version: 2.0\nref-storage: project.refs\n"
    )
    (tmp_path / "project.refs").write_text("projects: {}\n")
    with pytest.raises(RuntimeError, match="not a git repository"):
        _check_project_refs_strict(str(tmp_path))


def test_strict_fails_when_project_refs_has_uncommitted_changes(tmp_path):
    (tmp_path / "project.conf").write_text(
        "name: t\nmin-version: 2.0\nref-storage: project.refs\n"
    )
    (tmp_path / "project.refs").write_text("projects: {}\n")
    _git_init(tmp_path)
    _git_commit_all(tmp_path, "init")
    (tmp_path / "project.refs").write_text("projects: {changed: true}\n")

    with pytest.raises(RuntimeError, match="uncommitted changes"):
        _check_project_refs_strict(str(tmp_path))


def test_strict_succeeds_when_project_refs_is_clean(tmp_path):
    (tmp_path / "project.conf").write_text(
        "name: t\nmin-version: 2.0\nref-storage: project.refs\n"
    )
    content = b"projects: {}\n"
    (tmp_path / "project.refs").write_bytes(content)
    _git_init(tmp_path)
    _git_commit_all(tmp_path, "init")

    assert _check_project_refs_strict(str(tmp_path)) == content


def test_strict_ignores_uncommitted_changes_to_other_files(tmp_path):
    """Only project.refs itself matters - an unrelated dirty file must
    not trip --strict (that's exactly the imprecision --strict is meant
    to improve on relative to the existing whole-tree dirty check)."""
    (tmp_path / "project.conf").write_text(
        "name: t\nmin-version: 2.0\nref-storage: project.refs\n"
    )
    (tmp_path / "project.refs").write_text("projects: {}\n")
    _git_init(tmp_path)
    _git_commit_all(tmp_path, "init")
    (tmp_path / "unrelated.bst").write_text("kind: import\n")

    # No raise.
    _check_project_refs_strict(str(tmp_path))


# --- Real, bst-gated end-to-end: inline-storage fixture must fail loudly --

@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/spec/ingestion-pipeline.md")
def test_strict_fails_loudly_for_the_inline_storage_fixture(tmp_path):

    log_path = tmp_path / "build.log"
    proc = subprocess.run(
        ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "app.bst"],
        capture_output=True, text=True,
        env=isolated_bst_env(tmp_path),
    )
    log_path.write_text(proc.stdout + proc.stderr)

    with pytest.raises(RuntimeError, match="ref-storage: project.refs"):
        extract_run(str(FIXTURE_PROJECT), str(log_path), str(tmp_path / "run"), strict=True)


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/spec/ingestion-pipeline.md")
def test_non_strict_extraction_of_inline_fixture_has_no_provenance_field(tmp_path):
    """Default (non-strict) flow: unchanged behavior, and no
    project_refs_provenance field for a project with no project.refs at
    all (P4-13's own "no schema collision" requirement - the field is
    only ever present when a real project.refs exists)."""

    log_path = tmp_path / "build.log"
    proc = subprocess.run(
        ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "app.bst"],
        capture_output=True, text=True,
        env=isolated_bst_env(tmp_path),
    )
    log_path.write_text(proc.stdout + proc.stderr)

    out_dir = tmp_path / "run"
    extract_run(str(FIXTURE_PROJECT), str(log_path), str(out_dir))  # strict=False (default)
    run_context = json.loads((out_dir / "run-context.json").read_text())
    assert "project_refs_provenance" not in run_context


# --- Real, bst + buildstream-plugins-gated: full project.refs lifecycle --

@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BUILDSTREAM_PLUGINS_AVAILABLE),
    reason="bst and/or buildstream-plugins not available - see docs/spec/ingestion-pipeline.md",
)
def test_real_project_refs_lifecycle_clean_then_dirtied(tmp_path):
    """The full real P4-13 acceptance scenario: a real ref-storage:
    project.refs project with a real trackable (kind: git) source -
    clean tree succeeds with a real provenance hash embedded; dirtying
    project.refs (re-tracking against a new upstream commit without
    committing) makes --strict fail loudly, naming project.refs
    specifically."""

    env = isolated_bst_env(tmp_path / "home")
    (tmp_path / "home").mkdir()

    srcrepo = tmp_path / "srcrepo"
    srcrepo.mkdir()
    (srcrepo / "file.txt").write_text("hello\n")
    _git_init(srcrepo, env=env)
    _git_commit_all(srcrepo, "init", env=env)

    project = tmp_path / "project"
    (project / "elements").mkdir(parents=True)
    (project / "project.conf").write_text(
        "name: p413-test\nmin-version: 2.0\nelement-path: elements\n"
        "ref-storage: project.refs\n"
        "plugins:\n- origin: pip\n  package-name: buildstream-plugins\n  sources:\n  - git\n"
    )
    (project / "elements" / "thing.bst").write_text(
        f"kind: import\nsources:\n- kind: git\n  url: file://{srcrepo}\n  track: master\n"
    )

    subprocess.run(
        ["bst", "-C", str(project), "--no-colors", "source", "track", "thing.bst"],
        capture_output=True, text=True, env=env, check=True,
    )
    _git_init(project, env=env)
    _git_commit_all(project, "init with project.refs", env=env)

    build_log = tmp_path / "build.log"
    proc = subprocess.run(
        ["bst", "-C", str(project), "--no-colors", "build", "thing.bst"],
        capture_output=True, text=True, env=env,
    )
    build_log.write_text(proc.stdout + proc.stderr)

    out_dir = tmp_path / "run"
    summary = extract_run(str(project), str(build_log), str(out_dir), strict=True)
    assert summary["output_dir"] == str(out_dir)
    run_context = json.loads((out_dir / "run-context.json").read_text())
    assert run_context["project_refs_provenance"]["path"] == "project.refs"
    assert len(run_context["project_refs_provenance"]["sha256"]) == 64

    # Dirty project.refs: commit a new upstream revision, re-track
    # without committing the result.
    (srcrepo / "file.txt").write_text("hello\nsecond commit\n")
    subprocess.run(["git", "add", "file.txt"], cwd=srcrepo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "second"], cwd=srcrepo, check=True, env=env)
    subprocess.run(
        ["bst", "-C", str(project), "--no-colors", "source", "track", "thing.bst"],
        capture_output=True, text=True, env=env, check=True,
    )

    with pytest.raises(RuntimeError, match="project.refs.*uncommitted changes"):
        extract_run(str(project), str(build_log), str(tmp_path / "run2"), strict=True)
