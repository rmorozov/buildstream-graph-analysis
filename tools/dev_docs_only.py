#!/usr/bin/env python3
"""UX-956: whether a diff is docs only - the verdict CI's `changes` job
hands every other job, so it imports nothing outside the stdlib.

    git diff --name-only REF | python3 tools/dev_docs_only.py --event E

A path is docs when it is under `docs/` or ends `.md` outside `tests/`
(a fixture is test input); anything else is code, and one code path
sends the run to the full workflow. So does anything but a
`pull_request` event, or an empty list - which is what a failed
`git diff` leaves. `tools/dev_docs_lane.py` is what the lane runs.
"""
import argparse
import sys


def is_docs(path: str) -> bool:
    """Docs by where it is and what it is; never by what it contains."""
    if path.startswith("tests/"):
        return False
    return path.startswith("docs/") or path.endswith(".md")


def docs_only(paths, event="pull_request") -> bool:
    """True only for a pull request whose every changed path is docs."""
    paths = [p.strip() for p in paths if p.strip()]
    return event == "pull_request" and bool(paths) and all(map(is_docs, paths))


def main(argv=None, stdin=None) -> int:
    parser = argparse.ArgumentParser(description="is this diff docs only")
    parser.add_argument("--event", default="pull_request")
    args = parser.parse_args(argv)
    verdict = docs_only((stdin or sys.stdin).read().splitlines(), args.event)
    print(f"docs_only={'true' if verdict else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
