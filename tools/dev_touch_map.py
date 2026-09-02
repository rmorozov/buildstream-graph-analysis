#!/usr/bin/env python3
"""UX-524: which test files executed which module, measured in CI.

`dev_touching` selects by grep, and says why: a test that reads a
document or a fixture imports nothing from it, so an import graph would
miss half this suite. The price is the other direction - a Python test
that reaches a module through an import chain and never spells its
name. `UX-500`'s round counted two misses in five; `UX-522` closed the
census class, and this closes that one.

CI already runs the whole suite. With `--cov-context=test` the same run
records, per test, every module line it executed - the map the selector
is guessing at. It is **adopted from CI**, never recorded locally, for
`UX-447`'s reason about references from another clock: a laptop's run
covers what that laptop can run.
"""
import argparse
import collections
import json
import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
MAP = REPO / "tests/touch_map.json"

#: Only these are worth a row. A test's coverage of `tests/` is itself,
#: which the selector already knows, and site-packages is nobody's diff.
ROOTS = ("bga/", "tools/")


def _relative(path):
    try:
        return str(pathlib.Path(path).resolve().relative_to(REPO))
    except ValueError:
        return None


def read(database):
    """`{module: [test files]}` from one coverage database."""
    db = sqlite3.connect(str(database))
    try:
        rows = db.execute(
            "SELECT f.path, c.context FROM line_bits lb "
            "JOIN file f ON f.id = lb.file_id "
            "JOIN context c ON c.id = lb.context_id").fetchall()
    finally:
        db.close()
    found = collections.defaultdict(set)
    for path, context in rows:
        # Subsumed by the `tests/` check below - an empty context
        # splits to an empty guard, which starts with nothing. Kept
        # because a coverage database written without `--cov-context`
        # is *every* row like this, and saying so at the top is worth
        # more than one line. The mutation table records that it does
        # not discriminate.
        if not context:
            continue
        module = _relative(path)
        # The context is `<file>::<test>|<phase>`; the file is what a
        # selector runs, and one row per test would be a map nobody
        # could read at 5,900 tests.
        guard = context.split("::")[0]
        if module and module.startswith(ROOTS) and guard.startswith("tests/"):
            found[module].add(guard)
    return {module: sorted(guards) for module, guards in sorted(found.items())}


def adopt(existing, measured):
    """`UX-503`'s rule, one file over: add rows, rewrite none.

    A run that could not reach a module - no browser, no `bst` - would
    otherwise delete its row and quietly narrow the selector. Adding
    only is what makes this safe to run on every push.
    """
    merged = dict(existing)
    for module, guards in measured.items():
        merged[module] = sorted(set(merged.get(module, [])) | set(guards))
    return dict(sorted(merged.items()))


def load():
    """The committed map, or `{}` when there is none yet."""
    try:
        return json.loads(MAP.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("database", nargs="?", default=".coverage",
                        help="a coverage database written with --cov-context")
    parser.add_argument("--write", metavar="PATH",
                        help="write the map this run measured, and stop")
    parser.add_argument("--adopt", metavar="PATH",
                        help="merge a measured map into tests/touch_map.json")
    args = parser.parse_args(argv)

    if args.adopt:
        measured = json.loads(pathlib.Path(args.adopt).read_text())
        merged = adopt(load(), measured)
        MAP.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(f"{len(merged)} module(s), "
              f"{sum(len(v) for v in merged.values())} edge(s)")
        return 0

    measured = read(args.database)
    body = json.dumps(measured, indent=1, sort_keys=True) + "\n"
    if args.write:
        pathlib.Path(args.write).write_text(body, encoding="utf-8")
        print(f"{len(measured)} module(s), "
              f"{sum(len(v) for v in measured.values())} edge(s)")
        return 0
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
