#!/usr/bin/env python3
"""UX-872: the CI step's own check, as a real module rather than an
inline workflow one-liner.

`tests/unit/test_the_workflow_does_not_know_the_payload.py` (`UX-354`)
refuses a `run:` block that parses a `bga`-produced document and names
its keys itself - a step that goes through a publisher (or, as here, a
real committed script) cannot drift the way `bga compare` output has.

Asserts the named element's `jobserver_decisions` row (`plane2.json`,
UX-842/UX-871) reads `joined` with a real kind, not `unknown_kind` - the
junctioned cmake element's own defect class before UX-871.
"""
import json
import sys


def check(plane2_path, element):
    report = json.load(open(plane2_path, encoding="utf-8"))
    decisions = report.get("jobserver_decisions") or []
    rows = [row for row in decisions if row.get("element") == element]
    if not rows:
        return f"no jobserver_decisions row for {element!r}: {decisions}"
    row = rows[0]
    print(f"{element} decision: {row}")
    if row.get("decision") != "joined":
        return f"expected decision 'joined' for {element!r}, got {row}"
    if row.get("kind") in (None, "unknown_kind"):
        return f"expected a real kind for {element!r}, got {row}"
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    error = check(argv[0], argv[1])
    if error:
        sys.exit(error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
