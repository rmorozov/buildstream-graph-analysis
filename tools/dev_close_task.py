#!/usr/bin/env python3
"""UX-336: the mechanical tail of closing a task, scaffolded.

Closing a `UX-*` row is four edits in three files, plus an Outcome
section whose headings are the same every time. None of it is judgement
— the judgement is the *content* — and all of it has drifted: round 11
found a row 🟢 over a 🔴 file, round 13 found five, and every round
since has hand-retyped the index counts.

So this does the parts that are mechanical and refuses to do the parts
that are not:

    python tools/dev_close_task.py UX-329 --outcome --round 47
    python tools/dev_close_task.py UX-329 --move --note "one line for closed.md"
    python tools/dev_close_task.py --check

`--outcome` prints a skeleton to paste and fill: it writes the headings
the `verify` skill requires and leaves every measurement blank, because
a helper that pre-filled them would be inviting exactly the unmeasured
claim this repository keeps finding.

`--move` performs the row move, flips both copies of the status marker,
and adjusts the two index counts. It refuses when the task file has no
Outcome section — closing a row for work with nothing written down is
the failure mode, not the convenience.
"""
import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCENARIOS = REPO / "docs/backlog/scenarios"
INDEX = SCENARIOS / "README.md"
CLOSED = SCENARIOS / "closed.md"

OUTCOME_SKELETON = """
## Outcome (round {round}, {date}) — 🟢 Done

### The gap, measured

```text
<paste the command and its real output - what was wrong, before>
```

### After

```text
<paste the same command, after>
```

### <what the fix had to be, and why that shape>

### Mutations verified red and reverted ({n})

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| A1 | <the exact defect this item was filed for, reintroduced> | <clause(s), with the count> |
| A2 | <the opposite direction, so the fix is a distinction and not a rename> | <clause(s)> |

### Deviation from the Required Fix

- <"None." is a valid answer and has to be written, not omitted>
"""


def task_file(uid: str) -> pathlib.Path:
    number = int(re.sub(r"[^0-9]", "", uid))
    matches = sorted(SCENARIOS.glob(f"UX-{number:04d}-*.md"))
    if not matches:
        raise SystemExit(f"no task file for {uid}")
    return matches[0]


def open_row(uid: str):
    """`(line, topic)` for the row in the open table, or `(None, None)`."""
    short = f"UX-{int(re.sub(r'[^0-9]', '', uid))}"
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {short} |"):
            cells = [c.strip() for c in line.split("|")]
            return line, cells[3]
    return None, None


def check():
    """Every place the two copies of a status can disagree."""
    text = INDEX.read_text(encoding="utf-8")
    problems = []
    for line in text.splitlines():
        match = re.match(r"^\| (UX-\d+) \|", line)
        if not match:
            continue
        marker = line.rsplit("|", 2)[1].strip()
        path = task_file(match.group(1))
        head = path.read_text(encoding="utf-8")
        declared = re.search(r"\*\*Status:\*\* (\S+)", head)
        declared = declared.group(1) if declared else "?"
        if marker == "🟢" or declared == "🟢":
            problems.append(f"{match.group(1)}: row {marker}, file {declared} "
                            "- a closed row belongs in closed.md")
        elif marker != declared:
            problems.append(f"{match.group(1)}: row {marker} != file {declared}")

    open_count = len(re.findall(r"^\| UX-\d+ \|", text, re.M))
    stated = re.search(r"\*\*(\d+) open\*\*", text)
    if stated and int(stated.group(1)) != open_count:
        problems.append(f"the index says {stated.group(1)} open; "
                        f"{open_count} rows are in the table")
    return problems


