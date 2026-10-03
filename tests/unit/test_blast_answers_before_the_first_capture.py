"""UX-1326: `bga blast --no-cost` with no snapshot reads the project with `bst show`.

A fake `bst` on PATH prints `bst show`'s record format for three elements and records its argv.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_FAKE_BST = r'''#!{python}
import os, sys
with open(os.environ["FAKE_BST_ARGV"], "a") as handle:
    handle.write(" ".join(sys.argv[1:]) + "\n")
if os.environ.get("FAKE_BST_FAIL"):
    sys.stderr.write("pkgs/broken.bst: Malformed YAML\n")
    sys.exit(255)
US, RS = "\x1f", "\x1e"
records = [
    ("core.bst", "manual", "[]"),
    ("app.bst", "manual", "- core.bst"),
    ("tool.bst", "manual", "[]"),
]
for name, kind, deps in records:
    sys.stdout.write(US.join([name, "k-" + name, kind, deps, "[]", "{{}}", "{{}}"]) + RS)
'''


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    (root / "elements").mkdir(parents=True)
    (root / "files" / "core").mkdir(parents=True)
    (root / "project.conf").write_text("name: proj\nmin-version: 2.0\nelement-path: elements\n")
    (root / "elements" / "core.bst").write_text("kind: manual\nsources:\n- kind: local\n  path: files/core\n")
    for name in ("app.bst", "tool.bst"):
        (root / "elements" / name).write_text("kind: manual\n")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "bst"
    fake.write_text(_FAKE_BST.format(python=sys.executable))
    fake.chmod(0o755)
    monkeypatch.setenv("FAKE_BST_ARGV", str(tmp_path / "argv.txt"))
    monkeypatch.delenv("FAKE_BST_FAIL", raising=False)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("PYTHONPATH", REPO_ROOT)
    return root, tmp_path / "argv.txt"


def _bga(root, *args):
    return subprocess.run(
        [sys.executable, "-m", "bga.cli", "blast", *args], cwd=root, capture_output=True, text=True, check=False
    )


def test_no_cost_answers_from_the_project_and_says_so(project):
    root, argv = project
    result = _bga(root, "core.bst", "--no-cost")
    assert result.returncode == 0, result.stderr
    assert "Read from the project, not a run" in result.stdout
    assert "every element in the project" in result.stdout
    assert "Rebuilds 2 elements" in result.stdout and "of 3 in the project" in result.stdout
    assert argv.read_text().split("\n")[0].startswith("show --deps all --format")


def test_a_path_resolves_against_the_inventory_built_from_the_project(project):
    root, _argv = project
    payload = json.loads(_bga(root, "files/core/main.c", "--no-cost", "--format", "json").stdout)
    assert payload["read_from"] == "project" and payload["direct_elements"] == ["core.bst"]
    assert payload["blast_count"] == 2


def test_the_declared_default_target_is_read_and_named(project):
    root, argv = project
    (root / "project.conf").write_text(
        "name: proj\nmin-version: 2.0\nelement-path: elements\ndefaults:\n  targets:\n  - app.bst\n"
    )
    result = _bga(root, "core.bst", "--no-cost")
    assert "`bst show` on app.bst" in result.stdout, result.stdout
    assert argv.read_text().strip().endswith(" app.bst")


def test_target_names_the_graph_to_read(project):
    root, argv = project
    result = _bga(root, "core.bst", "--no-cost", "--target", "tool.bst")
    assert "`bst show` on tool.bst" in result.stdout
    assert argv.read_text().strip().endswith(" tool.bst")


def test_a_project_that_fails_to_load_prints_bsts_error_not_the_alias_error(project, monkeypatch):
    root, _argv = project
    monkeypatch.setenv("FAKE_BST_FAIL", "1")
    result = _bga(root, "core.bst", "--no-cost")
    assert result.returncode == 2
    assert "pkgs/broken.bst: Malformed YAML" in result.stderr
    assert "names a snapshot" not in result.stderr


def test_with_cost_and_no_snapshot_the_refusal_stands(project):
    root, argv = project
    result = _bga(root, "core.bst")
    assert result.returncode == 2 and "names a snapshot" in result.stderr
    assert not argv.exists(), "the measured answer must not read the project"


def test_with_a_snapshot_no_cost_still_reads_the_run(project):
    root, argv = project
    golden = os.path.join(REPO_ROOT, "tests", "fixtures", "golden", "mixed_task_kinds")
    run = root / ".bga" / "runs" / "20260101T000000Z" / "run"
    shutil.copytree(golden, run)
    payload = json.loads(_bga(root, "base.bst", "--no-cost", "--format", "json").stdout)
    assert payload["read_from"] == "run" and payload["element_exists"], payload
    assert not argv.exists(), "a snapshot is present, so `bst show` must not run"
