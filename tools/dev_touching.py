#!/usr/bin/env python3
"""UX-336: the tests that touch what you just changed.

The inner loop was "run a tier and wait". The small tier is the fastest
one and it still runs 160 files; small+medium — the widest tier a
machine without `bst` can finish — was measured at **335 s**, which is
nobody's inner loop. But a change almost never touches 160 files' worth
of behaviour: it touches one or two modules, and the tests that can see
that change are the ones that name them.

So this maps the working diff to a test set by **grep over the path,
the dotted name and the `from x import y` line**, not by import graph:

* an import graph would miss `tests/unit/test_docs_links_and_commands.py`
  reading `docs/guides/cli.md`, and half this suite's guards are of that
  kind — they read a document or a fixture and import nothing from it;
* a grep over 200-odd test files costs milliseconds, and the whole point
  is to be faster than the thing it replaces.

**It is a selector, not a gate.** `make test` before a commit is
unchanged; what this buys is the twenty runs *before* that one. Three
sets, unioned, `--why` naming which chose each: the **grep**; the
**census** (`UX-522`), guards that read the tree and name no module;
and the **map** (`UX-524`), what CI measured each test executing. A
green run prints one line (`UX-525`) - pytest output is 10-16% of a
track's tokens; red prints everything, and `--loud` always does.
"""
import argparse
import functools
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


# `UX-605`: an entry naming more test files than the selector's own
# bound is not a selection. Measured on the map CI adopted in
# `0bc5aff`: **38 of 85** modules named 100+ of 449 test files, topping
# out at `bga/progress.py` with 200, because `--cov-context=test`
# attributes a module's *import-time* lines to every test that imports
# it. 25 is `test_the_loop_stays_fast.py`'s bound on the whole
# selection, so an entry alone at that width can never be one.
MAP_ENTRY_CAP = 25


def wide_entries(cap=None):
    """`{module: size}` for the map entries too wide to be a selection."""
    cap = MAP_ENTRY_CAP if cap is None else cap
    return {k: len(v) for k, v in touch_map().items() if len(v) > cap}


