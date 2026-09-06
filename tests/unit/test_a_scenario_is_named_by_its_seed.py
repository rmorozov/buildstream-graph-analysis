"""UX-685: a walk is a seeded scenario, and its report grows the key.

Three claims: `dev_scenario.py --seed N` draws the same scenario every
time and a different one for a different seed; the scripted walk
names every input class the `decompose` skill's own table lists; a
walk report that follows the `walk` skill's shape is required to name
its seed and the answer-key rows it added, and one that does not is
caught rather than read as an ordinary round document.
"""
import pathlib
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
    """`UX-685` seed 1's answer-key row, and it records a **gap**.

    The first seeded walk found the recipe unrunnable in its first
    minute:

        $ bga gen-synthetic --seed 1 --elements 1 /tmp/gsprobe
        bga gen-synthetic: error: unrecognized arguments: --elements ...

    Asserted as it *is*, so a rerun of seed 1 says the row held.
    `UX-723` is the fix; closing it reddens these clauses, which is the
    point - they then become the rule rather than the gap.
    """

    def test_the_population_recipe_names_a_flag_that_does_not_exist(self):
        from tools.dev_scenario import _RECIPE

        assert "--elements" in _RECIPE["population"]["1"], (
            "the population recipe no longer names `--elements` - UX-723 "
            "has landed, so this row must become the rule it was filed "
            "for: every command the recipe prints parses against `--help`")

    def test_the_two_plane_two_recipes_are_the_same_command(self):
        from tools.dev_scenario import _RECIPE

        absent, hook = (_RECIPE["Plane 2"]["absent"],
                        _RECIPE["Plane 2"]["hook only"])
        command = "`bga snapshot -- bst build all.bst`"
        assert absent.startswith(command) and hook.startswith(command), (
            "the two Plane 2 recipes no longer print one command under two "
            "annotations - UX-723 has landed; assert what each now runs")

