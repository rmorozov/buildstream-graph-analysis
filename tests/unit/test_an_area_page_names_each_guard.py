"""UX-1000: an area page names each scenario's guard - from the task's
one `**Guard:**` line since `UX-1092`, never inferred from its prose.

A sandbox of rows - a named guard that exists, one that does not, a
`none — <reason>`, and a row with no line - so the counts are exact
without touching the real backlog or `tests/` tree.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_area_pages as dap
import dev_close_task as tasks


def _task(scenarios, number, guard, body=""):
    path = scenarios / f"UX-{number:04d}-x.md"
    line = f"**Guard:** {guard}\n\n" if guard is not None else ""
    path.write_text(
        f"# UX-{number}: x\n\n**Priority:** Low | **Status:** "
        f"\N{LARGE RED CIRCLE} Not Started | **Topic:** guards | "
        f"**Area:** tools\n\n{line}{body}\n", encoding="utf-8")
    tasks._FILES_BY_NUMBER.clear()
    return path


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    monkeypatch.setattr(tasks, "SCENARIOS", scenarios)
    tests_root = tmp_path / "tests"
    (tests_root / "unit").mkdir(parents=True)
    (tests_root / "unit" / "test_present.py").write_text("", encoding="utf-8")
    (tests_root / "unit" / "test_other.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(tasks, "TESTS_ROOT", tests_root)
    _task(scenarios, 1, "test_present.py")
    _task(scenarios, 2, "test_absent.py")
    _task(scenarios, 3, "none — nothing to hold")
    _task(scenarios, 4, None,
          "## Outcome (round 1) — Done\n\n`test_present.py` covers it.\n")
    yield scenarios
    tasks._FILES_BY_NUMBER.clear()


def _page(ids=("UX-1", "UX-2", "UX-3", "UX-4")):
    return dap.area_page_body("tools", list(ids))


class TestTheGuardColumn:

    def test_a_named_existing_guard_reads_present(self, sandbox):
        assert "| `test_present.py` |" in _page()

    def test_a_named_absent_guard_reads_missing(self, sandbox):
        assert "| `test_absent.py` (missing) |" in _page()

    def test_none_reads_its_reason(self, sandbox):
        assert "| none — nothing to hold |" in _page()

    def test_a_row_with_no_line_says_so(self, sandbox):
        assert "| no `Guard:` line |" in _page(["UX-4"])

    def test_the_page_ends_covered_n_of_m(self, sandbox):
        """Only the row naming an existing file is covered, of four -
        not 2 (a missing guard), and not the Outcome-only row."""
        assert "covered 1 / 4 (none 1, no line 1)" in _page()

    def test_the_page_names_the_row_count(self, sandbox):
        assert "4 row(s)" in _page()


class TestNothingIsInferredFromProse:
    """`UX-1092`: the line is the one source - an Outcome, Decision or
    Acceptance Test naming a file adds nothing to the page."""

    def test_an_outcome_only_row_is_not_covered(self, sandbox):
        body = _page(["UX-4"])
        assert "test_present.py" not in body
        assert "covered 0 / 1 (none 0, no line 1)" in body

    def test_the_line_wins_over_every_section(self, sandbox):
        _task(sandbox, 5, "test_present.py", (
            "## Acceptance Test\n\nGuard: `test_other.py`.\n\n"
            "## Decision\n\n```text\nGuard:     `test_other.py`\n```\n\n"
            "## Outcome (round 1) — Done\n\n`test_other.py` covers it.\n"))
        body = _page(["UX-5"])
        assert "| `test_present.py` |" in body
        assert "test_other.py" not in body

    def test_a_guard_line_below_a_heading_is_not_the_field(self, sandbox):
        """`UX-648` carries a `**Guard:**` paragraph in its body."""
        _task(sandbox, 6, None, "## Outcome\n\n**Guard:** `test_present.py`\n")
        assert "| no `Guard:` line |" in _page(["UX-6"])


class TestReportAreasStillOnlyPrints:

    def test_areas_names_the_unknown_one_and_exits_1(self, sandbox, capsys):
        assert dap.report_areas("nowhere-at-all") == 1
        assert "no such area" in capsys.readouterr().err
