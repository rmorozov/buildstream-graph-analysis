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

import dev_close_task as close_task  # noqa: E402
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
        """A pre-filled figure is an invitation to the unmeasured claim
        the `verify` skill exists to prevent.

        `UX-506` restated this from one literal phrase to the property:
        **every fenced block is a placeholder**. The literal made the
        clause a copy of the skeleton's wording, so rewording it reddened
        a guard about measurement for a reason that had nothing to do
        with one.
        """
        import re
        done = self._run("UX-336", "--outcome", "--round", "47")
        assert done.returncode == 0, done.stderr
        fences = re.findall(r"```text\n(.*?)```", done.stdout, re.S)
        assert fences, "the skeleton asks for no pasted output at all"
        for body in fences:
            assert body.strip().startswith("<") and body.strip().endswith(">"), (
                f"the skeleton pre-fills a measurement: {body.strip()!r}")
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


class TestTheIndexIsDerivedNotMerged:
    """`UX-501`: the two aggregates at the top of the backlog index.

    The `N scenarios: **M open**` sentence and the per-topic table say
    nothing the row lists do not already say. Hand-maintained, they were
    the line every parallel track collided on. Measured on two branches
    of a throwaway repository, each closing one item, with `--move`
    writing the counts as it used to:

    ```text
    CONFLICT (content): Merge conflict in scenarios/README.md
    506 scenarios: **16 open**, 490 closed.      <- 14 rows
    ```

    Both halves at once: the topic table conflicted (the two items'
    topic rows are adjacent, so git reads them as one hunk) and the
    counts sentence *auto-merged* - both sides had written the same
    decrement from the same base - into a number neither branch meant
    and nothing then checked.

    So `move` stops writing them, `--check --write` derives them from
    the rows once after the merge, and a fourth `--check` property
    asserts the derivation ran.
    """

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"), *argv],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)

    def test_the_index_says_what_its_rows_say(self):
        """The tree's own header against the derivation. This is the
        clause that catches a header edited by hand, in either
        direction."""
        sentence, table = close_task.index_header()
        text = (REPO / "docs/backlog/scenarios/README.md").read_text(
            encoding="utf-8")
        assert sentence in text, (
            "the counts sentence is not what the rows say; run "
            "`python tools/dev_close_task.py --check --write`")
        assert table in text, (
            "the topic table is not what the rows say; run "
            "`python tools/dev_close_task.py --check --write`")

    def test_the_totals_account_for_every_row(self):
        """The property the hand-written table failed: its Total column
        summed to **495** over 504 rows, so nine items were in no topic
        at all and nothing said which. A derived table cannot lose one -
        every row lands in a bucket, `unclassified` included."""
        _sentence, table = close_task.index_header()
        totals = [int(line.split("|")[3])
                  for line in table.splitlines() if line.startswith("| ")
                  and not line.startswith("| Topic")]
        rows = (len(close_task.row_ids(close_task.INDEX))
                + len(close_task.row_ids(close_task.CLOSED)))
        assert sum(totals) == rows, (
            f"the topic table accounts for {sum(totals)} of {rows} rows")

    def test_the_bucket_for_what_cannot_be_derived_is_named(self):
        """`unclassified` is not a topic anybody files under; it is the
        223 closed rows whose topic no longer exists anywhere - the
        closed row has no Topic column and they predate the
        `**Topic:**` header. Named rather than distributed by guesswork,
        so the number is visible and shrinks."""
        of = close_task.topics()
        unknown = [uid for uid, topic in of.items()
                   if topic == close_task.TOPIC_UNKNOWN]
        assert all(uid not in close_task.row_ids(close_task.INDEX)
                   for uid in unknown), (
            "an *open* row has no derivable topic - the open table has a "
            "Topic column, so this is a malformed row rather than a "
            "legacy one")

    def test_a_hand_edited_count_is_reported_and_then_restored(
            self, tmp_path):
        """The acceptance test's mutation, on a copy. `--check` alone
        must report and not repair: a checker that silently fixed what
        it checks could never fail, which is the rot the whole `--check`
        list exists to avoid."""
        import shutil
        scenarios = tmp_path / "scenarios"
        shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
        readme = scenarios / "README.md"
        was = readme.read_text(encoding="utf-8")
        readme.write_text(
            re.sub(r"^\d+ scenarios: \*\*\d+ open\*\*", "999 scenarios: **7 open**",
                   was, count=1, flags=re.M), encoding="utf-8")

        told = self._run("--check", "--scenarios", str(scenarios))
        assert told.returncode == 1, told.stdout
        assert "the counts sentence says" in told.stdout, told.stdout
        assert readme.read_text(encoding="utf-8") != was, (
            "`--check` repaired the file it was asked to check")

        fixed = self._run("--check", "--write", "--scenarios", str(scenarios))
        assert fixed.returncode == 0, fixed.stdout
        assert readme.read_text(encoding="utf-8") == was, (
            "`--write` did not restore the header the rows imply")

    def test_write_needs_check(self):
        """`--write` on its own would be a command that edits the index
        and says nothing about it."""
        done = self._run("--write")
        assert done.returncode != 0
        assert "give both" in done.stderr, done.stderr

    def test_closing_a_task_no_longer_writes_the_aggregates(self):
        """The change itself, read off the source rather than run: a
        `move` that writes the header puts both tracks on the same line
        again, and the clause above would still pass because a single
        close computes the right number.

        Read as text because the discriminating case is a two-branch
        merge, and this file is the fast tier."""
        body = (REPO / "tools/dev_close_task.py").read_text(encoding="utf-8")
        move = body.split("def move(", 1)[1].split("\ndef ", 1)[0]
        assert "write_index()" not in move, (
            "`move` writes the derived header again, so two tracks each "
            "closing one item collide on it - UX-501's own measurement")
        assert "--check --write" in move, (
            "`move` neither writes the header nor says what does")

    def test_the_merge_recipe_is_written_down(self):
        """A tool nobody is told to run after a merge is a tool that
        does not run after a merge."""
        skill = (REPO / ".claude/skills/decompose/SKILL.md").read_text(
            encoding="utf-8")
        assert "--check --write" in skill, (
            "the decompose skill's shared-files section does not name the "
            "command that resolves the counts")


