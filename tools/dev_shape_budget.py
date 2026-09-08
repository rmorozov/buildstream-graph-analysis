#!/usr/bin/env python3
"""UX-690: the suite's shape, derived - and the budget it is held to.

Duration (`tests/tiers.py`) says nothing about *purpose*. Five
disjoint classes, checked in this order so a file lands in the first
that fits: **enormous** (`pytest.mark.bst`, a real `bst`/`bwrap`
build), **journey** (`journey` in its name - the documented path
walked end to end, whatever else it also does), **browser** (imports
`tests.browser`, boots a real Chrome over CDP), **sweep** (its
docstring opens `UX-400:`, the population swept at zero/one/many), and
**unit** - the default, one claim each.

Measured against `tests/ci_reference.json`: the browser share is
already past the Required Fix's 40% ceiling, and the journey count is
nowhere near one per published contract (`bga.contracts.ids()`). Both
are printed rather than hidden; only the browser share is a hard gate,
held to "never rises" against `tests/shape_ledger.json` - adopted by
a real run (`--adopt`), the shape `dev_sizes.py --adopt` holds its own
floor in, not typed into this file.
"""
import argparse
import functools
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"
CI_REFERENCE = TESTS / "ci_reference.json"
#: `tests/quality_reference.json`'s own directory and shape - a small
#: adopted-figure ledger, not a typed constant.
LEDGER = TESTS / "shape_ledger.json"
#: Points of drift the ledger absorbs before the guard reds - the same
#: role `UX-476`'s shift gives a duration reading.
TOLERANCE_PCT = 1.0

# `tests.browser`'s own docstring: a real browser over CDP, node's
# built-in client - the harness this class is named for booting.
_BST = re.compile(r"pytest\.mark\.bst\b")
_BROWSER = re.compile(
    r"^\s*(import (?:tests\.)?browser\b|from (?:tests\.)?browser import)",
    re.M)
_JOURNEY = re.compile(r"journey", re.I)
# UX-400's own file opens its docstring naming itself; nothing else
# does, so this is precise rather than a keyword sweep of "population".
_SWEEP = re.compile(r'^"""UX-400:')

#: Display order - the Required Fix's own row order (unit, sweep,
#: journey, browser, enormous). `classify()`'s precedence is different
#: (`enormous` first): a file this order lists last can still claim a
#: row earlier ones would otherwise take.
CLASSES = ("unit", "sweep", "journey", "browser", "enormous")

#: The Required Fix's own ceiling (`UX-690`) - printed beside the
#: measured share, never silently swapped in for it. Already exceeded
#: (see the Outcome); the ledger is the held line, not this number.
BROWSER_BUDGET_PCT = 40.0


def load_ledger():
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_ledger(share):
    LEDGER.write_text(
        json.dumps({"browser_share_pct": round(share, 1)}, indent=2) + "\n",
        encoding="utf-8")


def test_files():
    """Every collected test file, repo-relative - the `ls` population."""
    return sorted(str(p.relative_to(REPO)) for p in TESTS.rglob("test_*.py")
                  if "__pycache__" not in p.parts)


@functools.cache
def _text(rel):
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def classify(rel):
    """One of `CLASSES`, in the order the module docstring states."""
    text = _text(rel)
    if _BST.search(text):
        return "enormous"
    if _JOURNEY.search(pathlib.Path(rel).name):
        return "journey"
    if _BROWSER.search(text):
        return "browser"
    if _SWEEP.search(text):
        return "sweep"
    return "unit"


def shapes():
    """`{class: [file, ...]}` - a partition of `test_files()`."""
    found = {c: [] for c in CLASSES}
    for rel in test_files():
        found[classify(rel)].append(rel)
    return found


def ci_seconds():
    """`{file: seconds}` from the CI reference.

    Raises, naming the path, when it is missing or unreadable - `{}`
    read 0 seconds for every class and the browser guard passed on a
    reference that was not there to check against.
    """
    try:
        text = CI_REFERENCE.read_text(encoding="utf-8")
        return json.loads(text)["files"]
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError(
            f"{CI_REFERENCE.relative_to(REPO)} is missing or unreadable "
            f"({exc}) - the shape budget cannot be measured") from exc


def seconds_by_class(classes=None, ci=None):
    classes = shapes() if classes is None else classes
    ci = ci_seconds() if ci is None else ci
    return {c: sum(ci.get(f, 0.0) for f in files)
            for c, files in classes.items()}


def browser_share_pct(classes=None, ci=None):
    """The browser class's share of the CI reference's total seconds."""
    ci = ci_seconds() if ci is None else ci
    total = sum(ci.values())
    if not total:
        return 0.0
    return seconds_by_class(classes, ci)["browser"] / total * 100


def ledger_problems(classes=None, ci=None):
    """`[]` while the measured share holds the ledger's line within
    `TOLERANCE_PCT`; otherwise one message naming both numbers - or
    naming the CI reference when `ci_seconds()` cannot read it."""
    ledger = load_ledger()
    held = ledger.get("browser_share_pct")
    if held is None:
        return [f"no {LEDGER.name} - run `--adopt` first"]
    try:
        measured = browser_share_pct(classes, ci)
    except RuntimeError as exc:
        return [str(exc)]
    if measured > held + TOLERANCE_PCT:
        return [f"browser share {measured:.1f}% moved past the ledger's "
                f"{held:.1f}% (+{TOLERANCE_PCT:.0f} point tolerance) - "
                f"`--adopt` if this is a deliberate move, a filing "
                "otherwise"]
    return []


def published_contract_count():
    """`len(bga.contracts.ids())` - the count the `UX-233` guard family
    already calls `_published_schemas()`."""
    sys.path.insert(0, str(REPO))
    from bga import contracts
    return len(contracts.ids())


def table():
    """The shape table and its budget lines, for the round document's
    Standing (`dev_flake_census.py`'s `top()` is the same convention) -
    and what `dev_close_task.py --check` prints."""
    classes = shapes()
    ci = ci_seconds()
    secs = seconds_by_class(classes, ci)
    total = sum(ci.values())
    files = test_files()
    lines = ["shape         files   CI seconds    share"]
    for c in CLASSES:
        share = secs[c] / total * 100 if total else 0.0
        lines.append(f"{c:<13} {len(classes[c]):5d}   {secs[c]:9.1f}s   "
                      f"{share:5.1f}%")
    lines.append(f"{'total':<13} {len(files):5d}   {total:9.1f}s")
    journeys = len(classes["journey"])
    published = published_contract_count()
    held = load_ledger().get("browser_share_pct")
    lines.append(
        f"browser budget: {browser_share_pct(classes, ci):.1f}% measured, "
        f"{BROWSER_BUDGET_PCT:.0f}% the Required Fix states, "
        + (f"{held:.1f}% the ledger holds" if held is not None
           else "no ledger - run --adopt"))
    lines.append(
        f"journey budget: {journeys} file(s) measured, "
        f"{published} published contract(s) (`bga.contracts.ids()`) - "
        "not held; UX-690's Outcome names the gap")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--adopt", action="store_true",
                        help="write the measured browser share to the ledger")
    args = parser.parse_args(argv)
    if args.adopt:
        share = browser_share_pct()
        write_ledger(share)
        print(f"wrote {share:.1f}% to {LEDGER.relative_to(REPO)}")
        return 0
    print(table())
    return 0


if __name__ == "__main__":
    sys.exit(main())
