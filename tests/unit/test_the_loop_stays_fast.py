"""UX-336: the levers that made the loop fast, held in place.

Four of them are configuration, and configuration rots silently: a
`Makefile` target loses a flag in a merge, a dev extra is dropped when
someone tidies `pyproject.toml`, and the suite goes back to ten minutes
without anything going red. The wall-clock numbers themselves are *not*
guarded — they are a property of the machine, and a guard on them would
fail on a slower laptop for no defect. What is guarded is that the
mechanism is still wired up, and that the selector still selects.
"""
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import dev_touching  # noqa: E402

MAKEFILE = (REPO / "Makefile").read_text(encoding="utf-8")
PYPROJECT = (REPO / "pyproject.toml").read_text(encoding="utf-8")


class TestTheSuiteStillRunsInParallel:

    def test_every_test_target_carries_the_parallel_flag(self):
        """375s -> 148.7s in the audit's trial, 642s -> 194s re-measured
        here. A target that loses `$(PYTEST_XDIST)` gets the old number
        back and says nothing."""
        targets = re.findall(r"^(test[a-z-]*):\n\t(.+)$", MAKEFILE, re.M)
        assert targets, "no test targets found; the Makefile shape moved"
        missing = [name for name, body in targets
                   if "pytest" in body and "$(PYTEST_XDIST)" not in body]
        assert not missing, (
            f"{missing} run pytest without $(PYTEST_XDIST). Every tier runs "
            "parallel or the loop is back where UX-336 found it.")

    def test_the_flag_defaults_to_auto_and_can_be_turned_off(self):
        assert re.search(r"^PYTEST_XDIST \?= -n auto$", MAKEFILE, re.M), (
            "PYTEST_XDIST is not defaulted to `-n auto`, or is no longer "
            "overridable with `?=` - the off switch is what makes `-x` and "
            "`pdb` usable")

    def test_xdist_is_a_declared_dev_dependency(self):
        assert "pytest-xdist" in PYPROJECT, (
            "pytest-xdist is not in the dev extras, so a fresh "
            "`pip install -e '.[dev]'` cannot run `make test`")
        assert '"pytest-xdist' in PYPROJECT.split("[project.optional-dependencies]")[1].split("\n]")[0], (
            "pytest-xdist is mentioned but not in the dev extra list")

    def test_ci_still_runs_the_small_tier_single_process(self):
        """The one thing parallelism can hide: an ordering assumption.
        CI runs the tier both ways so a test that only passes because
        xdist happened to separate it cannot ship."""
        ci = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "PYTEST_XDIST= " in ci, (
            "no CI step runs a tier single-process; a suite that is only "
            "ever run parallel has untested parallel-safety")


class TestTheSelectorStillSelects:

    def test_a_one_module_change_selects_a_handful_not_the_suite(self):
        selected, _ = dev_touching.select(["bga/store_aggregate.py"])
        assert 1 <= len(selected) <= 25, (
            f"a one-module diff selected {len(selected)} files. The point is "
            "to be faster than the tier; selecting everything is not.")
        assert "tests/unit/test_the_aggregate_says_what_it_mixes.py" in selected, (
            "the file whose whole subject is the changed module was not "
            f"selected: {selected}")

    def test_a_changed_test_file_runs_itself(self):
        selected, _ = dev_touching.select(
            ["tests/unit/test_the_loop_stays_fast.py"])
        assert "tests/unit/test_the_loop_stays_fast.py" in selected

    def test_a_shared_harness_change_selects_everything(self):
        """The honest edge: `conftest.py` and `tiers.py` are changes to
        every test, and a selector that pretended otherwise would be
        wrong on exactly the days it matters."""
        selected, why = dev_touching.select(["tests/conftest.py"])
        assert len(selected) == len(dev_touching.test_files())
        assert "*" in why

    def test_a_documentation_change_selects_the_guards_that_read_it(self):
        selected, _ = dev_touching.select(["docs/guides/cli.md"])
        assert "tests/unit/test_docs_links_and_commands.py" in selected, (
            "a guide changed and the guard that reads guides was not "
            f"selected - grep, not the import graph, is the whole reason "
            f"this works: {selected}")

    def test_a_one_word_module_stem_is_not_used_as_a_token(self):
        """`findings` is also an English word this project uses
        constantly - measured, 57 files matched against 7 for
        `store_aggregate`. The stem is only distinctive with a `_`."""
        assert "findings" not in dev_touching.tokens_for("bga/findings.py")
        assert "store_aggregate" in dev_touching.tokens_for(
            "bga/store_aggregate.py")


