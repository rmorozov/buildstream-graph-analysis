"""UX-920: `--check` fails when one id names two task files, or a heading
names an id its filename does not.

Two branches filing under one id merge clean - two new files, no
conflict - and `task_file` answers with the first, so nothing read the
second. The tree is silent; the guard is proved by writing the second
file.
"""
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import _close_task_checks as checks
import dev_close_task as close_task

FIRST = "UX-0917-the-fold-depth-guard-has-three-unconfirmed-excursions.md"
SECOND = "UX-0917-hidden-findings-keep-live-controls.md"


def _copy(tmp_path):
    scenarios = tmp_path / "scenarios"
    shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
    assert (scenarios / FIRST).exists(), "fixture: UX-917's file was renamed"
    return scenarios


def _run(*argv):
    return subprocess.run(
        [sys.executable, str(REPO / "tools/dev_close_task.py"), *argv],
        capture_output=True, text=True, cwd=str(REPO), timeout=120)


class TestOneIdNamesOneTaskFile:

    def test_the_tree_is_silent(self):
        assert checks.id_problems(close_task.SCENARIOS, REPO) == []

    def test_a_second_file_under_an_existing_id_fails_naming_both(
            self, tmp_path):
        scenarios = _copy(tmp_path)
        (scenarios / SECOND).write_text(
            "# UX-917: hidden findings keep live controls\n", encoding="utf-8")
        done = _run("--check", "--scenarios", str(scenarios))
        assert done.returncode == 1, done.stdout + done.stderr
        line = next((line for line in done.stdout.splitlines()
                     if "UX-917 names 2 files" in line), "")
        assert FIRST in line and SECOND in line, done.stdout

    def test_a_heading_that_names_another_id_fails_naming_both(
            self, tmp_path):
        scenarios = _copy(tmp_path)
        stray = scenarios / "UX-9999-a-row-filed-under-a-taken-id.md"
        stray.write_text("# UX-917: a row filed under a taken id\n",
                         encoding="utf-8")
        found = checks.id_problems(scenarios, REPO)
        assert len(found) == 1, found
        assert stray.name in found[0] and FIRST in found[0], found
