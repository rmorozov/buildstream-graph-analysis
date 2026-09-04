"""UX-630: every name in `bga`'s environment namespace has a home.

`bga --help` cannot list an environment variable, which is the reason
`bga/report/rate.py` gives for choosing one - so an inventory built
from the parser cannot see the surface it is an inventory of. This one
reads the tree.

Measured when this was filed: eight names under `bga/` and `tools/`,
six of them in no document outside `docs/backlog/` and `docs/audits/`.

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

#: The namespace as it appears in source. A pattern and not a list, so
#: a name added tomorrow is in the population without anyone adding it.
NAME = re.compile(r"\bBGA_[A-Z0-9_]+\b")

#: Where a name may be introduced. Not `tests/`: a harness variable is
#: the suite's own plumbing, and the acceptance this holds is about a
#: variable that changes what the shipped tool does.
ROOTS = ("bga", "tools")

#: A path claim inside a table cell: backticked, and with a suffix.
CITED = re.compile(r"`([\w./-]+\.\w+)`")


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
    listed = subprocess.run(["git", "ls-files", "--", *ROOTS], cwd=REPO,
                            check=True, capture_output=True, text=True).stdout
    found, read = {}, set()
    for rel in listed.splitlines():
        try:
            text = (REPO / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        read.add(rel)
        for name in NAME.findall(text):
            found.setdefault(name, set()).add(rel)
    return ({name: sorted(paths) for name, paths in sorted(found.items())},
            read)


def _tracked():
    listed = subprocess.run(["git", "ls-files", "--", *ROOTS], cwd=REPO,
                            check=True, capture_output=True, text=True).stdout
    return set(listed.splitlines())


@functools.lru_cache(maxsize=1)
def _rows():
    """`{name: the where cell}` from the section's table rows.

    A row is a line whose first cell is one backticked name; the header,
    the separator and every paragraph in the section are not.
    """
    text = GUIDE.read_text(encoding="utf-8")
    assert SECTION in text, f"{GUIDE.name} has no `{SECTION}` section"
    section = text.split(SECTION, 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        first = re.fullmatch(r"`(BGA_[A-Z0-9_]+)`", cells[0])
        if first:
            rows[first.group(1)] = cells[-1]
    assert rows, f"no table rows under `{SECTION}` in {GUIDE.name}"
    return rows


class TestTheInventoryIsTheTree:
    def test_every_name_in_the_tree_has_a_row(self):
        """The acceptance: a name with no documented home is red."""
        missing = sorted(set(_scan()[0]) - set(_rows()))
        assert missing == [], (
            f"environment name(s) in {'/, '.join(ROOTS)}/ with no row under "
            f"`{SECTION}` in docs/guides/cli.md: "
            + ", ".join(f"{n} ({', '.join(_scan()[0][n])})" for n in missing))

    def test_every_row_names_something_the_tree_still_has(self):
        """The other direction. A row for a variable that was removed
        sends a reader looking for something that is not there, and it
        is also what keeps the clause above from passing on an empty
        scan."""
        stale = sorted(set(_rows()) - set(_scan()[0]))
        assert stale == [], (
            f"row(s) under `{SECTION}` naming nothing in "
            f"{'/, '.join(ROOTS)}/: {stale}")

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
        assert wrong == [], (
            f"row(s) under `{SECTION}` citing a file that does not carry "
            f"the name: {wrong}")
