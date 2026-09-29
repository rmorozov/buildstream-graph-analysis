"""UX-1082: the pre-build cache key set is read from the build's own
Plane 1 `Pipeline` block instead of a second, option-blind `bst show` -
so it reflects the options this build actually ran with, and the
snapshot's pre-build window issues no extra `bst` invocation.
"""
import os
import shutil
import subprocess

import pytest

from tools import bst_native_build_tracer as tracer

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE_PROJECT = os.path.join(REPO, "tests", "fixtures", "bst_option_project")
PLANE1_FIXTURE = os.path.join(REPO, "tests", "fixtures", "with_timeline", "build.log")

BST_AVAILABLE = shutil.which("bst") is not None
BST_SKIP_REASON = "bst not found on PATH - see docs/spec/ingestion-pipeline.md"

_NO_BLOCK_LOG = (
    "[wrapper][2026-01-01 00:00:00,000] INFO: Executing command: bst build app.bst\n"
    "[wrapper][2026-01-01 00:00:00,001] INFO: [00:00:00][        ]"
    "[    main:core activity ] SUCCESS Loading elements\n"
)

_UNRESOLVED_LOG = (
    "[wrapper][2026-01-01 00:00:00,000] INFO: Pipeline\n"
    "[wrapper][2026-01-01 00:00:00,000] INFO:  no reference "
    + "?" * 64 + " app.bst \n"
    "[wrapper][2026-01-01 00:00:00,001] INFO: " + "=" * 79 + "\n"
)


# --- Pure parsing (hermetic, no bst) --------------------------------------

def test_the_real_fixtures_pipeline_block_is_read():
    """`tests/fixtures/with_timeline/build.log` is a real captured Plane
    1 log with 11 elements in its `Pipeline` block."""
    result = tracer.read_cache_key_set_from_plane1_log(PLANE1_FIXTURE)
    assert result == {"sha256": "713ad6804e90d04a698116f917639600cb860b7998ed459bc5f77c069d621ce2",
                       "elements": 11}


def test_a_missing_file_is_unread():
    assert tracer.read_cache_key_set_from_plane1_log("/no/such/path.log") is None


def test_a_log_with_no_pipeline_block_is_unread_not_empty(tmp_path):
    """Absent block: `None`, distinguished from `hash_cache_key_lines("")`,
    which is a real digest of zero elements."""
    log = tmp_path / "build.log"
    log.write_text(_NO_BLOCK_LOG)
    result = tracer.read_cache_key_set_from_plane1_log(str(log))
    assert result is None
    assert result != tracer.hash_cache_key_lines("")


def test_an_unresolved_key_is_unread_not_guessed(tmp_path):
    """A non-strict build whose sources are not yet resolved prints `?`
    x64 in place of the key - the whole set is unread rather than a
    hash of whatever else the block did resolve."""
    log = tmp_path / "build.log"
    log.write_text(_UNRESOLVED_LOG)
    assert tracer.read_cache_key_set_from_plane1_log(str(log)) is None


def test_none_path_is_unread():
    assert tracer.read_cache_key_set_from_plane1_log(None) is None


# --- The snapshot's pre-build window (hermetic: run_traced_build faked) --

def _fake_bst(tmp_path):
    """Records every argv it is called with, one line per call."""
    script = tmp_path / "fake-bst"
    argv_file = tmp_path / "argv.txt"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{argv_file}"\n'
    )
    script.chmod(0o755)
    return str(script), argv_file


