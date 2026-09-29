"""UX-1092: every task file names its guard on one `**Guard:**` line -
test files by name, or `none — <reason>` - and `--check` refuses a
file with no line, `none` with no reason, or a name absent under
`tests/`.

holds: rules.md#a-task-file-carries-one-guard-line-under-its-header-its-test-file-s-or-none-reason-ux-1092
"""

import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_area_pages as dap
import dev_close_task as tasks

HEADER = (
    "# UX-{n}: x\n\n**Priority:** Low | **Status:** \N{LARGE RED CIRCLE}"
    " Not Started | **Topic:** guards | **Area:** tools\n\n"
)


#: The highest id r149's backfill wrote; a later line is its author's.
BACKFILLED_THROUGH = 1093
MARK = " · inferred r149"


def unmarked_inferences(scenarios):
    """Backfilled files whose plain `**Guard:**` line names a file its
    `## Decision` and `## Acceptance Test` never do - prose, unmarked."""
    found = []
    for path in sorted(scenarios.glob("UX-*.md")):
        number = re.match(r"UX-0*(\d+)-", path.name)
        if not number or int(number.group(1)) > BACKFILLED_THROUGH:
            continue
        text = path.read_text(encoding="utf-8")
        line = re.search(r"^\*\*Guard:\*\*(.*)$", text.split("\n## ", 1)[0], re.M)
        if not line or line.group(1).rstrip().endswith(MARK.strip()):
            continue
        names, _reason = tasks.checks.header_guard(text)
        stated = "".join(part.split("\n## ", 1)[0] for part in re.split(r"\n## (?=Decision|Acceptance Test)", text)[1:])
        found += [f"{path.name}: {name}" for name in names if name not in stated]
    return found


def _guard_check():
    """The property as `--check` runs it, found by what it calls."""
    return next(run for _what, run in tasks.CHECKS if "guard_problems" in run.__code__.co_names)


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
            HEADER.format(n=n) + guard_line + "\n\n## Motivation\n\nx\n", encoding="utf-8"
        )

    write(1, "**Guard:** test_present.py")
    write(2, "**Guard:** none — a doc-only row")
    return write


class TestTheCheckRefuses:
    def test_a_fielded_sandbox_passes(self, sandbox):
        assert _guard_check()() == []

    def test_a_row_with_no_field(self, sandbox):
        """The Acceptance Test's mutation: drop one row's field."""
        sandbox(3, "")
        assert _guard_check()() == ["UX-0003-x.md: no **Guard:** line above its first heading"]

    def test_none_with_no_reason(self, sandbox):
        sandbox(3, "**Guard:** none")
        [problem] = _guard_check()()
        assert problem.startswith("UX-0003-x.md: **Guard:** names no")

    def test_a_named_file_absent_from_tests(self, sandbox):
        sandbox(3, "**Guard:** test_present.py, test_absent.py")
        assert _guard_check()() == ["UX-0003-x.md: **Guard:** test_absent.py is absent from tests/"]

    def test_a_none_reason_naming_a_dead_file_is_not_a_name(self, sandbox):
        """The backfill's `none — named <file>, absent from tests/`."""
        sandbox(3, "**Guard:** none — named test_absent.py, absent from tests/")
        assert _guard_check()() == []


class TestAnInferenceIsMarked:
    def test_a_plain_line_from_the_outcome_is_found(self, tmp_path):
        (tmp_path / "UX-0009-x.md").write_text(
            HEADER.format(n=9) + "**Guard:** test_present.py\n\n## Outcome\n\n`test_present.py` holds it.\n"
        )
        assert unmarked_inferences(tmp_path) == ["UX-0009-x.md: test_present.py"]

    def test_the_mark_or_a_stated_name_is_not(self, tmp_path):
        (tmp_path / "UX-0009-x.md").write_text(
            HEADER.format(n=9) + "**Guard:** test_present.py" + MARK + "\n\n## Outcome\n\n`test_present.py` holds it.\n"
        )
        (tmp_path / "UX-0010-x.md").write_text(
            HEADER.format(n=10) + "**Guard:** test_present.py\n\n## Acceptance Test\n\n`test_present.py` reds.\n"
        )
        assert unmarked_inferences(tmp_path) == []


class TestTheRealTree:
    """Green once the one-shot backfill has run (`UX-1092`'s step B)."""

    def test_every_task_file_names_an_existing_guard(self):
        problems = tasks.checks.guard_problems(tasks.SCENARIOS, tasks.TESTS_ROOT)
        assert problems == [], f"{len(problems)} problem(s): {problems[:5]}"

    def test_no_inference_is_unmarked(self):
        found = unmarked_inferences(tasks.SCENARIOS)
        assert found == [], f"{len(found)} unmarked: {found[:5]}"

    def test_no_area_page_reads_a_row_without_its_line(self):
        for area, ids in tasks.area_pages().items():
            body = dap.area_page_body(area, ids)
            assert "(inferred)" not in body, area
            assert body.rstrip().endswith(", no line 0)"), (area, body.rstrip().splitlines()[-1])