def touch_map():
    """`UX-524`: `{module: [test files]}`, measured by CI's own run.

    Empty when the file is absent, which is the honest answer on a
    clone that has not fetched it: the selection falls back to the grep
    and the census, and `--why` says so.
    """
    try:
        import json

        return json.loads((TESTS / "touch_map.json").read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        return {}


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


def import_pattern(path: str):
    """`UX-624`: the `from <package> import <module>` spelling, as a regex.

    `tokens_for` spells a module `bga.schemas`, and a test that uses it
    writes `from bga import schemas` - a form no token matches, so the
    grep half missed 253 real import edges and the map was covering for
    them. `None` when the path is not an importable submodule.
    """
    if not path.endswith(".py"):
        return None
    p = pathlib.Path(path)
    if p.stem.startswith("__") or not p.parent.parts:
        return None
    # The optional group is the `from bga import contracts, schemas`
    # form: 25 of those edges hung on which name was written first.
    return r"from\s+%s\s+import\s+\(?\s*(?:[\w\s,]*?,\s*)?%s\b" % (
        re.escape(".".join(p.parent.parts)), re.escape(p.stem))


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

    `UX-645`: the census is a **floor**, not a selection - the same 11
    files under every one of the 87 mapped modules. It is inside the
    width figure because those files run, and `naming(...)` below is
    the other half, for the questions that are about the change.
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
        mapped = touch_map().get(path, ())
        # `UX-605`: too wide to mean anything - fall back to the grep
        # and the census, which is what a clone without the map does.
        if len(mapped) > MAP_ENTRY_CAP:
            mapped = ()
        for candidate in mapped:
            if (REPO / candidate).exists():
                chosen[candidate] = True
                why.setdefault(candidate, []).append("map")
        spellings = [re.escape(t) for t in sorted(tokens)]
        importing = import_pattern(path)
        if importing:
            spellings.append(importing)
        pattern = re.compile("|".join(spellings))
        for candidate in test_files():
            try:
                text = (REPO / candidate).read_text(encoding="utf-8")
            except OSError:
                continue
            if pattern.search(text):
                chosen[candidate] = True
                why.setdefault(candidate, []).append(path)
    return sorted(chosen), why


def naming(selected, why):
    """`UX-645`: the half of a selection that names the change.

    A file the census alone chose is under every module equally, so it
    cannot answer "does anything guard this diff". A file with no
    recorded reason counts as naming: that is the shared-harness
    fallback, which keys its one reason under `"*"` and really does
    name everything.
    """
    return [name for name in selected if why.get(name, ["*"]) != ["census"]]


# `UX-632`: the documents carrying the figure. `CLAUDE.md` is not one -
# `UX-471`'s guard there forbids a count the tree changes under it, so
# that row defers to the guide the way its `make test` row already does.
COST_SITES = ("docs/contributing/fixing-guide.md",)

#: The sentence those documents carry, and the shape `--write` finds.
FIGURE = "{min}-{max} of {files} test files, median {median}"
FIGURE_RE = re.compile(r"\d+-\d+ of \d+ test files, median \d+")


@functools.lru_cache(maxsize=1)
def spread():
    """What a one-module diff selects, over every module the map names.

    Seconds are a property of the machine (`UX-551`) and this is a
    property of the tree, which is why it is the figure the documents
    carry. Cached: it is 85 selections over the whole suite, and the
    guard that reads it asks four times.

    `UX-645`: the census floor is **inside** these numbers, because the
    figure is what pytest is handed. Every selection carries all of it,
    so no reading here can be below `len(census_set())` - measured, the
    minimum is that floor exactly.
    """
    sizes = sorted(len(select([module])[0]) for module in touch_map())
    if not sizes:
        raise RuntimeError("the touch map is empty; there is no population")
    return {"min": sizes[0], "max": sizes[-1],
            "median": sizes[len(sizes) // 2],
            "modules": len(sizes), "files": len(test_files())}


def figure(values=None):
    """The cost row's sentence, from `spread()`."""
    return FIGURE.format(**(values or spread()))


def write_figure(text: str, row: str) -> str:
    """`text` with every stale copy of the figure replaced by `row`."""
    return FIGURE_RE.sub(row, text)


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
    parser.add_argument("--staged", action="store_true",
                        help="select from the staged diff, not the desk")
    parser.add_argument("--loud", action="store_true",
                        help="print pytest's output even when it passes")
    parser.add_argument("--spread", action="store_true",
                        help="print what a one-module diff selects, over "
                             "every module the map names")
    parser.add_argument("--write", action="store_true",
                        help="with --spread, put that figure in the "
                             "documents that price this loop")
    args, rest = parser.parse_known_args(argv)

    if args.spread:
        row = figure()
        print(row)
        for name in COST_SITES:
            path = REPO / name
            text = path.read_text(encoding="utf-8")
            fixed = write_figure(text, row)
            if fixed == text:
                continue
            if args.write:
                path.write_text(fixed, encoding="utf-8")
            print(f"{'rewrote' if args.write else 'stale'}: {name}",
                  file=sys.stderr)
        return 0

    changed = changed_files(args.base, staged=args.staged)
    if not changed:
        print("Nothing changed against HEAD - `make test-touching` has "
              "nothing to select. Run `make test-small` for the tier.",
              file=sys.stderr)
        return 0

    selected, why = select(changed)
    named = naming(selected, why)
    if not named:
        # `UX-645`: read off the naming half, not the whole selection.
        # The census floor made this unreachable - a module no test
        # names still selects 11 files and reported as a pass.
        print(f"No test file names any of {len(changed)} changed file(s):\n  "
              + "\n  ".join(changed)
              + "\n\nThat is a finding, not a pass: run `make test-small`, and "
                "if the change really has no guard, that is what to fix.",
              file=sys.stderr)
        if not selected:
            return 0

    if args.why:
        # `UX-557`: the shared-harness fallback keys its one reason
        # under `"*"`, so a per-name lookup printed `None` for all 424
        # files - the answer existed and no reader could reach it.
        for name in selected:
            print(f"{name}\n    <- {why.get(name, why.get('*'))}")
        print(f"({len(selected) - len(named)} of {len(selected)} are the "
              f"census floor, the same under every module - UX-645)",
              file=sys.stderr)
        for module, size in sorted(wide_entries().items()):
            print(f"(map entry for {module} ignored: {size} files, over the "
                  f"{MAP_ENTRY_CAP} bound - UX-605)", file=sys.stderr)
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
    # `UX-645`: the two populations, so the count is not read as if it
    # were all about the diff.
    print(f"{len(selected)} file(s) selected "
          f"({len(selected) - len(named)} census + {len(named)} naming the "
          f"change) · {last_line(done.stdout)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
