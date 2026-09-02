"""`UX-509`: a parallel track's worktree is inside the tree that lints it.

`UX-504`'s `implementer` runs in a worktree and the Agent tool puts it
at `.claude/worktrees/agent-<id>/` - inside the repository. `lint-docs`
scans `.claude/` recursively, so with three tracks in flight round 75's
`make lint` went red on `examples/README.md` in a copy the orchestrator
had never opened.

Two halves hold it: `.gitignore` names the directory, and the lint
reads that same list rather than a second copy of it. Both are asserted
here against the real mechanisms - the recipe in the `Makefile` and
`git check-ignore` - and the third clause runs the recipe's own file
listing over a planted file, because the flag is `pymarkdown`'s
promise and not this repository's.
"""
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

#: Where the Agent tool puts an `implementer`'s copy of the repository.
WORKTREES = ".claude/worktrees"


def _recipe():
    """The `lint-docs` command line, out of the Makefile.

    Read rather than restated: a constant here would be a third place
    to keep in step instead of a check on the two real ones.
    """
    body = (REPO / "Makefile").read_text(encoding="utf-8")
    found = re.search(r"^lint-docs:\n\t(.+)$", body, flags=re.M)
    assert found, "no lint-docs recipe in the Makefile any more"
    return found.group(1)


def test_git_ignores_the_worktree_directory():
    said = subprocess.run(
        ["git", "check-ignore", "-q", f"{WORKTREES}/agent-probe/README.md"],
        cwd=REPO, capture_output=True)
    assert said.returncode == 0, (
        f"`{WORKTREES}/` is not ignored, so every running track shows in "
        f"`git status` and a bulk add would commit another branch's "
        f"working copy")


def test_the_doc_lint_reads_that_same_list():
    assert "--respect-gitignore" in _recipe(), (
        f"lint-docs runs `{_recipe()}` - it scans `.claude/` recursively, "
        f"so it lints every track's copy of the repository as well as this "
        f"one")


def test_a_markdown_file_in_a_worktree_is_not_listed(tmp_path):
    """The end-to-end half: `--respect-gitignore` is `pymarkdown`'s
    promise, not this repository's, so it is exercised rather than
    read. The probe is planted where a real worktree goes and removed
    again."""
    probe = REPO / WORKTREES / "agent-lint-probe" / "PROBE.md"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("# probe\n\n```\nno language, MD040\n```\n",
                     encoding="utf-8")
    try:
        listed = subprocess.run(
            _recipe().replace("scan ", "scan -l ", 1).split(),
            cwd=REPO, capture_output=True, text=True).stdout
    finally:
        probe.unlink()
        probe.parent.rmdir()
    assert str(probe.relative_to(REPO)) not in listed, (
        "the lint lists a file inside a track's worktree, which is the "
        "state where one track's unfinished document reddens another's")
    assert ".claude/agents/implementer.md" in listed, (
        "and it has stopped reading `.claude/` at all, which is the other "
        "way this clause can be satisfied and the wrong one")


if __name__ == "__main__":  # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
