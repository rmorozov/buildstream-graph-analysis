"""UX-497: the register is a budget, and this holds its two copies.

A session pays for what it reads. Round 74 measured the start of one:
60 KB of process documents before the task file, task files at a
median 8.5 KB, Outcome sections at a median 114 lines, and one dev
tool carrying 206 comment lines over 46 of code. `CLAUDE.md` now
states the budgets; this reads the tree against them, and holds the
numbers in `CLAUDE.md` to the ones enforced here.

Existing files over the docstring cap are listed with the count they
had, and may only shrink - a ratchet, not an amnesty.
"""
import ast
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO / "CLAUDE.md"
SCENARIOS = REPO / "docs" / "backlog" / "scenarios"

DOCSTRING_CAP = 25
OUTCOME_CAP = 80
FIRST_BUDGETED_ID = 497

#: Over the cap when the budget was set (round 74), at the count they had.
#: An entry whose file now fits the cap is stale and must be removed.
#:
#: `UX-502` emptied it: all eight were rewritten to a docstring of what
#: the tool does, how it is invoked, and one sentence per non-obvious
#: decision with the task id that holds the argument. Nothing was lost -
#: every distinctive figure in the eight was already in the backlog, and
#: that was checked before a line was cut. The dict stays so the next
#: file over the cap has somewhere to be listed while it shrinks.
GRANDFATHERED = {}


def _budgeted_modules():
    return sorted(REPO.glob("tools/dev_*.py")) + sorted(REPO.glob(".claude/hooks/*.py"))


def _docstring_lines(path):
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    return len(doc.splitlines())


def _rel(path):
    return path.relative_to(REPO).as_posix()


class TestModuleDocstrings:
    @pytest.mark.parametrize("path", [p for p in _budgeted_modules()
                                      if _rel(p) not in GRANDFATHERED],
                             ids=lambda p: _rel(p))
    def test_a_budgeted_docstring_fits(self, path):
        n = _docstring_lines(path)
        assert n <= DOCSTRING_CAP, (
            f"{_rel(path)}: module docstring is {n} lines, cap is "
            f"{DOCSTRING_CAP}. The why is one sentence; the history "
            f"lives in the task file and git log.")

    def test_a_grandfathered_docstring_only_shrinks(self):
        """`UX-502` emptied the table, so this loops rather than
        parametrising: an empty parametrize emits a skip whose reason
        `UX-449`'s census has never seen, and declaring "got empty
        parameter set" as a known reason would be a fudge over a guard
        with nothing left to guard."""
        for rel, recorded in sorted(GRANDFATHERED.items()):
            path = REPO / rel
            assert path.exists(), (
                f"{rel} is grandfathered but gone - drop the entry")
            n = _docstring_lines(path)
            assert n <= recorded, (
                f"{rel}: {n} lines, recorded {recorded} - it may only shrink")
            assert n > DOCSTRING_CAP, (
                f"{rel}: {n} lines now fits the cap of {DOCSTRING_CAP} - "
                f"remove it from GRANDFATHERED so the table cannot rot")

    def test_every_grandfathered_file_is_budgeted(self):
        budgeted = {_rel(p) for p in _budgeted_modules()}
        assert set(GRANDFATHERED) <= budgeted, sorted(set(GRANDFATHERED) - budgeted)


def _outcome_body(text):
    m = re.search(r"^## Outcome.*$", text, re.M)
    if not m:
        return None
    rest = text[m.start():]
    nxt = re.search(r"^## (?!Outcome)", rest[1:], re.M)
    return rest if not nxt else rest[: nxt.start() + 1]


def _outcome_lines(text):
    body = _outcome_body(text)
    return None if body is None else len(body.rstrip().splitlines())


def _budgeted_task_files():
    out = []
    for path in sorted(SCENARIOS.glob("UX-*.md")):
        number = int(re.match(r"UX-(\d+)", path.name).group(1))
        if number >= FIRST_BUDGETED_ID:
            out.append(path)
    return out


def _is_closed(text):
    status = re.search(r"\*\*Status:\*\*[^\n|]*", text)
    return bool(status) and "🟢" in status.group(0)


def _closed_budgeted_task_files():
    return [p for p in _budgeted_task_files()
            if _is_closed(p.read_text(encoding="utf-8"))]


