"""UX-80 acceptance test: on a project that overrides `build-root`, the
README's own capture-and-correlate sequence must join the traced element
by UID rather than collapsing it into one unresolved bucket.

Every other fixture and example in this repository joins cleanly for a
reason that has nothing to do with the join working: BuildStream's
default build root embeds the element name, so Plane 2's path-convention
tag happens to be right. `freedesktop-sdk` - the project
`docs/guides/real-project.md` is written from - sets its own build root,
and there the tag is `buildstream-build` for every sandbox in the build.
That is UX-56's collapse, and it was invisible here until this fixture
existed.

So this test runs the documented commands, unmodified, against a project
built to fail the old way, and asserts both halves:

  - with the invocation log (the default since UX-80, implied by
    `--wrapped-log`), the sandbox resolves to `worker.bst`;
  - with `--no-invocation-log`, the same build collapses.

The control matters as much as the assertion. Without it a passing test
proves only that this fixture is not adversarial - which is the exact
mistake the pre-UX-80 suite made.
"""
import json
import os
import shutil
import subprocess

import pytest

from ._bst_env import isolated_bst_env

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "bst_build_root_override")

BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
BGA_AVAILABLE = shutil.which("bga") is not None


def _run(argv, env, cwd=REPO_ROOT):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    assert result.returncode == 0, f"{argv!r} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}"
    return result


def _staged_project(tmp_path):
    """A throwaway copy of the fixture with its sandbox runtime staged.

    The runtime is a real dynamically-linked shell and `sleep` lifted
    from the host, so it is generated rather than committed - the same
    rule `examples/` follows. Staging into a copy rather than into the
    checkout keeps the test from leaving 2.5 MB of host binaries behind
    in the working tree.
    """
    project_dir = str(tmp_path / "project")
    shutil.copytree(FIXTURE_DIR, project_dir)
    runtime = os.path.join(project_dir, "files", "runtime")
    result = subprocess.run(
        [os.path.join(project_dir, "stage_runtime.sh"), runtime],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"could not stage a dynamically-linked runtime: {result.stderr.strip()}")
    return project_dir


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and BGA_AVAILABLE),
    reason="bst/bwrap/bga not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_readme_sequence_joins_by_uid_when_build_root_is_overridden(tmp_path):
    project_dir = _staged_project(tmp_path)
    env = isolated_bst_env(tmp_path / "home")
    plane1 = str(tmp_path / "plane1.log")
    plane2 = str(tmp_path / "plane2.json")

    # README, "Joining the two planes", verbatim but for the paths.
    _run(
        ["bga", "capture", "run", "--wrapped-log", plane1, project_dir, plane2,
         "--", "bst", "build", "worker.bst"],
        env,
    )
    _run(["bga", "extract", "--format", "wrapped", project_dir, plane1, str(tmp_path / "run")], env)
    correlate = _run(["bga", "correlate", str(tmp_path / "run"), plane2], env)

    with open(plane2, encoding="utf-8") as f:
        report = json.load(f)

    # The build root really is overridden, so the path-convention tag
    # really did have nothing to offer. Asserted on the project file
    # rather than on the trace, so this stays true if the collapse is
    # ever fixed some other way.
    with open(os.path.join(project_dir, "project.conf"), encoding="utf-8") as f:
        assert "build-root: /buildstream-build" in f.read()

    correlation = report["invocation_correlation"]
    assert correlation["certain"] == 1, correlation
    assert correlation["intervals_used"] is True, correlation
    assert set(correlation["resolved"].values()) == {"worker.bst"}, correlation
    assert correlation["unmatched"] == [] and correlation["ambiguous"] == [], correlation

    attribution = report["element_attribution"]
    assert attribution["reliable"] is True, attribution
    assert attribution["recognized_elements"] == ["worker.bst"], attribution
    assert attribution["attributed_share"] == 1.0, attribution
    assert attribution["unresolved_bucket"] is None, attribution

    # And the user-facing join names the element, which is the thing the
    # guide promises and the thing a collapse cannot produce.
    assert "worker.bst" in correlate.stdout
    assert "Joined 1 element(s) on element UID" in correlate.stdout


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and BGA_AVAILABLE),
    reason="bst/bwrap/bga not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_without_the_invocation_log_the_same_build_collapses(tmp_path):
    project_dir = _staged_project(tmp_path)
    env = isolated_bst_env(tmp_path / "home")
    plane2 = str(tmp_path / "plane2.json")

    _run(
        ["bga", "capture", "run", "--no-invocation-log",
         "--wrapped-log", str(tmp_path / "plane1.log"), project_dir, plane2,
         "--", "bst", "build", "worker.bst"],
        env,
    )

    with open(plane2, encoding="utf-8") as f:
        report = json.load(f)

    assert report["invocation_correlation"] is None
    attribution = report["element_attribution"]
    assert attribution["reliable"] is False, attribution
    assert attribution["unresolved_bucket"] == "buildstream-build", attribution
    assert attribution["recognized_elements"] == [], attribution
