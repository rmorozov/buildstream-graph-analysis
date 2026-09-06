"""UX-685: a walk is a seeded scenario, and its report grows the key.

Three claims: `dev_scenario.py --seed N` draws the same scenario every
time and a different one for a different seed; the scripted walk
names every input class the `decompose` skill's own table lists; a
walk report that follows the `walk` skill's shape is required to name
its seed and the answer-key rows it added, and one that does not is
caught rather than read as an ordinary round document.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import tools.dev_scenario as scenario


def test_the_same_seed_reruns_identically():
    assert scenario.scripted_walk(1) == scenario.scripted_walk(1)


def test_two_seeds_draw_different_scenarios():
    """Measured over the open backlog: seeds 1 and 2 disagree on the
    area and on at least one input class - not merely the RNG state."""
    one, two = scenario.draw(1), scenario.draw(2)
    assert one["area"] != two["area"] or one["classes"] != two["classes"], (
        one, two)


def test_the_walk_names_every_partition_dimension():
    """Every dimension `decompose`'s §2 table lists is drawn, not a
    subset chosen here - a class the skill adds shows up unasked."""
    classes = scenario.partition_classes()
    assert set(classes) == {"population", "contract version", "capture mode",
                            "Plane 2", "reader", "host"}, classes
    drawn = scenario.draw(3)["classes"]
    assert set(drawn) == set(classes)


def test_the_scripted_walk_names_the_capture_recipe_and_the_census():
    printed = scenario.scripted_walk(1)
    assert "capture recipe:" in printed
    assert "tools/dev_page_census.py" in printed
    assert "report shape:" in printed and "seed" in printed


class TestAWalkReportNamesItsSeedAndItsRows:
    """The Acceptance Test's mutation, run directly: a report of the
    `walk` skill's shape (`capture` / `findings`) with its `seed` line
    removed is exactly what `report_problems` must catch."""

    GOOD = ("capture      2026-09-06 - macro/micro recording\n"
            "seed         1\n"
            "answer key   3 lines\n"
            "per plane    plane1 | said X | match\n"
            "findings     none new\n"
            "friction     nothing notable\n"
            "rows added   0\n")

    def test_a_conforming_report_is_clean(self):
        assert scenario.report_problems([("r.md", self.GOOD)]) == []

    def test_removing_the_seed_line_reds_the_guard(self):
        mutated = self.GOOD.replace("seed         1\n", "")
        problems = scenario.report_problems([("r.md", mutated)])
        assert problems == ["r.md: no seed line"], problems

    def test_removing_the_rows_added_line_reds_the_guard(self):
        mutated = self.GOOD.replace("rows added   0\n", "")
        problems = scenario.report_problems([("r.md", mutated)])
        assert problems == ["r.md: no answer-key rows added line"], problems

    def test_a_document_that_is_not_walk_shaped_is_left_alone(self):
        """`is_walk_report` must discriminate - a round document that
        never claims the walk's shape names no seed and is not a
        walk report missing one."""
        ordinary = "# Round 96\n\nSome prose about a walk, no fields.\n"
        assert scenario.report_problems([("round-96.md", ordinary)]) == []

    def test_every_real_walk_shaped_document_names_its_seed_and_rows(self):
        """The guard as it runs for real, over every tracked file under
        `docs/audits/` (`git ls-files`, so a worktree's own copies are
        not double-counted)."""
        problems = scenario.report_problems(scenario.audits_documents())
        assert problems == [], problems


class TestTheRecipeIsRunnable:
    """`UX-685` seed 1's answer-key row, **now the rule it was filed for**.

    The row recorded the gap the first seeded walk found:

        $ bga gen-synthetic --seed 1 --elements 1 /tmp/gsprobe
        bga gen-synthetic: error: unrecognized arguments: --elements ...

    `UX-723` closed it, so these assert the promise instead. A rerun of
    seed 1 says the row held by passing.
    """

    def test_the_population_recipe_names_a_project_and_a_target(self):
        """Not a planted run. `gen-synthetic` writes `graph.json` and
        friends; the recipe's next line then asks for a `bst build`,
        and the two cannot both be the input."""
        recipes = scenario._RECIPE["population"]
        assert "gen-synthetic" not in " ".join(recipes.values())
        for key, text in recipes.items():
            assert "examples/" in text, (key, text)
            assert "bst build" in text or "built twice" in text, (key, text)

    def test_the_three_plane_two_recipes_are_three_commands(self):
        """One command under two annotations was the defect. `absent`
        is not `snapshot` at all - no flag omits Plane 2 (`UX-726`)."""
        rows = scenario._RECIPE["Plane 2"]
        assert len(set(rows.values())) == 3, rows
        assert "snapshot" not in rows["absent"] or "not" in rows["absent"]
        assert "--trace-spine=off" in rows["hook only"]
        assert "--trace-spine=on" in rows["spine on"]


class TestEveryPrintedCommandRuns:
    """`UX-723`'s acceptance: the script the seed prints is runnable.

    Seed 1's walk found `bga gen-synthetic --seed N --elements 1` in the
    recipe; the flag does not exist. Nothing checked, because the recipe
    is a table of strings and no clause read them as commands.

    This parses every `bga <sub> ...` the recipe prints against that
    subcommand's own `--help`, which is the source of truth an
    `argparse` CLI already keeps. Paths and `<target>` placeholders are
    not resolved - a command that names a file is checked for its
    *flags*, not run.
    """

    #: Every seed's recipe, over a fixed sample. Ten is the Acceptance
    #: Test's own number and costs 0.4s: the tool shells out to nothing.
    SEEDS = range(1, 11)

    @staticmethod
    def _bga_commands(text):
        """`bga ...` fragments inside backticks, one per match."""
        return [found.strip() for found in
                re.findall(r"`(bga [^`]+)`", text)]

    @staticmethod
    def _flags(command):
        """The `--flag` tokens in one command fragment."""
        return [token.split("=")[0] for token in command.split()
                if token.startswith("--") and token != "--"]

    def _known_flags(self, sub):
        import subprocess

        done = subprocess.run(["bga", sub, "--help"], capture_output=True,
                              text=True, timeout=60)
        if done.returncode != 0:
            return None
        return set(re.findall(r"(--[a-z0-9-]+)", done.stdout))

    def test_every_recipe_command_names_a_real_subcommand(self):
        import subprocess

        subs = set(re.findall(r"^\s+\{?([a-z][a-z0-9,-]*)\}?",
                              subprocess.run(["bga", "--help"],
                                             capture_output=True, text=True,
                                             timeout=60).stdout, re.M))
        named = {command.split()[1]
                 for seed in self.SEEDS
                 for command in self._bga_commands(scenario.scripted_walk(seed))}
        unknown = sorted(name for name in named
                         if not any(name in group.split(",")
                                    for group in subs))
        assert unknown == [], (
            f"the recipe names subcommand(s) `bga` does not have: {unknown}")

    def test_every_recipe_flag_is_one_its_subcommand_takes(self):
        """The clause seed 1's finding needed. `--elements` parsed as a
        word before this; it is checked against `gen-synthetic --help`
        now, for every seed in the sample."""
        wrong = []
        for seed in self.SEEDS:
            for command in self._bga_commands(scenario.scripted_walk(seed)):
                sub = command.split()[1]
                known = self._known_flags(sub)
                if known is None:
                    wrong.append(f"seed {seed}: `bga {sub} --help` refused")
                    continue
                for flag in self._flags(command):
                    if flag not in known:
                        wrong.append(f"seed {seed}: `{command}` -> {flag}")
        assert wrong == [], "\n".join(wrong)
