"""UX-1000: an area page names each scenario's guard.

The Decision's own sandbox: three rows - a named guard that exists, a
named guard that does not, and a row naming none - so the page reads
"covered 1 / 3" without touching the real backlog or `tests/` tree.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_area_pages as dap
import dev_close_task as tasks


def _task(scenarios, number, body):
    path = scenarios / f"UX-{number:04d}-x.md"
    path.write_text(
        f"# UX-{number}: x\n\n**Priority:** Low | **Status:** "
        f"\N{LARGE RED CIRCLE} Not Started | **Topic:** guards | "
        f"**Area:** tools\n\n{body}\n", encoding="utf-8")
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
    monkeypatch.setattr(dap, "TESTS_ROOT", tests_root)
    tasks._FILES_BY_NUMBER.clear()
    _task(scenarios, 1, "## Acceptance Test\n\nGuard: `test_present.py`.\n")
    _task(scenarios, 2, "## Acceptance Test\n\nGuard: `test_absent.py`.\n")
    _task(scenarios, 3, "## Acceptance Test\n\nNothing named here.\n")
    yield scenarios
    tasks._FILES_BY_NUMBER.clear()


class TestTheGuardColumn:

    def test_a_named_existing_guard_reads_present(self, sandbox):
        body = dap.area_page_body("tools", ["UX-1", "UX-2", "UX-3"])
        assert "| `test_present.py` |" in body

    def test_a_named_absent_guard_reads_missing(self, sandbox):
        body = dap.area_page_body("tools", ["UX-1", "UX-2", "UX-3"])
        assert "| `test_absent.py` (missing) |" in body

    def test_no_file_named_reads_no_guard_named(self, sandbox):
        body = dap.area_page_body("tools", ["UX-1", "UX-2", "UX-3"])
        assert "| no guard named |" in body

    def test_the_page_ends_covered_n_of_m(self, sandbox):
        """The discriminating count: only the row with an existing
        file is covered, of the three rows listed - `covered 1 / 3`,
        not 2 (a missing guard still names one) or 3 (every row)."""
        body = dap.area_page_body("tools", ["UX-1", "UX-2", "UX-3"])
        assert "covered 1 / 3" in body

    def test_the_page_names_the_row_count(self, sandbox):
        """UX-575's defect retired `test_a_page_counts_the_rows_it_lists`
        with nothing left asserting the `N row(s)` sentence - restored
        here rather than dropped."""
        body = dap.area_page_body("tools", ["UX-1", "UX-2", "UX-3"])
        assert "3 row(s)" in body


class TestTheOutcomeSourceSkipsItsOwnBoilerplate:
    """UX-1000 (verifier, round 140): `guard_files()` swept the whole
    `## Outcome` and counted UX-575 covered via the register footer -
    a sentence every closed Outcome carries regardless of its own
    guard. The mutation table names whichever file a mutation touched,
    not what covers *this* row, and is excluded the same way."""

    def test_a_footer_only_mention_reads_no_guard_named(self, sandbox):
        _task(sandbox, 5, (
            "## Outcome (round 1) — Done\n\n**Premise:** held.\n\n"
            "<!-- 80 lines, held by test_present.py::TestOutcomes. -->\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-5"])
        assert "| no guard named |" in body

    def test_a_mutation_table_only_mention_reads_no_guard_named(
            self, sandbox):
        _task(sandbox, 6, (
            "## Outcome (round 1) — Done\n\n**Premise:** held.\n\n"
            "### Mutations verified red and reverted (1)\n\n"
            "| # | mutation | reddened |\n|---|---|---|\n"
            "| A | drop the check | `test_present.py` |\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-6"])
        assert "| no guard named |" in body


class TestTheOutcomeSourceReadsPastItsOwnSubsections:
    """UX-1000 (second verifier, round 140): a random sample of rows
    read `no guard named` with a real, existing guard still in the
    text - four shapes, each its own sandbox row."""

    def test_a_guard_cited_after_mutations_still_counts(self, sandbox):
        """`UX-610`/`UX-527`: the old cut dropped everything from
        `### Mutations` to the end of the Outcome, not just that
        subsection - losing a guard named in `### Deviation` or
        `### Acceptance Test`, which follow it in some Outcomes."""
        _task(sandbox, 11, (
            "## Outcome (round 1) — Done\n\n**Premise:** held.\n\n"
            "### Mutations verified red and reverted (1)\n\n"
            "| # | mutation | reddened |\n|---|---|---|\n"
            "| A | drop the check | 1 failed |\n\n"
            "### Deviation from the Required Fix\n\n"
            "`test_present.py` covers the rest.\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-11"])
        assert "| `test_present.py` (inferred) |" in body

    def test_a_path_prefixed_citation_still_counts(self, sandbox):
        """`UX-939`/`UX-302`: this corpus backticks a guard with its
        directory too (`` `tests/unit/test_x.py` ``), not just the
        bare name."""
        _task(sandbox, 12, (
            "## Outcome (round 1) — Done\n\n"
            "`tests/unit/test_present.py` covers it.\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-12"])
        assert "| `test_present.py` (inferred) |" in body

    def test_a_stub_then_real_outcome_reads_the_real_one(self, sandbox):
        """`UX-443`: `_section` returns the first `## Outcome`, a
        `_Not started._` stub, and never reaches the real one after
        it."""
        _task(sandbox, 13, (
            "## Outcome\n\n_Not started._\n\n"
            "## Outcome (round 1) — Done\n\n"
            "`test_present.py` covers it.\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-13"])
        assert "| `test_present.py` (inferred) |" in body

    def test_a_legacy_verification_log_still_counts(self, sandbox):
        """`UX-72`/`UX-81`/`UX-93`: pre-`UX-497` files carry `## Fix
        Implemented`/`## Verification Log` instead of `## Outcome`."""
        _task(sandbox, 14, (
            "## Fix Implemented\n\nDone.\n\n"
            "## Verification Log\n\n`test_present.py` passes.\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-14"])
        assert "| `test_present.py` (inferred) |" in body


class TestDeclaredAndInferredAreCountedSeparately:
    """UX-1000 (third verifier, round 142, `random.seed(142)`): 2 of 20
    sampled covered rows were false positives, both from the Outcome
    (`UX-219`, `UX-826` - a guard named while explaining why it does
    *not* discriminate something). No regex tells that prose from a
    real guard, so the page marks the kind of evidence instead."""

    def test_a_declared_only_row_counts_declared(self, sandbox):
        body = dap.area_page_body("tools", ["UX-1", "UX-2", "UX-3"])
        assert "covered 1 / 3 (declared 1, inferred 0)" in body

    def test_an_inferred_only_row_counts_inferred(self, sandbox):
        _task(sandbox, 16, (
            "## Outcome (round 1) — Done\n\n`test_present.py` covers it.\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-16"])
        assert "| `test_present.py` (inferred) |" in body
        assert "covered 1 / 1 (declared 0, inferred 1)" in body

    def test_a_row_with_both_counts_declared_not_twice(self, sandbox):
        """The Acceptance Test names one guard, the Outcome another -
        the row counts once, as declared; the Outcome's own guard
        never reaches the page (precedence stops at the first source
        naming one)."""
        _task(sandbox, 17, (
            "## Acceptance Test\n\nGuard: `test_present.py`.\n\n"
            "## Outcome (round 1) — Done\n\n`test_other.py` covers it too.\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-17"])
        assert "| `test_present.py` |" in body
        assert "test_other.py" not in body
        assert "covered 1 / 1 (declared 1, inferred 0)" in body


class TestOnlyDecisionGuardThenAcceptanceThenOutcome:

    def test_a_decision_guard_line_wins_over_acceptance_test(self, sandbox):
        _task(sandbox, 4, (
            "## Acceptance Test\n\nGuard: `test_absent.py`.\n\n"
            "## Decision\n\n```text\n"
            "Route:     x\nGuard:     `test_present.py`\nMutation:  x\n"
            "```\n"))
        tasks._FILES_BY_NUMBER.clear()
        body = dap.area_page_body("tools", ["UX-4"])
        assert "`test_present.py`" in body and "test_absent.py" not in body


class TestReportAreasStillOnlyPrints:

    def test_areas_names_the_unknown_one_and_exits_1(self, sandbox, capsys):
        assert dap.report_areas("nowhere-at-all") == 1
        assert "no such area" in capsys.readouterr().err
