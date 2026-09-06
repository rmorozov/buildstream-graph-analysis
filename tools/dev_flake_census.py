"""`UX-691`: which files the flake ledger says need a task.

    python3 tools/dev_flake_census.py                 # the top three

A file the drift gate reports keeps landing in `tests/flake_ledger.json`
(`dev_tier_drift.py --adopt-flake`) whether the run confirms it as
drift or only sees it once. Three appearances is the line between "one
excursion" and "a file nobody is tracking" (the task's own Motivation).
`unaccounted` names every file at or past that line with neither a
filed backlog row nor a declared reason beside it in the ledger; `top`
is what the round document's Standing prints.
"""
import argparse
import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
LEDGER = REPO / "tests" / "flake_ledger.json"
SCENARIOS = REPO / "docs" / "backlog" / "scenarios"

#: The task's own number: two excursions could be one afternoon; a
#: third is what tells a flake apart from noise.
EXCURSION_FLOOR = 3


def load(path=LEDGER):
    if not path.is_file():
        return {"entries": [], "declared": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def counts(document):
    """`{file: excursion count}` - every ledger row counts, confirmed or not."""
    return collections.Counter(row["file"]
                               for row in document.get("entries") or [])


def filed(name, scenarios=SCENARIOS):
    """Whether some task file under `scenarios` names this test file."""
    if not scenarios.is_dir():
        return False
    return any(name in task.read_text(encoding="utf-8")
              for task in scenarios.glob("*.md"))


def unaccounted(document, scenarios=SCENARIOS):
    """Files at or past `EXCURSION_FLOOR` with no filed task or declared
    reason, worst first - `[(file, count)]`.

    `declared` is the ledger's own `{file: reason}` map, for an
    excursion that is not worth a task.
    """
    declared = document.get("declared") or {}
    found = [(name, n) for name, n in counts(document).items()
             if n >= EXCURSION_FLOOR and not declared.get(name)
             and not filed(name, scenarios)]
    return sorted(found, key=lambda row: -row[1])


def top(document, n=3):
    """The ledger's `n` most-excursed files, for the round document's
    Standing."""
    return counts(document).most_common(n)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--top", type=int, default=3,
                        help="print the ledger's N most-excursed files")
    args = parser.parse_args(argv)
    document = load()
    for name, n in top(document, args.top):
        print(f"{name}  {n} excursion(s)")
    missing = unaccounted(document)
    if missing:
        print(f"\n{len(missing)} file(s) at or past {EXCURSION_FLOOR} "
              f"excursions with no filed task or declared reason:",
              file=sys.stderr)
        for name, n in missing:
            print(f"  {name}  {n} excursion(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
