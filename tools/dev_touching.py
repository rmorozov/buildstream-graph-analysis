#!/usr/bin/env python3
"""UX-336: the tests that touch what you just changed.

The inner loop was "run a tier and wait". The small tier is the fastest
one and it still runs 160 files; small+medium — the widest tier a
machine without `bst` can finish — was measured at **335 s**, which is
nobody's inner loop. But a change almost never touches 160 files' worth
of behaviour: it touches one or two modules, and the tests that can see
that change are the ones that name them.

So this maps the working diff to a test set, by **grep, not by import
graph**. That choice is deliberate:

* an import graph would miss `tests/unit/test_docs_links_and_commands.py`
  reading `docs/guides/cli.md`, and half this suite's guards are of that
  kind — they read a document or a fixture and import nothing from it;
* a grep over 200-odd test files costs milliseconds, and the whole point
  is to be faster than the thing it replaces.

**It is a selector, not a gate.** A grep-derived set can miss a test
that exercises a module without naming it, so `make test` before a
commit is unchanged and the verify skill still requires it. What this
buys is the twenty runs *before* that one.

**A green run prints one line** (`UX-525`): pytest output is 10-16% of a
track's tokens. Red prints everything; `--loud` restores the old shape.
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"

# A change to one of these is a change to everything, and pretending
# otherwise would make the selector quietly wrong on exactly the days it
# matters most.
EVERYTHING = ("tests/conftest.py", "tests/tiers.py", "pyproject.toml",
              "Makefile", "tests/support/", "tests/dom_shim.mjs")


def changed_files(base=None):
    """The working diff, staged and unstaged, plus untracked files."""
    if base:
        argv = ["git", "diff", "--name-only", base]
    else:
        argv = ["git", "diff", "--name-only", "HEAD"]
    out = subprocess.run(argv, capture_output=True, text=True, cwd=REPO)
    files = [line for line in out.stdout.splitlines() if line.strip()]
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, cwd=REPO)
    files += [line for line in untracked.stdout.splitlines() if line.strip()]
    return sorted(set(files))


def tokens_for(path: str):
    """What a test file would have to say to be about this change.

    Three spellings, because the suite uses all three: the repository
    path (`docs/guides/cli.md`, `bga/findings.py`), the importable
    dotted name (`bga.findings`), and the bare stem (`findings`). The
    stem is the loose one and is only used for source modules, where a
    test naming `store_aggregate` is about `store_aggregate`.
    """
    tokens = {path}
    if path.endswith(".py"):
        dotted = path[:-3].replace("/", ".")
        tokens.add(dotted)
        stem = pathlib.Path(path).stem
        # The bare stem only when it is distinctive. `store_aggregate`
        # appears in a test because the test is about it; `findings`
        # appears in sixty because it is also an English word this
        # project uses constantly - measured, 57 files against 7.
        if path.startswith(("bga/", "tools/")) and "_" in stem:
            tokens.add(stem)
    else:
        tokens.add(pathlib.Path(path).name)
    return {token for token in tokens if len(token) > 3}


def test_files():
    return sorted(
        str(p.relative_to(REPO))
        for p in TESTS.rglob("test_*.py")
        if "__pycache__" not in p.parts)


def select(changed):
    """The test files to run, and why each was chosen."""
    everything = [c for c in changed
                  if any(c == e or c.startswith(e) for e in EVERYTHING)]
    if everything:
        return sorted(test_files()), {"*": f"shared harness changed: {everything}"}

    chosen, why = {}, {}
    for path in changed:
        # A changed test file runs itself, whatever else it mentions.
        if path.startswith("tests/") and pathlib.Path(path).name.startswith("test_"):
            chosen[path] = True
            why.setdefault(path, []).append("changed")
            continue
        tokens = tokens_for(path)
        if not tokens:
            continue
        pattern = re.compile("|".join(re.escape(t) for t in sorted(tokens)))
        for candidate in test_files():
            try:
                text = (REPO / candidate).read_text(encoding="utf-8")
            except OSError:
                continue
            if pattern.search(text):
                chosen[candidate] = True
                why.setdefault(candidate, []).append(path)
    return sorted(chosen), why


def last_line(text: str) -> str:
    """Pytest's summary line - the last non-empty one it printed."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1].strip("= ") if lines else "no output"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default=None,
                        help="diff against this ref instead of HEAD")
    parser.add_argument("--list", action="store_true",
                        help="print the selected files and exit")
    parser.add_argument("--why", action="store_true",
                        help="print what selected each file")
    parser.add_argument("--loud", action="store_true",
                        help="print pytest's output even when it passes")
    args, rest = parser.parse_known_args(argv)

    changed = changed_files(args.base)
    if not changed:
        print("Nothing changed against HEAD - `make test-touching` has "
              "nothing to select. Run `make test-small` for the tier.",
              file=sys.stderr)
        return 0

    selected, why = select(changed)
    if not selected:
        print(f"No test file names any of {len(changed)} changed file(s):\n  "
              + "\n  ".join(changed)
              + "\n\nThat is a finding, not a pass: run `make test-small`, and "
                "if the change really has no guard, that is what to fix.",
              file=sys.stderr)
        return 0

    if args.why:
        for name in selected:
            print(f"{name}\n    <- {why.get(name)}")
        return 0
    if args.list:
        print("\n".join(selected))
        return 0

    argv = [sys.executable, "-m", "pytest", *selected, "-q", "-n", "auto", *rest]
    env = {**os.environ, "BGA_TIER_ANY": "1"}
    if args.loud:
        print(f"{len(selected)} test file(s) name the {len(changed)} changed "
              f"file(s); running them.", file=sys.stderr)
        return subprocess.call(argv, cwd=REPO, env=env)
    done = subprocess.run(argv, cwd=REPO, env=env, capture_output=True, text=True)
    if done.returncode:
        # Red is the case a reader needs whole; only green is summarised.
        print(f"{len(selected)} test file(s) name the {len(changed)} changed "
              f"file(s); running them.", file=sys.stderr)
        sys.stdout.write(done.stdout)
        sys.stderr.write(done.stderr)
        return done.returncode
    print(f"{len(selected)} file(s) selected · {last_line(done.stdout)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