def _run_main(tmp_path, monkeypatch, fake_bst, wrapped_log_text):
    """Runs `tracer.main(["run", ...])` with `run_traced_build` faked to
    a plain `subprocess.run` of the wrapped command (so the fake `bst`
    above sees exactly what a real capture would hand it) plus a fixed
    wrapped-log body, standing in for what a real capture's Plane 1 log
    would already contain by the time this function reads it."""
    raw_log = tmp_path / "raw.log"
    raw_log.write_bytes(b"")
    wrapped_log = tmp_path / "wrapped.log"
    output = tmp_path / "report.json"

    def fake_run_traced_build(project_dir, cmd, raw_log_path, wrapped_log_path=None, **kwargs):
        subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
        if wrapped_log_path:
            with open(wrapped_log_path, "w", encoding="utf-8") as f:
                f.write(wrapped_log_text)
        return 0

    monkeypatch.setattr(tracer, "run_traced_build", fake_run_traced_build)

    rc = tracer.main([
        "run", "--raw-log", str(raw_log), "--wrapped-log", str(wrapped_log),
        str(tmp_path), str(output),
        "--", fake_bst, "build", "app.bst",
    ])
    assert rc == 0
    import json
    with open(output, encoding="utf-8") as f:
        return json.load(f)


def test_the_snapshot_issues_no_bst_show_before_the_build(tmp_path, monkeypatch):
    fake_bst, argv_file = _fake_bst(tmp_path)
    _run_main(tmp_path, monkeypatch, fake_bst, _NO_BLOCK_LOG)

    calls = argv_file.read_text().splitlines()
    # Exactly the one wrapped build call reached the fake `bst` - no
    # separate pre-build `show` subprocess.
    assert calls == ["build app.bst"]
    assert not any("show" in call for call in calls)


def test_the_report_carries_the_key_set_read_from_the_log(tmp_path, monkeypatch):
    fake_bst, _ = _fake_bst(tmp_path)
    with open(PLANE1_FIXTURE, encoding="utf-8") as f:
        real_pipeline_log = f.read()
    report = _run_main(tmp_path, monkeypatch, fake_bst, real_pipeline_log)

    assert report["cache_key_set"] == {
        "sha256": "713ad6804e90d04a698116f917639600cb860b7998ed459bc5f77c069d621ce2",
        "elements": 11,
    }


def test_a_report_without_a_pipeline_block_carries_an_unread_key_set(tmp_path, monkeypatch):
    fake_bst, _ = _fake_bst(tmp_path)
    report = _run_main(tmp_path, monkeypatch, fake_bst, _NO_BLOCK_LOG)
    assert report["cache_key_set"] is None


# --- Real bst, two variants (bst-marked) ----------------------------------

def _bst_show_key_set(project_dir, global_opts, target):
    proc = subprocess.run(
        ["bst", *global_opts, "--no-colors", "show", "--format",
         "%{name} %{full-key}", target],
        cwd=project_dir, capture_output=True, text=True, check=True,
    )
    return tracer.hash_cache_key_lines(proc.stdout)


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason=BST_SKIP_REASON)
def test_two_variants_of_a_real_build_read_different_option_aware_key_sets(tmp_path):
    """Two real builds of the same fixture project, differing only by a
    project option passed as `-o`: each build's own Plane 1 log yields
    a key set equal to an option-aware `bst show -o ...` for that
    variant, and the two sets differ - proving the read reflects the
    build's own options rather than the default ones a bare `bst show`
    would see."""
    from tests.unit._bst_env import bst_env

    def _build_and_read(global_opts, out_name):
        raw_log = str(tmp_path / f"{out_name}-raw.log")
        wrapped_log = str(tmp_path / f"{out_name}-wrapped.log")
        cmd = ["bst", *global_opts, "--no-colors", "build", "app.bst"]
        with bst_env(tmp_path / f"{out_name}-home"):
            tracer.run_traced_build(FIXTURE_PROJECT, cmd, raw_log, wrapped_log_path=wrapped_log)
            expected = _bst_show_key_set(FIXTURE_PROJECT, global_opts, "app.bst")
        return tracer.read_cache_key_set_from_plane1_log(wrapped_log), expected

    default_read, default_expected = _build_and_read([], "default")
    variant_b_read, variant_b_expected = _build_and_read(["-o", "variant", "b"], "variant-b")

    assert default_read is not None and variant_b_read is not None
    assert default_read == default_expected
    assert variant_b_read == variant_b_expected
    assert default_read != variant_b_read
