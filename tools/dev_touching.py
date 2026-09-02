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

`UX-522`: a **census** guard reads the tree and names no module, so it
is unioned in unconditionally; `--why` says which set chose each file.
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


def census_set():
    """`UX-522`: the guards a grep can never select, run every time.

    A census guard's subject is the **tree** - the register cap over
    every task file, the skip census over every guard, the context map
    over every module - so it names none of them and no diff can point
    at it. Round 75 measured the cost: of five defects the per-item
    suite caught, `test-touching` could not have named two, and both
    were this class.

    Declared in `tests/tiers.py` and checked against a derivation, so
    the list is auditable rather than typed:
    `tests/unit/test_the_selector_carries_the_census.py`. Measured at
    **10.80s** for 272 tests at `-n auto` - the price of the inner
    loop never being wrong about this class again.
    """
    sys.path.insert(0, str(TESTS))
    import tiers
    return [f for f in tiers.CENSUS if (REPO / f).exists()]


def changed_files(base=None, staged=False):
    """The working diff, staged and unstaged, plus untracked files.

    `staged=True` narrows to what a commit would actually carry -
    `UX-522`'s hook, which runs at the commit and should judge the
    commit rather than the desk it is made from.
    """
    if staged:
        argv = ["git", "diff", "--cached", "--name-only"]
    elif base:
        argv = ["git", "diff", "--name-only", base]
    else:
        argv = ["git", "diff", "--name-only", "HEAD"]
    out = subprocess.run(argv, capture_output=True, text=True, cwd=REPO)
    files = [line for line in out.stdout.splitlines() if line.strip()]
    if not staged:
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
        # `UX-522`: not `__init__`. Every package has one, and the stem
        # matched any test mentioning a dunder-init - measured, fifteen
        # `__init__.py` files each "selected" the skip census, which is
        # a guard about skip reasons. A false edge in `--why` is worse
        # than a missing one: it says the selector saw something it did
        # not.
        if path.startswith(("bga/", "tools/")) and "_" in stem \
                and not stem.startswith("__"):
            tokens.add(stem)
    else:
        tokens.add(pathlib.Path(path).name)
    return {token for token in tokens if len(token) > 3}


def test_files():
    return sorted(
        str(p.relative_to(REPO))
        for p in TESTS.rglob("test_*.py")
        if "__pycache__" not in p.parts)


def select(changed, census=True):
    """The test files to run, and why each was chosen.

    `census=False` asks for the grep half alone. Only the derivation in
    `test_the_selector_carries_the_census.py` wants that: it computes
    which guards a grep can never reach, and calling the whole selector
    to answer that would make every census file reachable by itself.
    """
    everything = [c for c in changed
                  if any(c == e or c.startswith(e) for e in EVERYTHING)]
    if everything:
        return sorted(test_files()), {"*": f"shared harness changed: {everything}"}

    chosen, why = {}, {}
    for name in (census_set() if census else ()):
        chosen[name] = True
        why.setdefault(name, []).append("census")
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default=None,
                        help="diff against this ref instead of HEAD")
    parser.add_argument("--list", action="store_true",
                        help="print the selected files and exit")
    parser.add_argument("--why", action="store_true",
                        help="print what selected each file")
    parser.add_argument("--staged", action="store_true",
                        help="select from the staged diff, not the desk")
    args, rest = parser.parse_known_args(argv)

    changed = changed_files(args.base, staged=args.staged)
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

    print(f"{len(selected)} test file(s) name the {len(changed)} changed "
          f"file(s); running them.", file=sys.stderr)
    return subprocess.call(
        [sys.executable, "-m", "pytest", *selected, "-q", "-n", "auto", *rest],
        cwd=REPO, env={**os.environ, "BGA_TIER_ANY": "1"})


if __name__ == "__main__":
    sys.exit(main())
