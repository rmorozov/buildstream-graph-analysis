"""UX-580: a roles row says who serves it, and the corpus decides whether it must.

`roles.md`'s table said "nothing aggregates across builds" of R5 for
four rounds after `bga/store_aggregate.py` began publishing
min/median/p95/max/MAD per host class, and "nothing speaks about
variance or worst-case" of R7 for the same four. Rule 3 of that file's
Traceability section - the table is maintained, not archaeological -
was convention, and `UX-231`'s guard only pinned the *unserved* role.

So this reads the other direction, derived rather than restated: the
closed filings are the population, each row's last cell is the claim,
and a role the corpus serves whose row names nobody is the defect.
"""
import functools
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]
ROLES = REPO / "docs" / "design" / "roles.md"
SCENARIOS = "docs/backlog/scenarios"

#: A row of the role table: `| R5 | ... |`. The subject of every claim
#: below is a *cell* of one of these, never the prose around them - the
#: gap-analysis paragraph names `UX-234` too, and a guard that read the
#: document would pass on the sentence arguing for the fix.
ROW = re.compile(r"^\| (R\d+) \|.*\|\s*$", re.M)

ITEM = re.compile(r"\bUX-0*(\d+)\b")


def _cells(row):
    """The row's cells, the way a renderer splits them."""
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


@functools.lru_cache(maxsize=1)
def _rows():
    """`{role id: the row's last cell}` - the served-by cell."""
    out = {}
    for line in ROLES.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            out[match.group(1)] = _cells(line)[-1]
    return out


@functools.lru_cache(maxsize=1)
def _filings():
    """`{item number: (closed, roles its Serves line names)}`.

    `git ls-files` rather than a glob: a main checkout holds
    `.claude/worktrees/<agent>/`, a whole second copy of this tree at
    an older commit, and a walk would count it twice (`UX-577`).
    """
    listed = subprocess.run(
        ["git", "ls-files", SCENARIOS + "/UX-*.md"],
        cwd=REPO, check=True, capture_output=True, text=True).stdout.split()
    out = {}
    for relative in listed:
        number = int(re.search(r"UX-0*(\d+)-", relative).group(1))
        header = (REPO / relative).read_text(encoding="utf-8").split("\n## ", 1)[0]
        serves = [line for line in header.splitlines() if "**Serves:**" in line]
        roles = frozenset(
            re.findall(r"\bR\d+\b", serves[0].split("**Serves:**")[1].split("|")[0])
        ) if serves else frozenset()
        out[number] = ("**Status:** 🟢" in header, roles)
    return out


def _closed_by_role():
    """`{role id: [item numbers]}` over closed filings only."""
    out = {}
    for number, (closed, roles) in _filings().items():
        if closed:
            for role in roles:
                out.setdefault(role, []).append(number)
    return {role: sorted(numbers) for role, numbers in out.items()}


class TestThereIsSomethingToCheck:
    """A guard over an empty population passes vacuously."""

    def test_the_table_parses_as_eight_rows(self):
        assert sorted(_rows(), key=lambda r: int(r[1:])) == [
            f"R{n}" for n in range(1, 9)], sorted(_rows())

    def test_the_corpus_is_the_backlog_and_not_a_handful(self):
        filings = _filings()
        assert len(filings) >= 500, len(filings)
        tagged = [n for n, (_, roles) in filings.items() if roles]
        assert len(tagged) >= 100, len(tagged)

    def test_the_population_covers_most_of_the_table(self):
        served = _closed_by_role()
        assert len(served) >= 6, sorted(served)


class TestEveryRowNamesWhoServesIt:

    def test_a_role_the_corpus_serves_names_a_closed_filing_that_carries_it(self):
        """The claim. Derived from the counts, so the next mechanism
        that serves a role cannot leave the row stale: the row must
        name at least one item that is closed *and* whose own `Serves:`
        line carries this role."""
        filings = _filings()
        stale = []
        for role, candidates in sorted(_closed_by_role().items()):
            cell = _rows()[role]
            named = [int(n) for n in ITEM.findall(cell)]
            good = [n for n in named
                    if filings.get(n, (False, frozenset()))[0]
                    and role in filings[n][1]]
            if not good:
                stale.append(
                    f"{role}: the row's served-by cell names {named or 'nobody'}, "
                    f"and none of those is a closed filing carrying {role}. "
                    f"{len(candidates)} filing(s) do, e.g. "
                    + ", ".join(f"UX-{n}" for n in candidates[:4]))
        assert stale == [], (
            "roles.md's table is archaeological again (rule 3):\n  "
            + "\n  ".join(stale))

    def test_every_id_a_cell_names_is_a_filing_that_exists(self):
        filings = _filings()
        unknown = [(role, n) for role, cell in _rows().items()
                   for n in (int(x) for x in ITEM.findall(cell))
                   if n not in filings]
        assert unknown == [], f"served-by cell(s) citing no filing: {unknown}"

    def test_a_role_no_closed_filing_carries_names_nobody(self):
        """R6 - the contributor waiting on a queue. The row must not
        borrow someone else's work: the day a filing for it closes,
        this reddens and the row is rewritten in that commit."""
        served = _closed_by_role()
        filings = _filings()
        borrowed = []
        for role, cell in sorted(_rows().items()):
            if role in served:
                continue
            named = [n for n in (int(x) for x in ITEM.findall(cell))
                     if filings.get(n, (False, frozenset()))[0]]
            if named:
                borrowed.append((role, named))
        assert borrowed == [], (
            f"a role no closed filing serves, whose row names one: {borrowed}")

    def test_the_served_by_cell_is_the_column_the_header_names(self):
        """What the parse above depends on. An extra column, or a row an
        unescaped pipe split, moves the served-by cell somewhere else
        and every claim here would then read the wrong text - silently,
        because the wrong text is still a cell. So the header names the
        column and every row is measured against it."""
        lines = ROLES.read_text(encoding="utf-8").splitlines()
        header = [line for line in lines if line.startswith("| # | role |")]
        assert len(header) == 1, header
        columns = _cells(header[0])
        assert columns[-1] == "bga today, and what served it", columns
        for role, cell in sorted(_rows().items()):
            row = [line for line in lines if line.startswith(f"| {role} |")]
            assert len(row) == 1, (role, len(row))
            assert len(_cells(row[0])) == len(columns), (role, _cells(row[0]))
            assert cell == _cells(row[0])[-1], role


class TestTheGapAnalysisIsDated:

    def test_the_paragraph_says_when_it_was_last_measured(self):
        """A gap analysis with no date reads as current forever; this
        one was quoted as current for four rounds after it stopped
        being true."""
        heading = [line for line in ROLES.read_text(encoding="utf-8").splitlines()
                   if line.startswith("## The gap")]
        assert len(heading) == 1, heading
        assert re.search(r"round \d+, \d{4}-\d{2}-\d{2}", heading[0]), heading[0]
