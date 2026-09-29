"""UX-1112: `push-check` lints the markdown changed against the merge-base,
not all 1,300 files (154 s); a `.pymarkdown.json` change lints everything.
Run in a scratch repo: the Makefile's own docs line, with `origin/main` a ref
there."""
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "dev_lint_docs.py"
BROKEN = "# A\ntext\n"  # MD022: no blank line under a heading
CLEAN = "# B\n\ntext\n"


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@example.com",
                    "-c", "user.name=t", *args], check=True,
                   capture_output=True, text=True)


def _docs_line():
    body = (REPO / "Makefile").read_text(encoding="utf-8")
    line = re.search(r"^push-check:.*\n((?:\t.*\n)+)", body, re.M).group(1)
    line = next(ln for ln in line.splitlines() if "dev_lint_docs" in ln)
    return line.strip().replace("tools/dev_lint_docs.py", str(TOOL)) \
                       .replace("python3", sys.executable).replace("$$", "$")


@pytest.fixture
def scratch(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / ".pymarkdown.json").write_bytes(
        (REPO / ".pymarkdown.json").read_bytes())
    (tmp_path / "docs" / "a.md").write_text(BROKEN)
    (tmp_path / "docs" / "b.md").write_text(CLEAN)
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path


def _gate(root):
    return subprocess.run(_docs_line(), shell=True, cwd=root,
                          capture_output=True, text=True,
                          env=dict(os.environ)).returncode


def _select(root, *args):
    out = subprocess.run([sys.executable, str(TOOL), *args], cwd=root,
                         capture_output=True, text=True).stdout
    return sorted(n for n in out.split("\0") if n)


class TestThePushGateLintsWhatChanged:
    def test_a_broken_unchanged_file_is_not_read(self, scratch):
        (scratch / "docs" / "b.md").write_text(CLEAN + "\nmore\n")
        assert _gate(scratch) == 0

    def test_a_broken_changed_file_reds(self, scratch):
        (scratch / "docs" / "a.md").write_text(BROKEN + "\nmore\n")
        assert _gate(scratch) != 0

    def test_the_fixture_is_broken_when_scanned(self, scratch):
        run = subprocess.run(
            [sys.executable, "-m", "pymarkdown", "--config", ".pymarkdown.json",
             "scan", "docs/a.md"], cwd=scratch, capture_output=True, text=True)
        assert run.returncode != 0

    def test_touching_the_config_lints_everything(self, scratch):
        cfg = scratch / ".pymarkdown.json"
        cfg.write_text(cfg.read_text() + "\n")
        assert _select(scratch, "--base", "origin/main") == [
            "docs/a.md", "docs/b.md"]
        assert _gate(scratch) != 0

    def test_a_rename_lints_the_new_name(self, scratch):
        _git(scratch, "mv", "docs/a.md", "docs/c.md")
        assert _select(scratch, "--base", "origin/main") == ["docs/c.md"]
        assert _gate(scratch) != 0

    def test_a_delete_does_not_error(self, scratch):
        _git(scratch, "rm", "-q", "docs/b.md")
        assert _select(scratch, "--base", "origin/main") == []
        assert _gate(scratch) == 0

    def test_an_unresolvable_base_lints_everything(self, scratch):
        assert _select(scratch, "--base", "nope") == ["docs/a.md", "docs/b.md"]

    def test_no_argument_is_every_tracked_doc(self, scratch):
        assert _select(scratch) == ["docs/a.md", "docs/b.md"]
