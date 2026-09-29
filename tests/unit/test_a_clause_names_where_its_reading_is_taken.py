"""UX-938: an Acceptance Test names where its reading is taken, or reds.

`container`, a `runner:<job>` under `ci.yml`'s `jobs:`, an
`owner:<machine>`, or `unpayable:<reason>` - anything else, including
no field, is a clause nobody can pay and nothing said so.

holds: rules.md#an-acceptance-test-names-where-its-reading-is-taken-or-files-unpayable-with-a-reason-from-ux-938
"""

import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_close_task as close

TOOL = REPO / "tools/dev_close_task.py"


def _sandbox(tmp_path):
    into = tmp_path / "scenarios"
    into.mkdir()
    for path in (REPO / "docs/backlog/scenarios").glob("*.md"):
        shutil.copy(path, into / path.name)
    return into


def _plant(into, uid, header_line):
    """A new open row at `uid`, header's `**Priority:**` line replaced."""
    src = REPO / "docs/backlog/scenarios/UX-0938-an-acceptance-clause-can-name-a-reading-no-environment-takes.md"
    lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
    lines[0] = f"# UX-{uid}: a planted row\n"
    for i, line in enumerate(lines[:8]):
        if line.startswith("**Priority:**"):
            lines[i] = header_line
            break
    target = into / f"UX-{uid:04d}-a-planted-row.md"
    target.write_text("".join(lines), encoding="utf-8")
    row = f"| UX-{uid} | [a planted row](UX-{uid:04d}-a-planted-row.md) | guards | Medium | a test | 🔴 Not Started |\n"
    with (into / "README.md").open("a", encoding="utf-8") as index:
        index.write(row)
    return target


def _check(into):
    return subprocess.run(
        [sys.executable, str(TOOL), "--check", "--scenarios", str(into)], capture_output=True, text=True
    )


class TestAPlantedRowWithNoReadingReds:
    def test_names_the_row(self, tmp_path):
        into = _sandbox(tmp_path)
        _plant(
            into,
            9001,
            "**Priority:** Medium | **Status:** \U0001f534 Not Started | "
            "**Topic:** guards | **Area:** tools | **Shape:** mechanical\n",
        )
        run = _check(into)
        assert run.returncode == 1
        assert "UX-9001: no Reading field" in run.stdout, run.stdout


class TestARunnerJobNotInCiYmlReds:
    def test_names_the_row(self, tmp_path):
        into = _sandbox(tmp_path)
        _plant(
            into,
            9002,
            "**Priority:** Medium | **Status:** \U0001f534 Not Started | "
            "**Topic:** guards | **Area:** tools | **Shape:** mechanical | "
            "**Reading:** runner:no-such-job\n",
        )
        run = _check(into)
        assert run.returncode == 1
        assert "UX-9002: runner job 'no-such-job' is not under ci.yml's jobs:" in run.stdout, run.stdout


class TestAnUnpayableWithNoReasonReds:
    def test_names_the_row(self, tmp_path):
        into = _sandbox(tmp_path)
        _plant(
            into,
            9003,
            "**Priority:** Medium | **Status:** \U0001f534 Not Started | "
            "**Topic:** guards | **Area:** tools | **Shape:** mechanical | "
            "**Reading:** unpayable:\n",
        )
        run = _check(into)
        assert run.returncode == 1
        assert "UX-9003: 'unpayable:' names no reason" in run.stdout, run.stdout


class TestARowBelowUX938Passes:
    def test_no_field_is_no_problem(self, tmp_path):
        into = _sandbox(tmp_path)
        target = next(into.glob("UX-0900-*.md"))
        text = target.read_text(encoding="utf-8")
        assert close.header_reading(text) is None
        run = _check(into)
        assert "UX-900: no Reading field" not in run.stdout, run.stdout


class TestTheRealTreeAgrees:
    def test_zero_problems(self):
        assert close.reading_problems() == []