class TestTheSkeletonFitsTheRegister:
    """`UX-506`: the shape the skeleton asks for is the shape that fits.

    Counted over round 74's range (`UX-440`..`UX-496`), under the
    skeleton `UX-336` printed:

    ```text
    Outcomes written              56
    median length                117 lines
    longest                      284
    over the 80-line cap         45   (80 %)
    ```

    The skeleton was never over the cap - the prose under it was - but
    it *invited* the prose: a heading reading "what the fix had to be,
    and why that shape" asks for a narrative and gets one. It is gone;
    what the headings now name is what a later round reads.

    Two things the skeleton must keep, and a clause each. It seeds
    `dev_process_bands.py`'s census - the phrases that tool counts are
    printed by this skeleton and by nothing else - and it states the cap,
    so a session sees the budget while writing rather than when the
    guard reds.
    """

    def _printed(self):
        return close_task.OUTCOME_SKELETON.format(
            round="NN", date="YYYY-MM-DD", n=2,
            cap=close_task.OUTCOME_CAP)

    def test_the_skeleton_seeds_the_process_census(self):
        """`dev_process_bands.py` counts phrases this repository already
        writes by convention rather than fields anyone fills in - and the
        convention is this skeleton. A reworded heading silently drops a
        row of a census over 288 closed items to zero, and nothing else
        would say so."""
        import dev_process_bands as bands
        printed = self._printed()
        for key in ("falsified",):
            pattern = next(p for k, _h, p in bands.SIGNALS if k == key)
            assert pattern.search(printed), (
                f"the skeleton no longer prints what `{key}` counts; "
                f"dev_process_bands.py reads the committed record for "
                f"this phrase and would report 0 %")
        assert "Deviation from the Required Fix" in printed, (
            "the deviation heading is what `deviated` is measured from, "
            "in both directions")

    def test_it_leaves_room_under_the_cap(self):
        """A skeleton that filled the budget would make the cap
        unreachable, which is a different defect from the one this item
        is about."""
        printed = len(self._printed().strip().splitlines())
        assert printed < close_task.OUTCOME_CAP * 0.6, (
            f"the skeleton is {printed} lines of a {close_task.OUTCOME_CAP}-"
            f"line budget; there is no room left for the measurements")

    def test_it_states_the_cap_the_guard_holds(self):
        """One copy. A skeleton that names a different number than the
        guard enforces sends every session to the wrong budget."""
        assert str(close_task.OUTCOME_CAP) in self._printed(), (
            "the skeleton does not tell a session what the budget is")
        source = (REPO / "tests/unit/test_the_register_is_terse.py").read_text(
            encoding="utf-8")
        assert f"OUTCOME_CAP = {close_task.OUTCOME_CAP}" in source, (
            f"the tool prints a cap of {close_task.OUTCOME_CAP} and the "
            f"guard holds a different one")

    def test_it_asks_for_no_narrative(self):
        """The heading this item removed, by name. A skeleton that asks
        "why that shape" gets a page of design history, and the task
        file is not where design history goes - the register is."""
        printed = self._printed()
        for asked in ("why that shape", "Counts are what the run printed"):
            assert asked not in printed, (
                f"the skeleton still asks for {asked!r}")