class TestTheCloseHelperRefusesTheJudgementParts:

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"), *argv],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)

    def test_check_reports_a_clean_tree_as_clean(self):
        done = self._run("--check")
        assert done.returncode == 0, done.stdout + done.stderr

    def test_the_outcome_skeleton_leaves_every_measurement_blank(self):
        done = self._run("UX-336", "--outcome", "--round", "47")
        assert done.returncode == 0, done.stderr
        assert "<paste the command and its real output" in done.stdout, (
            "the skeleton pre-fills a measurement, which is an invitation to "
            "the unmeasured claim the verify skill exists to prevent")
        for heading in ("## Outcome", "Mutations verified red and reverted",
                        "Deviation from the Required Fix"):
            assert heading in done.stdout, heading

    @staticmethod
    def _backlog_with_an_open_row(tmp_path):
        """A copy of the backlog with one synthetic open row in it.

        Both refusals below need an id that is open and has no Outcome.
        They used to name a real one, and `UX-337` closing turned this
        file red for a reason that had nothing to do with the loop -
        the guard was coupled to which task happened to be unfinished.
        A row this test writes itself cannot go stale, and the copy is
        deliberate: falsifying the refusal made the clause perform the
        move, and a guard that edits the repository when the code under
        test misbehaves is worse than what it is testing.
        """
        import shutil

        scenarios = tmp_path / "scenarios"
        shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
        uid, slug = "UX-999", "UX-0999-a-row-this-guard-wrote"
        (scenarios / f"{slug}.md").write_text(
            f"# {uid}: a row this guard wrote\n\n"
            f"**Priority:** Low | **Status:** \U0001f534 Not Started | "
            f"**Serves:** nobody | **Topic:** guards\n\n"
            f"## Motivation\n\nNo Outcome section, which is the point.\n",
            encoding="utf-8")
        readme = scenarios / "README.md"
        text = readme.read_text(encoding="utf-8")
        marker = "\n## UX-333"
        assert marker in text, "the open table's end moved"
        row = (f"| {uid} | [a row this guard wrote]({slug}.md) | guards "
               f"| Low | — | \U0001f534 |\n")
        readme.write_text(text.replace(marker, "\n" + row + marker, 1),
                          encoding="utf-8")
        return uid, scenarios

    def test_move_refuses_without_the_one_line_nobody_can_write_for_you(
            self, tmp_path):
        uid, scenarios = self._backlog_with_an_open_row(tmp_path)
        done = self._run(uid, "--move", "--scenarios", str(scenarios))
        assert done.returncode != 0
        assert "--note" in done.stderr

    def test_move_refuses_a_task_file_with_no_outcome(self, tmp_path):
        uid, scenarios = self._backlog_with_an_open_row(tmp_path)
        before = (scenarios / "README.md").read_bytes()
        done = self._run(uid, "--move", "--note", "x" * 20,
                         "--scenarios", str(scenarios))
        assert done.returncode == 2, done.stdout + done.stderr
        assert "no Outcome section" in done.stderr, done.stderr
        assert (scenarios / "README.md").read_bytes() == before, (
            "a refused --move still wrote to the index")

    def test_the_verify_skill_cites_the_helper(self):
        """A scaffold nobody is told about is a scaffold nobody uses."""
        skill = (REPO / ".claude/skills/verify/SKILL.md").read_text(
            encoding="utf-8")
        assert "dev_close_task.py" in skill
        assert "make test-touching" in skill
