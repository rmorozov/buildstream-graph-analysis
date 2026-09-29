#!/usr/bin/env python3
"""UX-1112: the markdown files `make lint-docs` and `push-check` scan.

    python3 tools/dev_lint_docs.py                 # every tracked doc, NUL-separated
    python3 tools/dev_lint_docs.py --base REV      # only the ones changed against REV

`--base` is the diff against REV (ACMR: a rename keeps the new path, a
delete drops) intersected with the tracked list; the full list when
`.pymarkdown.json` changed or REV does not resolve. No argument is
`lint-docs`'s own list (UX-509: `git ls-files`, so a worktree clone
under `.claude/` is never walked).
"""

import argparse
import shutil
import subprocess
import sys

PATHSPECS = ("README.md", "CLAUDE.md", "REVIEW.md", "CHANGELOG.md", "docs/*.md", ".claude/*.md")
CONFIG = ".pymarkdown.json"
GIT = shutil.which("git") or "git"


def _git(*args):
    done = subprocess.run([GIT, *args], capture_output=True, text=True, check=False)
    return done.returncode, done.stdout


def _names(stdout):
    return [n for n in stdout.split("\0") if n]


def tracked():
    return _names(_git("ls-files", "-z", "--", *PATHSPECS)[1])


def changed(base):
    """The tracked docs changed against `base`, or all of them."""
    everything = tracked()
    if _git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")[0] != 0:
        return everything
    if _names(_git("diff", "--name-only", "-z", base, "--", CONFIG)[1]):
        return everything
    diff = _names(_git("diff", "--name-only", "-z", "--diff-filter=ACMR", base, "--", *PATHSPECS)[1])
    return [n for n in everything if n in set(diff)]


def main(argv=None):
    parser = argparse.ArgumentParser(description="the markdown files to lint")
    parser.add_argument("--base", default=None)
    args = parser.parse_args(argv)
    names = tracked() if args.base is None else changed(args.base)
    sys.stdout.write("".join(f"{n}\0" for n in names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
