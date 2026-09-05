"""UX-688: the hierarchy is a view, derived from a header.

Eight topics were the only grouping, and impact analysis started by
rescanning hundreds of files. The area is a path in the module tree the
fixing guide's §6 already maintains, so the vocabulary is **read from
that section** rather than typed beside it, and the pages under
`docs/backlog/areas/` are regenerated whole from the headers.

What the filing asked for and the tree could not give: the 682 rows
back-derived from their closing commits. Measured, that places 122 of
714 decisively and makes `tests/unit` the modal area, because every
task commit touches its own guard. Restricted to `bga/` and `tools/`
paths it places 300, and the rest are the `AREA_UNKNOWN` bucket
`UX-501` established for exactly this - a population no derivation
reaches, left visible instead of distributed by guesswork.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_close_task

#: The row that introduced the field. Everything filed from here on
#: carries one; older rows are back-filled only where git was decisive.
FIRST = 688


class TestTheVocabularyIsTheModuleTree:

    def test_the_areas_come_from_the_fixing_guide(self):
        areas = dev_close_task.declared_areas()
        assert "bga/floors" in areas and "bga/graph" in areas, sorted(areas)
        assert "docs" not in areas, "areas are code, not documents"

    def test_an_area_outside_the_tree_is_a_problem(self):
        """The row's own mutation, run in-process on a fake header."""
        assert dev_close_task.header_area(
            "**Topic:** guards | **Area:** bga/nowhere") == "bga/nowhere"
        assert "bga/nowhere" not in dev_close_task.declared_areas()


class TestEveryRowFiledSinceCarriesOne:

    def test_the_rows_this_item_introduced_declare_an_area(self):
        missing = []
        for path in sorted(dev_close_task.SCENARIOS.glob("UX-*.md")):
            if not dev_close_task._FILE_ID.match(path.name):
                continue
            uid = int(path.name.split("-")[1])
            if uid >= FIRST and not dev_close_task.header_area(
                    path.read_text(encoding="utf-8")):
                missing.append(path.name)
        assert not missing, f"filed since UX-{FIRST} without an Area: {missing}"

    def test_every_declared_area_is_known(self):
        assert dev_close_task.area_problems() == []

    def test_the_check_reports_an_area_outside_the_tree(self, monkeypatch):
        """`== []` passes whatever the property does — the first cut of
        this clause survived deleting the comparison. So the population
        is replaced with one known-bad row and the report must name it."""
        monkeypatch.setattr(dev_close_task, "file_areas",
                            lambda: {"UX-1": "bga/nowhere"})
        found = dev_close_task.area_problems()
        assert len(found) == 1 and "bga/nowhere" in found[0], found


class TestThePagesAreGeneratedFromTheHeaders:

    def test_every_area_with_rows_has_a_page(self):
        pages = dev_close_task.area_pages()
        assert pages, "no area has rows"
        for area in pages:
            page = dev_close_task.AREA_PAGES / (area.replace("/", "-") + ".md")
            assert page.exists(), f"{area} has rows and no page"

    def test_a_page_counts_the_rows_it_lists(self):
        """The count in the sentence is the length of the table."""
        for area, ids in dev_close_task.area_pages().items():
            page = dev_close_task.AREA_PAGES / (area.replace("/", "-") + ".md")
            text = page.read_text(encoding="utf-8")
            assert f"{len(ids)} row(s)" in text, area
            assert text.count("\n| [UX-") == len(ids), area