def move(uid: str, note: str) -> int:
    path = task_file(uid)
    body = path.read_text(encoding="utf-8")
    if "## Outcome" not in body:
        print(f"{path.name} has no Outcome section. Write it first - a row "
              f"moved without one is the thing the guides warn about.",
              file=sys.stderr)
        return 2

    line, topic = open_row(uid)
    if line is None:
        print(f"{uid} has no row in the open table (already closed?).",
              file=sys.stderr)
        return 2

    body = re.sub(r"\*\*Status:\*\* \S+( Not Started| In Progress)?",
                  "**Status:** 🟢 Done", body, count=1)
    path.write_text(body, encoding="utf-8")

    cells = [c for c in line.split("|")]
    scenario, priority, serves = cells[2].strip(), cells[4].strip(), cells[5].strip()
    # The last cell is the **task file link**, not the scenario text
    # again. The first draft of this function copied the scenario into
    # both and the row rendered with a duplicated title - caught by
    # reading the row it produced, which is why `--move` prints a line
    # telling you to.
    closed_row = (f"| {uid} | {scenario} | {priority} | {serves} | "
                  f"🟢 Done — {note} | [{uid}]({path.name}) |")

    text = INDEX.read_text(encoding="utf-8")
    text = text.replace(line + "\n", "")
    stated = re.search(r"\*\*(\d+) open\*\*, (\d+) closed", text)
    if stated:
        text = text.replace(stated.group(0),
                            f"**{int(stated.group(1)) - 1} open**, "
                            f"{int(stated.group(2)) + 1} closed")
    row = re.search(rf"^\| {topic} \| (\d+) \| (\d+) \|$", text, re.M)
    if row:
        text = text.replace(row.group(0),
                            f"| {topic} | {int(row.group(1)) - 1} | {row.group(2)} |")
    INDEX.write_text(text, encoding="utf-8")

    # After the **last table row**, not at the end of the file:
    # `closed.md` carries per-round narrative sections below its table,
    # and the first draft appended into those - which broke the table
    # and was caught by `test_no_table_is_split_by_a_blank_line`.
    closed = CLOSED.read_text(encoding="utf-8").splitlines()
    last = max(i for i, text in enumerate(closed) if text.startswith("| UX-"))
    closed.insert(last + 1, closed_row)
    CLOSED.write_text("\n".join(closed) + "\n", encoding="utf-8")
    print(f"{uid}: status flipped, row moved, counts adjusted.\n"
          f"  Read the row it just wrote. The scenario text is copied from "
          f"the open row and usually wants rewriting into what was *found*, "
          f"and this function's own first run produced a malformed row -\n"
          f"    grep '^| {uid} |' {CLOSED.relative_to(REPO)}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("uid", nargs="?", help="e.g. UX-329")
    parser.add_argument("--outcome", action="store_true",
                        help="print the Outcome skeleton to fill in")
    parser.add_argument("--round", default="NN")
    parser.add_argument("--date", default="YYYY-MM-DD")
    parser.add_argument("--mutations", type=int, default=2)
    parser.add_argument("--move", action="store_true",
                        help="flip both markers, move the row, fix the counts")
    parser.add_argument("--note", default="",
                        help="the one-line narrative for the closed.md row")
    parser.add_argument("--check", action="store_true",
                        help="report every status/count disagreement")
    # UX-336: so a guard can exercise `--move` against a copy. Found by
    # falsifying this file's own refusal: with the Outcome check removed
    # the clause *performed* the move, on the real backlog. A test that
    # edits the repository when the code under test misbehaves is a
    # worse instrument than the thing it is testing.
    parser.add_argument("--scenarios", default=None,
                        help="the scenarios directory to act on "
                             "(default: this repository's)")
    args = parser.parse_args(argv)

    if args.scenarios:
        global SCENARIOS, INDEX, CLOSED
        SCENARIOS = pathlib.Path(args.scenarios).resolve()
        INDEX = SCENARIOS / "README.md"
        CLOSED = SCENARIOS / "closed.md"

    if args.check:
        problems = check()
        for problem in problems:
            print(problem)
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if not args.uid:
        parser.error("a UX id is required unless --check is given")
    if args.outcome:
        print(OUTCOME_SKELETON.format(round=args.round, date=args.date,
                                      n=args.mutations))
        return 0
    if args.move:
        if not args.note:
            parser.error("--move needs --note: the closed.md row is a "
                         "sentence about what was found, and nothing can "
                         "write it for you")
        return move(args.uid, args.note)
    parser.error("give --outcome, --move or --check")


if __name__ == "__main__":
    sys.exit(main())
