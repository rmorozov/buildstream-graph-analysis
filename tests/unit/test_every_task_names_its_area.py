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


class TestEveryTopLevelDirectoryIsRead:
    """`UX-937`: the vocabulary is every top-level directory §6's tree
    names, with its subdirectories - not an alternation of two of them."""

    @staticmethod
    def _guide(tmp_path, monkeypatch, edit):
        guide = tmp_path / "fixing-guide.md"
        text = dev_close_task.AREA_GUIDE.read_text(encoding="utf-8")
        edited = edit(text)
        assert edited != text, "the edit did not land"
        guide.write_text(edited, encoding="utf-8")
        monkeypatch.setattr(dev_close_task, "AREA_GUIDE", guide)

    def test_tests_is_an_area(self):
        areas = dev_close_task.declared_areas()
        assert {"tests", "tests/unit"} <= areas, sorted(areas)

    def test_a_row_declaring_tests_passes_and_a_stray_one_does_not(
            self, monkeypatch):
        monkeypatch.setattr(dev_close_task, "file_areas", lambda: {
            "UX-1": "tests", "UX-2": "tests/unit", "UX-3": "bga/nowhere"})
        found = dev_close_task.area_problems()
        assert len(found) == 1 and "UX-3" in found[0], found

    def test_a_line_leaving_the_tree_leaves_the_vocabulary(
            self, tmp_path, monkeypatch):
        """The discriminating one: a fix that types `tests/unit` passes
        the clauses above and fails this."""
        self._guide(tmp_path, monkeypatch, lambda text: "\n".join(
            line for line in text.splitlines()
            if not line.startswith("tests/unit/ ")))
        areas = dev_close_task.declared_areas()
        assert "tests/unit" not in areas and "tests" in areas, sorted(areas)

    def test_a_line_joining_the_tree_joins_the_vocabulary(
            self, tmp_path, monkeypatch):
        self._guide(tmp_path, monkeypatch, lambda text: text.replace(
            "\ntests/unit/ ", "\nnowhere/deep/  x\ntests/unit/ ", 1))
        assert {"nowhere", "nowhere/deep"} <= dev_close_task.declared_areas()


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
    """`UX-996`: a page is printed by `area_page_body`/`--areas`, never
    committed - `docs/backlog/areas/` is `git rm`ed."""

    def test_the_directory_is_gone(self):
        """`git rm`ed a directory whose only contents were the pages
        (`UX-996`) leaves nothing on disk either - the tracked-vs-not
        distinction `git ls-files` would draw is checked once, in
        `test_a_derived_figure_is_printed_not_committed.py`."""
        assert not (dev_close_task.REPO / "docs/backlog/areas").exists()

    def test_every_area_with_rows_prints_a_page(self):
        pages = dev_close_task.area_pages()
        assert pages, "no area has rows"
        for area, ids in pages.items():
            body = dev_close_task.area_page_body(area, ids)
            assert body.startswith(f"# {area}\n"), area

    def test_a_page_counts_the_rows_it_lists(self):
        """The count in the sentence is the length of the table."""
        for area, ids in dev_close_task.area_pages().items():
            body = dev_close_task.area_page_body(area, ids)
            assert f"{len(ids)} row(s)" in body, area


class TestTheGeneratedPageLinksItsHandWrittenMechanism:
    """`UX-689`: a printed area page names its hand-written companion
    if one exists — derived from the file's existence, so a page
    without one carries nothing."""

    def _body(self, name):
        pages = dev_close_task.area_pages()
        [area] = [a for a in pages if a.replace("/", "-") + ".md" == name]
        return dev_close_task.area_page_body(area, pages[area])

    def test_an_area_with_a_hand_written_page_carries_the_line(self):
        name = "bga-viewer.md"
        assert (dev_close_task.DESIGN_AREA_PAGES / name).exists(), (
            "fixture missing: docs/design/areas/bga-viewer.md")
        text = self._body(name)
        assert (f"Mechanism: [docs/design/areas/{name}]"
                f"(../../design/areas/{name})") in text, text[:300]

    def test_an_area_with_no_hand_written_page_carries_nothing(self):
        name = "bga-attribution.md"
        assert not (dev_close_task.DESIGN_AREA_PAGES / name).exists(), (
            "fixture assumption broken: docs/design/areas/"
            "bga-attribution.md now exists")
        text = self._body(name)
        assert "Mechanism:" not in text, text[:300]

    def test_the_bga_area_gained_its_hand_written_page(self):
        """`UX-816`: `bga` was the first area with rows and no page."""
        name = "bga.md"
        assert (dev_close_task.DESIGN_AREA_PAGES / name).exists(), (
            "fixture missing: docs/design/areas/bga.md")
        text = self._body(name)
        assert (f"Mechanism: [docs/design/areas/{name}]"
                f"(../../design/areas/{name})") in text, text[:300]

