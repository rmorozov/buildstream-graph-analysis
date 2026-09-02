"""`UX-509`: a parallel track's worktree is inside the tree that lints it.

`UX-504`'s `implementer` runs in a worktree and the Agent tool puts it
at `.claude/worktrees/agent-<id>/` - inside the repository. `lint-docs`
walked `.claude/` recursively, so with three tracks in flight round 75's
`make lint` went red on `examples/README.md` in a copy the orchestrator
had never opened.

The fix is that the file list comes from **git** rather than from a
walk: a worktree is untracked, so `git ls-files` cannot name it, on any
version of anything. The first attempt used `--respect-gitignore`
instead and CI found it - the 3.9 lane resolves `pymarkdownlnt>=0.9` to
0.9.33, which has no such flag, and `make lint` died with `unrecognized
arguments` before linting a single file (run 33581936314).

The claim that can fail is not "some path is excluded" but "the list is
git's": a walk that skipped this one directory would satisfy the first
and lose the property on the next worktree the tooling invents.
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
    found = re.search(r"^lint-docs:\n((?:\t.*\n)+)", body, flags=re.M)
    assert found, "no lint-docs recipe in the Makefile any more"
    return found.group(1).replace("\t", "").replace("\\\n", " ")


def test_git_ignores_the_worktree_directory():
    said = subprocess.run(
        ["git", "check-ignore", "-q", f"{WORKTREES}/agent-probe/README.md"],
        cwd=REPO, capture_output=True)
    assert said.returncode == 0, (
        f"`{WORKTREES}/` is not ignored, so every running track shows in "
        f"`git status` and a bulk add would commit another branch's "
        f"working copy")


def test_the_doc_lint_takes_its_files_from_git():
    recipe = _recipe()
    assert "git ls-files" in recipe, (
        f"lint-docs runs `{recipe.strip()}` - it walks the tree, so it "
        f"lints every track's copy of the repository as well as this one")


def test_the_lint_does_not_depend_on_a_flag_the_39_lane_lacks():
    """`--respect-gitignore` arrived in pymarkdown 0.9.34 and the 3.9
    lane resolves to 0.9.33, where it is a hard argument error. CI found
    that; this keeps it found."""
    assert "--respect-gitignore" not in _recipe()


def test_a_markdown_file_in_a_worktree_is_not_listed():
    """The end-to-end half, run through a shell because the recipe is a
    pipeline. The probe is planted where a real worktree goes and
    removed again."""
    probe = REPO / WORKTREES / "agent-lint-probe" / "PROBE.md"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("# probe\n\n```\nno language, MD040\n```\n",
                     encoding="utf-8")
    try:
        listed = subprocess.run(_recipe().replace("scan", "scan -l"),
                                shell=True, cwd=REPO,
                                capture_output=True, text=True).stdout
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
