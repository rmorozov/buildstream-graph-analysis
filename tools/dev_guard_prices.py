#!/usr/bin/env python3
"""UX-1122: what each guard costs per pull request, and which to retire.

    python tools/dev_guard_prices.py [--n 10] [--catches catches.json]

Joins `tests/ci_reference.json`'s seconds per file to the `**Guard:**`
map (`dev_area_pages.guard_files`) and to each file's last catch, and
prints a table by seconds of every file that is a candidate:
"needs owner" (named by no task), "scheduled lane" (a recorded last
catch older than N rounds), "confirm inferred" (an `inferred r149`
owner, confirmed before it justifies a move). A file caught within N
rounds, or owned with no catch recorded, is not listed. `--catches` is a JSON map of test path
to the round number of its last true catch; no such record exists yet,
so by default only "needs owner" and "confirm inferred" appear. It
proposes; nothing moves without a row, and nothing is deleted.
"""

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import dev_area_pages
import dev_records

REFERENCE = "tests/ci_reference.json"
SCENARIOS = REPO / "docs/backlog/scenarios"


def proposals(prices, guards, last_catch, current_round, n=10):
    """Rows `(path, seconds, owners, last catch, proposal)` by seconds,
    highest first. `guards` maps a test file's basename to
    `[(task id, kind)]`; `last_catch` maps a path to a round or None."""
    rows = []
    for path, seconds in prices.items():
        owners = guards.get(pathlib.PurePath(path).name, [])
        named = [(uid, kind) for uid, kind in owners if kind != "none"]
        last = last_catch.get(path)
        old = last is not None and current_round - last > n
        if not named:
            proposal = "needs owner"
        elif all(kind == "inferred" for _, kind in named):
            if last is not None and not old:
                continue
            proposal = "confirm inferred"
        elif old:
            proposal = "scheduled lane"
        else:
            continue  # unrecorded is no evidence, not quiet
        rows.append((path, seconds, [uid for uid, _ in named], last, proposal))
    return sorted(rows, key=lambda row: (-row[1], row[0]))


def guard_map(scenarios=SCENARIOS):
    """`{test basename: [(task id, kind)]}` over every task file."""
    found = {}
    for path in sorted(scenarios.glob("UX-*.md")):
        uid = "-".join(path.name.split("-", 2)[:2])
        names, kind = dev_area_pages.guard_files(path.read_text(encoding="utf-8"))
        if kind in ("named", "inferred"):
            for name in names:
                found.setdefault(name, []).append((uid, kind))
    return found


def current_round(audits=REPO / "docs/audits"):
    rounds = [int(m.group(1)) for p in audits.glob("round-*.md") if (m := re.fullmatch(r"round-(\d+)\.md", p.name))]
    return max(rounds, default=0)


def table(rows, n):
    lines = [f"| file | seconds | owner task(s) | last catch (N={n}) | proposal |", "|---|---|---|---|---|"]
    for path, seconds, owners, last, proposal in rows:
        lines.append(
            f"| {path} | {seconds} | {', '.join(owners) or '-'} | "
            f"{'round ' + str(last) if last is not None else 'unrecorded'}"
            f" | {proposal} |"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--n", type=int, default=10, help="rounds a guard may go without a catch")
    parser.add_argument("--catches", type=pathlib.Path, help="JSON {test path: round of its last catch}")
    args = parser.parse_args(argv)
    prices = json.loads(dev_records.load(REFERENCE))["files"]
    catches = json.loads(args.catches.read_text()) if args.catches else {}
    rows = proposals(prices, guard_map(), catches, current_round(), args.n)
    print(table(rows, args.n))
    print(
        f"\n{len(rows)} of {len(prices)} files proposed; "
        f"{sum(row[1] for row in rows):.0f} of {sum(prices.values()):.0f} CPU-s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
