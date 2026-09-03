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
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCENARIOS = REPO / "docs/backlog/scenarios"
INDEX = SCENARIOS / "README.md"
CLOSED = SCENARIOS / "closed.md"

#: `UX-497`'s budget, printed under the skeleton so a session sees it
#: while writing rather than when the guard reds. One copy:
#: `test_the_register_is_terse.py` reads this constant.
OUTCOME_CAP = 80

OUTCOME_SKELETON = """
## Outcome (round {round}, {date}) — 🟢 Done

**Premise:** held | falsified — <the Motivation's claim, measured. A Fix
option that turned out unavailable is a Deviation below, not this.>

### The gap, measured

```text
<the command, and its real output - what was wrong, before>
```

<one paragraph: what that output says. Not how it was found.>

### After

```text
<the same command, after>
```

<one paragraph: what changed, and the number that shows it.>

### Mutations verified red and reverted ({n})

| # | mutation | reddened |
|---|---|---|
| A1 | <the defect this item was filed for, reintroduced> | <clause(s), count> |
| A2 | <the opposite direction, so the fix is a distinction> | <clause(s), count> |

<any guard of your own that turned out not to discriminate, and why.
This repository has found several and each was worth writing down.>

### Deviation from the Required Fix

<one line. "None." is a valid answer and has to be written, not
omitted. A design you rejected is one line with the number that
rejected it - not a paragraph about the alternatives.>

```text
<make test, make lint - the real lines>
```

<!-- {cap} lines, held by
     test_the_register_is_terse.py::TestOutcomes. The four
     measurements are the point; the room around them is not. -->
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


#: `UX-454`: the words a status line may carry after its glyph.
#:
#: `move()` below rewrites the glyph **and the word**, keeping whatever
#: verdict prose follows an em-dash. It has to name every word it might
#: be replacing, including the closed ones - a pattern that names only
#: the open words matches the glyph alone against an already-closed
#: line and leaves the old word standing, which is how twenty-four
#: files came to say `🟢 Done Done`. `Fixed & Verified` is in the list
#: because 54 files use it and it would double the same way; `Done\.?`
#: because eight write a full stop.
STATUS_WORDS = ("Not Started", "In Progress", "Fixed & Verified", "Done")
_STATUS_WORD = re.compile(
    r"(?: (?:" + "|".join(re.escape(w) for w in STATUS_WORDS) + r")\.?)*")
_ONE_STATUS_WORD = re.compile(
    r"(?:" + "|".join(re.escape(w) for w in STATUS_WORDS) + r")\.?")
_STATUS_LINE = re.compile(
    r"\*\*Status:\*\* (\S+)((?: (?:"
    + "|".join(re.escape(w) for w in STATUS_WORDS) + r")\.?)*)")


def status_marker(text):
    """The status glyph in a cell or a header line, or `None`."""
    return next((emoji for emoji in STATUS_EMOJI if emoji in text), None)


def status_words(text):
    """The word(s) a status line carries after its glyph, or `None`.

    `UX-454`: `status_marker` above answers with the **glyph**, which is
    the only thing the two copies of the marker have to agree on - and
    is therefore blind to a line that says its word twice. This reads
    the other half, so a guard can assert the line rather than its
    parse. Returns a list, because the whole point is that there can
    wrongly be more than one.
    """
    found = _STATUS_LINE.search(text)
    if not found:
        return None
    # Matched as whole words, never split on spaces: `Fixed & Verified`
    # is one word and splitting would make every one of its 54 files
    # look like three, which is the shape the caller is counting.
    return [word.rstrip(".")
            for word in _ONE_STATUS_WORD.findall(found.group(2))]


def close_status_line(body):
    """`body` with its first status line flipped to `🟢 Done`.

    `UX-454`: lifted out of `move()` so the guard can exercise **this**
    rather than a copy of it - `UX-387`'s lesson, that two readings of
    one property is how they came to disagree.

    Idempotent, because `_STATUS_WORD` repeats: applied to a line that
    already says `🟢 Done` it says it once, and applied to one that says
    it twice it repairs it. The pattern it replaced named only the two
    *open* words, so against an already-closed line it matched the glyph
    alone and left the old word standing - twenty-five files.
    """
    return re.sub(r"\*\*Status:\*\* \S+" + _STATUS_WORD.pattern,
                  "**Status:** 🟢 Done", body, count=1)


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
#: The order the topic table has always been written in. A derived
#: table still has to be *read*, and alphabetical would reshuffle it
#: every time a topic appears. Anything not listed sorts after these.
TOPIC_ORDER = ("capture", "analysis", "contracts", "viewer", "cli",
               "store", "docs", "guards")

#: `UX-501`: 223 of the 489 closed rows predate the `**Topic:**` header
#: and are in no historical index either, so no topic can be *derived*
#: for them. They go here rather than being distributed by guesswork -
#: a bucket that shrinks as they are classified, and a table that sums
#: to the row count instead of to 495 of 504.
TOPIC_UNKNOWN = "unclassified"


def row_ids(path):
    """The `UX-NNN` ids of a row list, in file order."""
    return re.findall(r"^\| (UX-\d+) \|", path.read_text(encoding="utf-8"),
                      re.M)


def _declared_topics():
    """`{uid: topic}` from the open table's own Topic column.

    The open row carries it and the closed row does not, so this is
    what a row *about to close* is read for - `move` copies it into the
    task file if the file has no header, and the count survives the
    move.
    """
    found = {}
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) > 4 and re.fullmatch(r"UX-\d+", cells[1]):
            found[cells[1]] = cells[3]
    return found


def topics():
    """`{uid: topic}` for every row in both lists.

    The task file's `**Topic:**` header first - one authority, and the
    only one a closed row still has. The open table's own column is the
    fallback for the handful of open items filed before the header
    existed. Everything else is `TOPIC_UNKNOWN`, said out loud.
    """
    declared = _declared_topics()
    found = {}
    for uid in row_ids(INDEX) + row_ids(CLOSED):
        header = re.search(r"\*\*Topic:\*\*\s*([a-z]+)",
                           task_file(uid).read_text(encoding="utf-8"))
        found[uid] = (header.group(1) if header
                      else declared.get(uid) or TOPIC_UNKNOWN)
    return found


def index_header():
    """The counts sentence and the topic table, derived from the rows.

    `UX-501`. Both are aggregates of the row lists, and being hand-typed
    made them the line two parallel tracks collide on even when neither
    touched the other's row.
    """
    open_ids, closed_ids = row_ids(INDEX), row_ids(CLOSED)
    of = topics()
    every = sorted({of[uid] for uid in of},
                   key=lambda name: (name == TOPIC_UNKNOWN,
                                     TOPIC_ORDER.index(name)
                                     if name in TOPIC_ORDER else len(TOPIC_ORDER),
                                     name))
    rows = ["| Topic | Open | Total |", "|---|---|---|"]
    for topic in every:
        rows.append("| %s | %d | %d |" % (
            topic,
            sum(1 for uid in open_ids if of[uid] == topic),
            sum(1 for uid in of if of[uid] == topic)))
    sentence = ("%d scenarios: **%d open**, %d closed."
                % (len(open_ids) + len(closed_ids), len(open_ids),
                   len(closed_ids)))
    return sentence, "\n".join(rows)


#: The counts sentence, and the topic table, as they sit in the index.
SENTENCE = re.compile(r"^\d+ scenarios: \*\*\d+ open\*\*, \d+ closed\.$",
                      re.M)
TOPIC_TABLE = re.compile(r"^\| Topic \| Open \| Total \|\n\|[-| ]+\|\n"
                         r"(?:\|.*\n)+", re.M)


def _index_is_derived():
    """`UX-501`: the two aggregates against the rows they summarise."""
    text = INDEX.read_text(encoding="utf-8")
    sentence, table = index_header()
    problems = []
    written = SENTENCE.search(text)
    if not written:
        problems.append("the index has no counts sentence to check")
    elif written.group(0) != sentence:
        problems.append("the counts sentence says %r; the rows say %r "
                        "- `--check --write` rewrites it"
                        % (written.group(0), sentence))
    block = TOPIC_TABLE.search(text)
    if not block:
        problems.append("the index has no topic table to check")
    elif block.group(0).strip() != table:
        problems.append("the topic table disagrees with the rows "
                        "- `--check --write` rewrites it")
    return problems


def write_index():
    """Put the derived sentence and table into the index."""
    text = INDEX.read_text(encoding="utf-8")
    sentence, table = index_header()
    text = SENTENCE.sub(lambda _m: sentence, text, count=1)
    text = TOPIC_TABLE.sub(lambda _m: table + "\n", text, count=1)
    INDEX.write_text(text, encoding="utf-8")


CHECKS = (
    ("every row's status glyph matches its task file's",
     lambda: status_disagreements()),
    ("no closed row is left in the open index",
     lambda: _closed_rows_left_open()),
    ("the index's open count matches its table",
     lambda: _open_count_disagreement()),
    ("the counts sentence and topic table are what the rows say",
     lambda: _index_is_derived()),
)


#: `UX-493`: a figure is `450,000` in prose and `450_000` in Python.
_FIGURE = re.compile(r"\d{1,3}(?:[,_]\d{3})+")


def figures_removed(diff: str):
    """Thousands-separated numbers a diff deletes from the file that had them.

    Digits only, so the two spellings of one figure are one figure -
    `UX-469` deleted `("golden", GOLDEN, 406_000)` and the backlog said
    `406,000`. Kept **per file**: that same commit wrote `406,000 →
    411,000` into its own task file, so a whole-diff subtraction
    cancelled the figure it had just moved and reported nothing.
    """
    per_file, gone, kept = {}, set(), set()

    def close():
        per_file.update({d: None for d in gone - kept})

    for line in diff.splitlines():
        if line.startswith("+++ "):
            close()
            gone, kept = set(), set()
        elif line[:1] in ("-", "+") and not line.startswith("--- "):
            found = {f.replace(",", "").replace("_", "")
                     for f in _FIGURE.findall(line[1:])}
            (gone if line[0] == "-" else kept).update(found)
    close()
    return sorted(per_file, key=int)


def figures_still_written(figures, skip=None):
    """`{digits: [(path, lineno, line)]}` for each figure the backlog says.

    Not a verdict. §3.6 is judgement-shaped - an Outcome quoting a
    figure it measured is history and a sentence presenting one as
    current is not - and `UX-132` declined to make that a test. This is
    the half that is not judgement: the grep, run rather than
    remembered, which is the half round 73 skipped.
    """
    wanted = {d: re.compile(r"\b" + r"[,_]?".join(
        [d[:len(d) % 3 or 3]] + [d[i:i + 3] for i in
                                 range(len(d) % 3 or 3, len(d), 3)]) + r"\b")
              for d in figures}
    hits = {d: [] for d in figures}
    for path in sorted(SCENARIOS.glob("*.md")):
        if skip is not None and path.name == skip.name:
            continue
        for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            for digits, pattern in wanted.items():
                if pattern.search(line):
                    hits[digits].append((path, number, line.strip()))
    return hits


def report_figures(diff: str, skip=None) -> int:
    """Print §3.6's grep. Always 0: the annotation call is the author's."""
    figures = figures_removed(diff)
    hits = figures_still_written(figures, skip=skip)
    written = [d for d in figures if hits[d]]
    print(f"§3.6: {len(figures)} figure(s) removed by this diff, "
          f"{len(written) or 'none'} still written in {_shown(SCENARIOS)}.")
    for digits in written:
        print(f"  {int(digits):,}")
        for path, number, line in hits[digits]:
            print(f"    {path.name}:{number}  {line[:72]}")
    if written:
        print("  Each is a judgement: annotate the file, or record it in "
              "your Outcome as history. Nothing here decides that.")
    return 0


def working_diff() -> str:
    """Staged and unstaged, against `HEAD`. Empty when git cannot answer."""
    try:
        done = subprocess.run(["git", "diff", "HEAD"], cwd=str(REPO),
                              capture_output=True, text=True, timeout=60)
    except OSError:
        return ""
    return done.stdout if done.returncode == 0 else ""


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

    body = close_status_line(body)
    # `UX-501`: the topic travels with the item. The open row carries a
    # Topic column and the closed row does not, so an item filed before
    # the `**Topic:**` header existed lost its topic the moment it
    # closed - which is 223 of the 489 closed rows, and why the derived
    # table has an `unclassified` line at all.
    if topic and not re.search(r"\*\*Topic:\*\*", body):
        body = re.sub(r"^(\*\*Priority:.*?)$", r"\1 | **Topic:** " + topic,
                      body, count=1, flags=re.M)
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
    INDEX.write_text(text, encoding="utf-8")

    # After the **last table row**, not at the end of the file:
    # `closed.md` carries per-round narrative sections below its table,
    # and the first draft appended into those - which broke the table
    # and was caught by `test_no_table_is_split_by_a_blank_line`.
    closed = CLOSED.read_text(encoding="utf-8").splitlines()
    last = max(i for i, text in enumerate(closed) if text.startswith("| UX-"))
    closed.insert(last + 1, closed_row)
    CLOSED.write_text("\n".join(closed) + "\n", encoding="utf-8")
    # `UX-501`: the aggregates are deliberately **not** written here.
    # Measured on two branches each closing one item: writing them made
    # the topic table conflict - the two topics' rows are adjacent, so
    # git reads them as one hunk - and auto-merged the counts sentence
    # to a number neither branch meant, "16 open" over 14 rows. A close
    # that edits only its own rows collides with nothing, and
    # `--check --write` derives the header once, after the merge.
    print(f"{uid}: status flipped, row moved.\n"
          f"  Read the row it just wrote. The scenario text is copied from "
          f"the open row and usually wants rewriting into what was *found*, "
          f"and this function's own first run produced a malformed row -\n"
          f"    grep '^| {uid} |' {_shown(CLOSED)}\n"
          f"  Then derive the index's counts from the rows (UX-501):\n"
          f"    python tools/dev_close_task.py --check --write")
    report_figures(working_diff(), skip=path)
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
    parser.add_argument("--write", action="store_true",
                        help="with --check: regenerate the index's counts "
                             "sentence and topic table from the rows, "
                             "instead of reporting that they disagree. The "
                             "rows stay hand-edited - they carry judgement "
                             "- and the aggregates never do (UX-501)")
    parser.add_argument("--figures", action="store_true",
                        help="fixing guide §3.6's grep: figures this diff "
                             "removed that the backlog still writes")
    parser.add_argument("--diff", default=None,
                        help="read the diff from this file instead of "
                             "`git diff HEAD` (for a guard)")
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

    if args.write and not args.check:
        parser.error("--write is what --check does instead of reporting; "
                     "give both")
    if args.check:
        if args.write:
            write_index()
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
    if args.figures:
        diff = (pathlib.Path(args.diff).read_text(encoding="utf-8")
                if args.diff else working_diff())
        return report_figures(diff,
                              skip=task_file(args.uid) if args.uid else None)
    if not args.uid:
        parser.error("a UX id is required unless --check or --figures is given")
    if args.outcome:
        print(OUTCOME_SKELETON.format(round=args.round, date=args.date,
                                      n=args.mutations, cap=OUTCOME_CAP))
        return 0
    if args.move:
        if not args.note:
            parser.error("--move needs --note: the closed.md row is a "
                         "sentence about what was found, and nothing can "
                         "write it for you")
        return move(args.uid, args.note)
    parser.error("give --outcome, --move, --check or --figures")


if __name__ == "__main__":
    sys.exit(main())
