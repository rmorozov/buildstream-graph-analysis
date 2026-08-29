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


# UX-232 split the backlog by liveness: open rows in README.md, closed
# ones verbatim in closed.md. Both are the backlog, so anything that
# reads a status reads both.
#
# `UX-387`: this tool read only the open index, and the guard that
# holds the same property read both. Measured when that was filed, the
# open table had 7 rows and `closed.md` had 379 - so `--check` was
# answering for 1.8% of the backlog and printing "0 problem(s)" for the
# other 98%. Round 61 hit it live: `UX-382`'s row moved to `closed.md`
# and its file's marker stayed 🔴, `--check` passed, and a full
# `make test-fast` two items later was what noticed.
#
# The readers below are the single implementation of that property.
# `tests/unit/test_docs_links_and_commands.py` imports them rather than
# keeping its own copy, because the two asserting one property by two
# readings is how they came to disagree in the first place.
STATUS_EMOJI = ("🔴", "🟡", "🟢", "⚪")
_TABLE_ROW = re.compile(r"^\|\s*UX-0*(\d+)\s*\|")
_FILE_ID = re.compile(r"^UX-0*(\d+)-")


def backlog_files():
    """Both halves of the backlog, read at call time.

    A module-level tuple would be captured at import and `--scenarios`
    rebinds `INDEX` and `CLOSED` after that, so a constant here would
    send every reader below at the real backlog while the caller
    believed it was pointed at a fixture.
    """
    return (INDEX, CLOSED)


def status_marker(text):
    """The status glyph in a cell or a header line, or `None`."""
    return next((emoji for emoji in STATUS_EMOJI if emoji in text), None)


def table_statuses():
    """`{item number: status cell}` across both backlog files.

    The two tables have different shapes on purpose - the open one is
    an index (id, title, topic, priority, serves, status), the closed
    one keeps its full narrative - so the status cell is found by
    *marker* rather than by column number, which is the only thing both
    promise.
    """
    statuses = {}
    for path in backlog_files():
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _TABLE_ROW.match(line)
            if not match:
                continue
            cells = [cell.strip() for cell in
                     re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            marker = next((c for c in cells if c[:1] in "🔴🟡🟢⚪"), "")
            statuses[int(match.group(1))] = marker
    return statuses


def file_statuses():
    """`{item number: (filename, status line)}` from the task files."""
    statuses = {}
    for path in sorted(SCENARIOS.glob("UX-*.md")):
        match = _FILE_ID.match(path.name)
        if not match:
            continue
        header = path.read_text(encoding="utf-8").splitlines()[:8]
        line = next((line for line in header if "**Status:**" in line), None)
        statuses[int(match.group(1))] = (path.name, line)
    return statuses


def status_disagreements():
    """`UX-131`'s property: each row's glyph equals its file's glyph.

    Symmetric by construction - it compares the pair and does not care
    which half moved - so flipping either one alone is reported.
    """
    rows = table_statuses()
    problems = []
    for number, (name, line) in sorted(file_statuses().items()):
        if number not in rows:
            continue
        in_table = status_marker(rows[number])
        in_file = status_marker(line or "")
        if in_table != in_file:
            problems.append(
                f"UX-{number}: table says {in_table}, {name} says {in_file}")
    return problems


#: What `--check` holds, in the order it prints them. `UX-387`: the
#: output used to be a bare "0 problem(s)", which reads the same for "I
#: checked four properties and all passed" and "I checked three and the
#: fourth is not implemented" - and a contributor cannot tell those
#: apart, which is how the missing one went unnoticed for as long as it
#: did.
CHECKS = (
    ("every row's status glyph matches its task file's",
     lambda: status_disagreements()),
    ("no closed row is left in the open index",
     lambda: _closed_rows_left_open()),
    ("the index's open count matches its table",
     lambda: _open_count_disagreement()),
)


def _closed_rows_left_open():
    problems = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\| (UX-\d+) \|", line)
        if not match:
            continue
        marker = line.rsplit("|", 2)[1].strip()
        declared = re.search(r"\*\*Status:\*\* (\S+)",
                             task_file(match.group(1)).read_text("utf-8"))
        declared = declared.group(1) if declared else "?"
        if marker == "🟢" or declared == "🟢":
            problems.append(f"{match.group(1)}: row {marker}, file {declared} "
                            "- a closed row belongs in closed.md")
    return problems


def _open_count_disagreement():
    text = INDEX.read_text(encoding="utf-8")
    open_count = len(re.findall(r"^\| UX-\d+ \|", text, re.M))
    stated = re.search(r"\*\*(\d+) open\*\*", text)
    if stated and int(stated.group(1)) != open_count:
        return [f"the index says {stated.group(1)} open; "
                f"{open_count} rows are in the table"]
    return []


def check():
    """Every place the two copies of a status can disagree."""
    return [problem for _what, run in CHECKS for problem in run()]


def _shown(path: pathlib.Path) -> str:
    """A path to print: repo-relative when it is in the repo.

    `--scenarios` accepts a directory anywhere - a `tmp_path` copy is
    the whole point of it - and `relative_to` raises on one that is
    outside. It raised *after* the row was written, so the move
    succeeded and the command still exited with a traceback.
    """
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


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
    # The verdict is this function's to write, so a note that already
    # opens with one is not doubled. `🟢 Done — 🟢 Done — …` is what the
    # first row written from a note drafted elsewhere looked like -
    # caught, again, by reading the row it produced.
    said = note.strip()
    for opener in ("🟢 Done —", "🟢 Done -", "Done —", "Done -"):
        if said.startswith(opener):
            said = said[len(opener):].strip()
            break
    closed_row = (f"| {uid} | {scenario} | {priority} | {serves} | "
                  f"🟢 Done — {said} | [{uid}]({path.name}) |")

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
          f"    grep '^| {uid} |' {_shown(CLOSED)}")
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
        problems = []
        for what, run in CHECKS:
            found = run()
            problems.extend(found)
            print(f"  {'FAIL' if found else 'ok  '}  {what}"
                  + (f" - {len(found)} problem(s)" if found else ""))
            for problem in found:
                print(f"          {problem}")
        rows = len(table_statuses())
        print(f"{len(problems)} problem(s) over {len(CHECKS)} propert(y/ies), "
              f"{rows} backlog row(s)")
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
