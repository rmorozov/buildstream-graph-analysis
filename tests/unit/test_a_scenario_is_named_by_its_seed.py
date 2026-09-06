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