#: Closed before `UX-497` on and shipped no code guard, so there is
#: nothing a mutation table could name - checked, not assumed, by
#: `test_every_exemption_is_a_real_closed_task` below. A permanent
#: list, not a ratchet: a closed Outcome does not get a mutation table
#: later, so an entry here never comes off.
NO_GUARD_OUTCOMES = {
    # A process/regime decision (batch gate vs. per-item); no code
    # shipped for either regime to guard.
    "UX-0500": "a decision between two measured regimes, no new guard",
    # Premise falsified before any guard landed; everything it shipped
    # was undone in the same Outcome.
    "UX-0633": "reverted on its own Outcome; nothing left to mutate",
    # The row is about a review process reading a moving branch, not
    # about code the row's own commit changed.
    "UX-0656": "the Outcome is a process finding, not a code guard",
    # An investigation and an upstream-cause fix pinned by a fixture
    # value, not a new guard.
    "UX-0755": "a root-cause fix pinned by a fixture value, no new guard",
}


class TestOutcomes:
    @pytest.mark.parametrize("path", _budgeted_task_files(), ids=lambda p: p.name[:7])
    def test_a_budgeted_outcome_fits(self, path):
        n = _outcome_lines(path.read_text(encoding="utf-8"))
        if n is None:
            return  # not closed yet; nothing to measure
        assert n <= OUTCOME_CAP, (
            f"{path.name}: Outcome is {n} lines, cap is {OUTCOME_CAP} - the "
            f"gap measured, the close measured, the mutation table, the deviation")

    def test_the_counter_reads_a_section_not_the_file(self):
        text = "# t\n\n## Motivation\nx\n\n## Outcome (r)\na\nb\n\n## After\nz\n"
        assert _outcome_lines(text) == 3


class TestOutcomeContentIsGuarded:
    """`UX-764`: the length cap says nothing about content. `round-94.md`
    counted 55 of 60 closed Outcomes naming a mutation table - five did
    not, and nothing reddened. This reads the section `_outcome_body`
    already isolates, so the length and content checks cannot drift
    about which text they mean."""

    @pytest.mark.parametrize(
        "path", [p for p in _closed_budgeted_task_files()
                 if p.name[:7] not in NO_GUARD_OUTCOMES],
        ids=lambda p: p.name[:7])
    def test_a_closed_outcome_names_its_mutation(self, path):
        body = _outcome_body(path.read_text(encoding="utf-8"))
        assert body is not None
        assert "mutation" in body.lower(), (
            f"{path.name}: closed Outcome names no mutation table - the "
            f"defect `docs/audits/round-94.md` counted five of sixty "
            f"closed tasks having, with the suite green throughout")

    def test_every_exemption_is_a_real_closed_task(self):
        closed = {p.name[:7] for p in _closed_budgeted_task_files()}
        assert set(NO_GUARD_OUTCOMES) <= closed, (
            f"exempted but not a closed, budgeted task file: "
            f"{sorted(set(NO_GUARD_OUTCOMES) - closed)}")


def _register_rows():
    """`[(cap, detail)]` from `CLAUDE.md`'s `## Register` table only -
    the blank header and separator rows are dropped by shape, like
    `_rule_rows` in `test_the_agent_configuration_holds.py`."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    m = re.search(r"^## Register\n(.*?)(?=^## )", text, re.M | re.S)
    assert m, "CLAUDE.md has no ## Register section"
    rows = []
    for line in m.group(1).splitlines():
        if not (line.startswith("| ") and line.count("|") == 3
                and "---" not in line):
            continue
        cap, detail = (cell.strip() for cell in line.split("|")[1:3])
        if (cap, detail) == ("", ""):
            continue
        rows.append((cap, detail))
    return rows


class TestEveryRegisterRowNamesItsEnforcement:
    """`UX-764`: the code comment row was unguarded and read the same
    as the three that were. Every row must now either name a guard
    file that exists or say "convention" - so a fifth row cannot go
    back to the honour system silently."""

    def test_every_row_names_a_guard_or_says_convention(self):
        rows = _register_rows()
        assert len(rows) >= 4, f"CLAUDE.md's Register table has {len(rows)} rows"
        bad = []
        for cap, detail in rows:
            if "convention" in detail.lower():
                continue
            named = re.findall(r"`([\w./-]+\.py)`", detail)
            if named and all((REPO / n).exists() for n in named):
                continue
            bad.append((cap, detail))
        assert not bad, (
            f"Register row(s) name no existing guard file and no "
            f"'convention': {bad}")


class TestClaudeMdCarriesTheSameNumbers:
    def test_the_register_section_exists(self):
        assert re.search(r"^## Register", CLAUDE_MD.read_text(encoding="utf-8"), re.M)

    @pytest.mark.parametrize("figure", [f"≤ {DOCSTRING_CAP} lines", f"≤ {OUTCOME_CAP} lines",
                                        f"UX-{FIRST_BUDGETED_ID}"])
    def test_a_budget_is_stated_as_enforced(self, figure):
        assert figure in CLAUDE_MD.read_text(encoding="utf-8"), (
            f"CLAUDE.md does not state {figure!r}; the budget it states and "
            f"the one enforced here are two copies of one fact")
