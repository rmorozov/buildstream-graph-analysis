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
GRANDFATHERED = {
    "tools/dev_perfetto_queries.py": 29,
    "tools/dev_process_bands.py": 29,
    ".claude/hooks/no_bulk_add.py": 33,
    "tools/dev_refresh_analysis.py": 35,
    "tools/dev_js_deps.py": 38,
    "tools/dev_plane_capability.py": 55,
    "tools/dev_tier_drift.py": 77,
    "tools/dev_trace_coverage.py": 85,
}


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

    @pytest.mark.parametrize("rel,recorded", sorted(GRANDFATHERED.items()))
    def test_a_grandfathered_docstring_only_shrinks(self, rel, recorded):
        path = REPO / rel
        assert path.exists(), f"{rel} is grandfathered but gone - drop the entry"
        n = _docstring_lines(path)
        assert n <= recorded, f"{rel}: {n} lines, recorded {recorded} - it may only shrink"
        assert n > DOCSTRING_CAP, (
            f"{rel}: {n} lines now fits the cap of {DOCSTRING_CAP} - "
            f"remove it from GRANDFATHERED so the table cannot rot")

    def test_every_grandfathered_file_is_budgeted(self):
        budgeted = {_rel(p) for p in _budgeted_modules()}
        assert set(GRANDFATHERED) <= budgeted, sorted(set(GRANDFATHERED) - budgeted)


def _outcome_lines(text):
    m = re.search(r"^## Outcome.*$", text, re.M)
    if not m:
        return None
    rest = text[m.start():]
    nxt = re.search(r"^## (?!Outcome)", rest[1:], re.M)
    body = rest if not nxt else rest[: nxt.start() + 1]
    return len(body.rstrip().splitlines())


def _budgeted_task_files():
    out = []
    for path in sorted(SCENARIOS.glob("UX-*.md")):
        number = int(re.match(r"UX-(\d+)", path.name).group(1))
        if number >= FIRST_BUDGETED_ID:
            out.append(path)
    return out


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


class TestClaudeMdCarriesTheSameNumbers:
    def test_the_register_section_exists(self):
        assert re.search(r"^## Register", CLAUDE_MD.read_text(encoding="utf-8"), re.M)

    @pytest.mark.parametrize("figure", [f"≤ {DOCSTRING_CAP} lines", f"≤ {OUTCOME_CAP} lines",
                                        f"UX-{FIRST_BUDGETED_ID}"])
    def test_a_budget_is_stated_as_enforced(self, figure):
        assert figure in CLAUDE_MD.read_text(encoding="utf-8"), (
            f"CLAUDE.md does not state {figure!r}; the budget it states and "
            f"the one enforced here are two copies of one fact")
