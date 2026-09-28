"""UX-1092: every task file names its guard on one `**Guard:**` line -
test files by name, or `none — <reason>` - and `--check` refuses a
file with no line, `none` with no reason, or a name absent under
`tests/`.

holds: rules.md#a-task-file-carries-one-guard-line-under-its-header-its-test-file-s-or-none-reason-ux-1092
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_area_pages as dap
import dev_close_task as tasks

HEADER = ("# UX-{n}: x\n\n**Priority:** Low | **Status:** \N{LARGE RED CIRCLE}"
          " Not Started | **Topic:** guards | **Area:** tools\n\n")


def _guard_check():
    """The property as `--check` runs it, found by what it calls."""
    return next(run for _what, run in tasks.CHECKS
                if "guard_problems" in run.__code__.co_names)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_present.py").write_text("")
    monkeypatch.setattr(tasks, "SCENARIOS", scenarios)
    monkeypatch.setattr(tasks, "TESTS_ROOT", tmp_path / "tests")

    def write(n, guard_line):
        (scenarios / f"UX-{n:04d}-x.md").write_text(
            HEADER.format(n=n) + guard_line + "\n\n## Motivation\n\nx\n",
            encoding="utf-8")
    write(1, "**Guard:** test_present.py")
    write(2, "**Guard:** none — a doc-only row")
    return write


class TestTheCheckRefuses:

    def test_a_fielded_sandbox_passes(self, sandbox):
        assert _guard_check()() == []

    def test_a_row_with_no_field(self, sandbox):
        """The Acceptance Test's mutation: drop one row's field."""
        sandbox(3, "")
        assert _guard_check()() == [
            "UX-0003-x.md: no **Guard:** line above its first heading"]

    def test_none_with_no_reason(self, sandbox):
        sandbox(3, "**Guard:** none")
        [problem] = _guard_check()()
        assert problem.startswith("UX-0003-x.md: **Guard:** names no")

    def test_a_named_file_absent_from_tests(self, sandbox):
        sandbox(3, "**Guard:** test_present.py, test_absent.py")
        assert _guard_check()() == [
            "UX-0003-x.md: **Guard:** test_absent.py is absent from tests/"]

    def test_a_none_reason_naming_a_dead_file_is_not_a_name(self, sandbox):
        """The backfill's `none — named <file>, absent from tests/`."""
        sandbox(3, "**Guard:** none — named test_absent.py, absent from tests/")
        assert _guard_check()() == []


class TestTheRealTree:
    """Green once the one-shot backfill has run (`UX-1092`'s step B)."""

    def test_every_task_file_names_an_existing_guard(self):
        problems = tasks.checks.guard_problems(tasks.SCENARIOS,
                                               tasks.TESTS_ROOT)
        assert problems == [], f"{len(problems)} problem(s): {problems[:5]}"

    def test_no_area_page_reads_a_row_without_its_line(self):
        for area, ids in tasks.area_pages().items():
            body = dap.area_page_body(area, ids)
            assert "(inferred)" not in body, area
            assert body.rstrip().endswith(", no line 0)"), (
                area, body.rstrip().splitlines()[-1])
