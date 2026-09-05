"""UX-694: identity ignores the line number; the baseline only shrinks.

A temporary package and a temporary baseline, so these mutate the
tree - move lines, add and fix findings, shrink - without touching the
real `tests/quality_baseline.json`.
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "dev_baseline.py"

VIOLATION = ("import subprocess\n\n\n"
             "def f():\n"
             "    subprocess.run(cmd, shell=True)\n")
CLEAN = "def f():\n    return 1\n"


def _run(root, baseline, *flags):
    cmd = [sys.executable, str(TOOL), "--root", str(root), "--paths", "pkg",
           "--baseline", str(baseline), *flags]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestIdentityIgnoresTheLineNumber:
    def test_a_line_inserted_above_still_matches(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, "\n" + VIOLATION)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 0, check.stdout


class TestNewAndStaleFindings:
    def test_a_new_finding_is_reported_and_reds(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, VIOLATION)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1
        assert "new: ruff S602" in check.stdout

    def test_a_fixed_finding_is_reported_as_stale(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, CLEAN)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1
        assert "stale: ruff S602" in check.stdout


class TestShrinkOnlyShrinks:
    def test_shrink_removes_exactly_the_stale_entry(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        _run(tmp_path, baseline, "--write")
        before = len(_load(baseline)["findings"])
        _write(module, CLEAN)
        shrink = _run(tmp_path, baseline, "--shrink")
        assert shrink.returncode == 0
        after = _load(baseline)["findings"]
        assert len(after) == before - 1
        assert _run(tmp_path, baseline, "--check").returncode == 0

    def test_shrink_never_adds(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        _run(tmp_path, baseline, "--write")
        before = _load(baseline)["findings"]
        _write(module, VIOLATION)
        shrink = _run(tmp_path, baseline, "--shrink")
        assert shrink.returncode == 0
        assert _load(baseline)["findings"] == before
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1
        assert "new: ruff S602" in check.stdout


class TestOccurrenceDisambiguates:
    def test_the_same_line_twice_gives_two_identities(self, tmp_path):
        text = ("import subprocess\n\n\n"
                "def f():\n"
                "    subprocess.run(cmd, shell=True)\n\n\n"
                "def g():\n"
                "    subprocess.run(cmd, shell=True)\n")
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, text)
        _run(tmp_path, baseline, "--write")
        entries = [f for f in _load(baseline)["findings"] if f["rule"] == "S602"]
        assert sorted(f["nth"] for f in entries) == [1, 2]
