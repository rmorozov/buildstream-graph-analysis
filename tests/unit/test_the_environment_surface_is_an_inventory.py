"""UX-630: every name in `bga`'s environment namespace has a home.

`bga --help` cannot list an environment variable, which is the reason
`bga/report/rate.py` gives for choosing one - so an inventory built
from the parser cannot see the surface it is an inventory of. This one
reads the tree.

Measured when this was filed: eight names under `bga/` and `tools/`,
six of them in no document outside `docs/backlog/` and `docs/audits/`.
`UX-635` added the second namespace this scan could not see - 21
`BST_TRACE_*` names, none documented anywhere a reader looks - and
made the population a set of prefixes rather than one.

Both directions, because a scan that finds nothing satisfies "every
name is documented" and says so to no one.
"""

import functools
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs/guides/cli.md"

#: The heading over the section that is the *subject*. Read by heading,
#: and then by table row, because `cli.md` names one of these in prose
#: too and a guard its own explanation satisfies checks nothing.
SECTION = "## The environment `bga` reads"

#: `UX-1290`: every home a row may live in, `(page, heading)`; the capture path's own namespace left the guide.
HOMES = (
    (GUIDE, SECTION),
    (REPO / "docs/design/areas/tools-native_trace.md", "## `BST_TRACE_*` — Plane 2 and Plane 3"),
)

#: `UX-1290`: the table a user reads for what to set, and the cells each row of it owes.
SWITCHES = "### Switches you set"
SWITCH_HEADER = "| name | default | how to turn it off | cost | what it changes | where |"

#: The namespaces, as they appear in source. `UX-635`: a **set**, not
#: one prefix - `UX-630` scanned `BGA_` alone, and `BST_TRACE_*` is a
#: second family the same size one namespace over, invisible to a guard
#: whose population is as wide as the prefix somebody typed into it.
#:
#: What is deliberately *not* here: the system variables `bga` merely
#: consumes (`TMPDIR`, `XDG_CACHE_HOME`, `LD_PRELOAD`, `PYTHONPATH`).
#: They are not this project's names, and a table that lists them is
#: describing the platform rather than the tool.
PREFIXES = ("BGA_", "BST_TRACE_")

#: A pattern and not a list, so a name added tomorrow is in the
#: population without anyone adding it.
NAME = re.compile(r"\b(?:{})[A-Z0-9_]+\b".format("|".join(re.escape(p) for p in PREFIXES)))

#: Where a name may be introduced. Not `tests/`: a harness variable is
#: the suite's own plumbing, and the acceptance this holds is about a
#: variable that changes what the shipped tool does.
ROOTS = ("bga", "tools")

#: A path claim inside a table cell: backticked, and with a suffix.
CITED = re.compile(r"`([\w./-]+\.\w+)`")

#: A row's first cell. Deliberately **not** derived from `NAME`: it
#: reads any shouting name, so narrowing `PREFIXES` leaves the rows for
#: the dropped namespace parsed and unmatched - which is what the stale
#: clause below is for. Derived, the two sides would shrink together
#: and a narrowed population would pass every clause in this file.
ROW_NAME = re.compile(r"`([A-Z][A-Z0-9_]*_[A-Z0-9_]+)`")


