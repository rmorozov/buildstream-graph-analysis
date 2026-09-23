"""UX-632: what `make test-touching` costs is derived, never committed.

Three places priced the loop at 4s on a one-module diff -
`bga/store_aggregate.py`, the narrowest name in the tree, on one
machine. `UX-606` had already replaced that sample in the guard with a
distribution over every module the map names, and the prose beside it
went on quoting the sample. `UX-996` went further: a committed figure
(seconds or a selection width) drifts every time the tree does, so
`tools/dev_touching.py --spread` prints it and the documents name the
command instead of a number.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_touching

#: The documents that price this loop - held to naming the command,
#: never a figure of their own (`UX-996`).
SITES = ("docs/contributing/fixing-guide.md", "CLAUDE.md")

#: A wall-clock claim: `4s`, `~4s`, `20 s`. `11-124` is not one, and
#: neither is `UX-551` - the lookbehind is what makes that true.
DURATION = re.compile(r"(?<![\w.-])~?\d+(?:\.\d+)?\s*s(?![\w])")

#: `UX-493`'s shape: a selection width committed as digits, the thing
#: `--spread` now prints instead.
STALE_SPREAD = re.compile(r"\d+-\d+ of \d+ test files")


def cost_lines(name):
    """The lines of `name` that price this loop: those naming the target.

    The subject, not the argument. A guard that grepped the whole
    document would be answered by the paragraph explaining why the
    figure is there.
    """
    text = (REPO / name).read_text(encoding="utf-8")
    return [line for line in text.splitlines() if "make test-touching" in line]


class TestTheGuideNamesTheCommandNotAFigure:

    def test_the_sites_are_real_and_price_the_loop(self):
        """The vacuity floor. Every clause below reads `cost_lines`, and
        an empty one passes all of them."""
        assert SITES, "no document is held to anything"
        for name in SITES:
            assert (REPO / name).exists(), name
            assert cost_lines(name), f"{name} does not name `make test-touching`"

    @pytest.mark.parametrize("name", sorted(SITES))
    def test_no_cost_line_commits_a_selection_width(self, name):
        """The defect `UX-996` removed: a figure that drifts every time
        the tree does, sitting in a document nothing rewrites."""
        stale = [line for line in cost_lines(name) if STALE_SPREAD.search(line)]
        assert stale == [], (
            f"{name} commits a selection width instead of naming "
            f"`dev_touching.py --spread`: {stale}")

    @pytest.mark.parametrize("name", sorted(SITES))
    def test_no_cost_line_prices_the_loop_in_seconds(self, name):
        """The defect this item was filed for: a duration read as the
        cost. It is one machine's, and no local instrument can check
        it."""
        timed = [line for line in cost_lines(name) if DURATION.search(line)]
        assert timed == [], (
            f"{name} prices `make test-touching` in seconds: {timed}")

    @pytest.mark.parametrize("name", sorted(SITES))
    def test_the_cost_line_names_the_command(self, name):
        named = [line for line in cost_lines(name) if "--spread" in line
                 or "guide" in line]
        assert named, (
            f"{name} prices the loop with neither the command nor a "
            f"pointer to the document that names it")


class TestTheFigureIsMeasured:

    def test_the_spread_reads_the_mapped_population(self):
        """`UX-606`'s population, and the floor under it: a spread over
        an empty map would satisfy every clause above."""
        got = dev_touching.spread()
        assert got["modules"] >= 60, got
        assert got["files"] >= 200, got
        assert got["min"] <= got["max"], got
        assert "median" not in got, got  # UX-770

    def test_the_figure_interpolates_and_is_not_a_constant(self):
        """A string returned whatever the tree says would be a typed
        figure with an extra step in front of it."""
        made = dev_touching.figure(
            {"min": 1, "max": 2, "files": 4, "modules": 5})
        assert made == "1-2 of 4 test files", made
        assert made != dev_touching.figure()

    def test_the_option_prints_what_the_clauses_read(self, capsys):
        """The tool and the guard are one figure, or the tool is a
        second copy of it. `--spread` never writes (`UX-996`)."""
        before = (REPO / "docs/contributing/fixing-guide.md").read_bytes()
        assert dev_touching.main(["--spread"]) == 0
        assert capsys.readouterr().out.strip() == dev_touching.figure()
        assert (REPO / "docs/contributing/fixing-guide.md").read_bytes() == before, (
            "`--spread` wrote to the guide")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
