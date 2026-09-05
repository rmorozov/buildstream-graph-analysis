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

import dev_tier_drift

REPO = pathlib.Path(__file__).resolve().parents[1]
MAP = REPO / "tests/touch_map.json"

#: Only these are worth a row. A test's coverage of `tests/` is itself,
#: which the selector already knows, and site-packages is nobody's diff.
ROOTS = ("bga/", "tools/")

#: The module that reads the map when the selector runs. Its own row
#: names the guards that pay for whatever the map grows to, so `readers`
#: below is derived from the map rather than typed beside it.
READER = "tools/dev_touching.py"


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


def readers(merged):
    """The guards whose cost this map sets: `READER`'s own row in it."""
    return sorted(merged.get(READER, ()))


def retire(reference, names):
    """`(document, retired)` - `names` dropped from the drift reference.

    `UX-662`: adopting a map changes what the guards that read it cost,
    and a number recorded before it is not one they can be judged
    against. Dropping the entry does not lose it. `dev_tier_drift`
    carries a file with no entry out as `recorded` rather than
    `confirmed`, so the gate prints it instead of failing on it, and the
    next reference candidate re-records it on that run's own clock -
    `--adopt` adds exactly the names the reference lacks. One run
    unjudged, against a branch going red for a cost it did not add.
    """
    files = reference.get("files") or {}
    retired = sorted(name for name in names if name in files)
    if not retired:
        return reference, []
    document = dict(reference)
    for key in ("files", "samples"):
        if key in document:
            document[key] = {name: value
                             for name, value in document[key].items()
                             if name not in set(retired)}
    return document, retired


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
        before = load()
        merged = adopt(before, measured)
        MAP.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(f"{len(merged)} module(s), "
              f"{sum(len(v) for v in merged.values())} edge(s)")
        if merged != before:
            reference = json.loads(
                dev_tier_drift.CI_REFERENCE.read_text(encoding="utf-8"))
            document, retired = retire(reference, readers(merged))
            if retired:
                dev_tier_drift.CI_REFERENCE.write_text(
                    json.dumps(document, indent=2) + "\n", encoding="utf-8")
                print(f"retired {len(retired)} drift entr"
                      f"{'y' if len(retired) == 1 else 'ies'} the map's "
                      f"readers own, for the next run to re-record:")
                for name in retired:
                    print(f"  {name}")
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