@functools.lru_cache(maxsize=1)
def _scan():
    """`({name: [path]}, {path read})` over the tracked files in ROOTS.

    `git ls-files` and not a walk: a main checkout holds whole copies of
    this tree at older commits under `.claude/worktrees/`, and a walk
    reports their contents as this tree's - the defect
    `test_the_context_map_is_the_tree.py` records from round 83.

    Comments and docstrings count as occurrences. `BGA_TRACE_PROCESSOR`
    appears in `tools/` only in a docstring and an error message and is
    a real variable, so a scan that read code alone would drop it.
    """
    listed = subprocess.run(
        ["git", "ls-files", "--", *ROOTS], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout
    found, read = {}, set()
    for rel in listed.splitlines():
        try:
            text = (REPO / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        read.add(rel)
        for name in NAME.findall(text):
            found.setdefault(name, set()).add(rel)
    return ({name: sorted(paths) for name, paths in sorted(found.items())}, read)


def _tracked():
    listed = subprocess.run(
        ["git", "ls-files", "--", *ROOTS], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout
    return set(listed.splitlines())


def _table(section: str) -> dict:
    """`{name: cells}` for each line whose first cell is one backticked name."""
    rows = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        first = ROW_NAME.fullmatch(cells[0])
        if first:
            rows[first.group(1)] = cells
    return rows


@functools.cache
def _home(page: pathlib.Path, heading: str) -> dict:
    """`{name: cells}` from the table rows under `heading` in `page`."""
    text = page.read_text(encoding="utf-8")
    assert heading in text, f"{page.name} has no `{heading}` section"
    rows = _table(text.split(heading, 1)[1].split("\n## ", 1)[0])
    assert rows, f"no table rows under `{heading}` in {page.name}"
    return rows


@functools.lru_cache(maxsize=1)
def _rows():
    """`{name: the where cell}` over every home in `HOMES`.

    A row is a line whose first cell is one backticked name; the header,
    the separator and every paragraph in the section are not.
    """
    rows = {}
    for page, heading in HOMES:
        for name, cells in _home(page, heading).items():
            assert name not in rows, f"{name} has a row in two homes"
            rows[name] = cells[-1]
    return rows


def _switches() -> str:
    section = GUIDE.read_text(encoding="utf-8").split(SECTION, 1)[1]
    assert SWITCHES in section, f"{GUIDE.name} has no `{SWITCHES}` under `{SECTION}`"
    return section.split(SWITCHES, 1)[1].split("\n#", 1)[0]


class TestTheInventoryIsTheTree:
    def test_every_name_in_the_tree_has_a_row(self):
        """The acceptance: a name with no documented home is red."""
        missing = sorted(set(_scan()[0]) - set(_rows()))
        assert missing == [], (
            f"environment name(s) in {'/, '.join(ROOTS)}/ with no row under "
            f"`{SECTION}` in docs/guides/cli.md, nor in any other home in HOMES: "
            + ", ".join(f"{n} ({', '.join(_scan()[0][n])})" for n in missing)
        )

    def test_every_row_names_something_the_tree_still_has(self):
        """The other direction. A row for a variable that was removed
        sends a reader looking for something that is not there, and it
        is also what keeps the clause above from passing on an empty
        scan."""
        stale = sorted(set(_rows()) - set(_scan()[0]))
        assert stale == [], f"row(s) under `{SECTION}` naming nothing in {'/, '.join(ROOTS)}/: {stale}"

    def test_the_scan_reads_every_tracked_file_in_its_roots(self):
        """A population that quietly shrinks is how this guard goes
        blind to exactly the file a new variable lands in. Every tracked
        file under the roots is read, or the difference is named."""
        names, read = _scan()
        unread = sorted(_tracked() - read)
        assert unread == [], f"the scan skipped tracked file(s): {unread}"
        assert read, "the scan read nothing at all"
        assert names, "the scan found no name at all"

    def test_each_row_cites_a_file_that_carries_the_name(self):
        """Not that the cited path exists - that it contains the name.
        A file can exist and have nothing to do with the variable, and
        asking the cheaper question is a guard reading a proxy for the
        thing it names."""
        wrong = []
        for name, where in _rows().items():
            cited = CITED.findall(where)
            assert cited, f"{name}'s row cites no file: {where!r}"
            for rel in cited:
                path = REPO / rel
                if not path.is_file():
                    wrong.append(f"{name}: {rel} does not exist")
                elif name not in path.read_text(encoding="utf-8"):
                    wrong.append(f"{name}: {rel} does not name it")
        assert wrong == [], f"row(s) under `{SECTION}` citing a file that does not carry the name: {wrong}"


class TestTheSwitchesAreTheUsersOwn:
    """`UX-1290`: what a user sets is one table, with a default, an off and a cost per row."""

    def test_no_capture_wiring_row_in_the_switches_table(self):
        rows = _table(_switches())
        assert rows, f"no rows under `{SWITCHES}`"
        wiring = sorted(name for name in rows if name.startswith("BST_TRACE_"))
        assert wiring == [], f"`{SWITCHES}` lists the capture path's own wiring: {wiring}"

    def test_every_switch_states_its_default_its_off_and_its_cost(self):
        assert SWITCH_HEADER in _switches(), f"`{SWITCHES}` is not headed {SWITCH_HEADER!r}"
        short = {name: cells for name, cells in _table(_switches()).items() if len(cells) != 6 or not all(cells[1:4])}
        assert short == {}, f"switch row(s) missing a default, an off or a cost: {sorted(short)}"

    def test_every_capture_wiring_name_lives_in_the_area_page(self):
        page, heading = HOMES[1]
        guide = set(_home(GUIDE, SECTION))
        stray = sorted(name for name in _scan()[0] if name.startswith("BST_TRACE_") and name in guide)
        assert stray == [], f"`BST_TRACE_*` row(s) still in the guide: {stray}"
        assert any(name.startswith("BST_TRACE_") for name in _home(page, heading))
