"""UX-712: the size ledger's three counts, and that it only shrinks.

A temporary package and a temporary reference file, so these mutate
sizes without touching the real `tests/quality_reference.json`.
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "dev_sizes.py"

SMALL = "def f():\n    return 1\n"

#: Eight distinct-looking statements - pylint's `duplicate-code` needs
#: this many matching lines before it reports anything (measured: four
#: identical assignments plus a return did not trigger it, here).
BODY = ("    a = 1\n    b = 2\n    c = 3\n    d = 4\n"
        "    e = 5\n    g = 6\n    h = 7\n    return a + b + c + d + e + g + h\n")


def _run(root, reference, *flags):
    cmd = [sys.executable, str(TOOL), "--root", str(root), "--paths", "pkg",
           "--reference", str(reference), *flags]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fake_pylint(tmp_path, script):
    """A `pylint` on `PATH` ahead of the real one, standing in for a
    broken install."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "pylint"
    fake.write_text(script, encoding="utf-8")
    fake.chmod(0o755)
    return bin_dir


class TestTheThreeCells:
    def test_longest_function_and_file_lines_are_measured(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, "def f():\n" + BODY)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        row = _load(reference)["files"]["pkg/m.py"]
        assert row["longest_function"] == 9
        assert row["file_lines"] == 9
        assert row["duplicate_blocks"] == 0

    def test_a_duplicate_block_is_attributed_to_both_real_files(self, tmp_path):
        """pylint attributes every `duplicate-code` finding in a run to
        whichever module it analysed last - not the files the
        duplication is in - so this checks the count lands on both
        participants instead of on one arbitrary third file."""
        module = tmp_path / "pkg" / "m.py"
        other = tmp_path / "pkg" / "o.py"
        third = tmp_path / "pkg" / "z.py"
        reference = tmp_path / "reference.json"
        _write(module, "def f():\n" + BODY)
        _write(other, "def g():\n" + BODY)
        _write(third, SMALL)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        rows = _load(reference)["files"]
        assert rows["pkg/m.py"]["duplicate_blocks"] == 1
        assert rows["pkg/o.py"]["duplicate_blocks"] == 1
        assert rows["pkg/z.py"]["duplicate_blocks"] == 0


class TestTheRatchet:
    def test_a_grown_cell_reds_check(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, SMALL)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        _write(module, "def f():\n" + BODY)
        check = _run(tmp_path, reference, "--check")
        assert check.returncode == 1
        assert "grew: pkg/m.py longest_function 2 -> 9" in check.stdout

    def test_ten_lines_added_to_a_function_reds_check(self, tmp_path):
        """The Acceptance Test's own mutation shape: a function grows
        by ten lines and its row grows, red."""
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        before = "def f():\n" + BODY
        _write(module, before)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        extra = "".join(f"    _ = {n}\n" for n in range(10))
        after = "def f():\n" + BODY + extra
        _write(module, after)
        check = _run(tmp_path, reference, "--check")
        assert check.returncode == 1
        assert "grew: pkg/m.py longest_function" in check.stdout

    def test_a_shrunk_cell_leaves_check_clean_once_adopted(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, "def f():\n" + BODY)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        _write(module, SMALL)
        assert _run(tmp_path, reference, "--check").returncode == 0
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        row = _load(reference)["files"]["pkg/m.py"]
        assert row["longest_function"] == 2
        assert _run(tmp_path, reference, "--check").returncode == 0


class TestAdoptRefusesToMoveACellUp:
    def test_adopt_without_force_refuses_and_writes_nothing(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, SMALL)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        before = reference.read_bytes()
        _write(module, "def f():\n" + BODY)
        adopt = _run(tmp_path, reference, "--adopt")
        assert adopt.returncode == 1
        assert "refused: pkg/m.py longest_function 2 -> 9" in adopt.stdout
        assert reference.read_bytes() == before

    def test_adopt_with_force_moves_the_cell_up(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, SMALL)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        _write(module, "def f():\n" + BODY)
        assert _run(tmp_path, reference, "--adopt", "--force").returncode == 0
        row = _load(reference)["files"]["pkg/m.py"]
        assert row["longest_function"] == 9
        assert _run(tmp_path, reference, "--check").returncode == 0


class TestANewFileIsRecordedNotJudged:
    def test_a_file_missing_from_the_reference_does_not_red_check(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, SMALL)
        assert _run(tmp_path, reference, "--adopt").returncode == 0
        other = tmp_path / "pkg" / "o.py"
        _write(other, "def g():\n" + BODY)
        assert _run(tmp_path, reference, "--check").returncode == 0


class TestABrokenPylintIsAFailureNotZeroDuplicates:
    """`UX-788`: a swallowed pylint run must not read as a clean sweep."""

    def test_a_nonzero_exit_with_no_json_raises(self, tmp_path, monkeypatch):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, SMALL)
        bin_dir = _fake_pylint(tmp_path, "#!/bin/sh\nexit 32\n")
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
        result = _run(tmp_path, reference, "--adopt")
        assert result.returncode == 2
        assert "pylint exited 32" in result.stdout

    def test_an_ok_exit_with_non_json_output_raises(self, tmp_path, monkeypatch):
        module = tmp_path / "pkg" / "m.py"
        reference = tmp_path / "reference.json"
        _write(module, SMALL)
        bin_dir = _fake_pylint(tmp_path, "#!/bin/sh\necho 'not json'\nexit 0\n")
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
        result = _run(tmp_path, reference, "--adopt")
        assert result.returncode == 2
        assert "pylint did not print JSON" in result.stdout
