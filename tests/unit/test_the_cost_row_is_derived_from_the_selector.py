"""UX-632: what the documents say `make test-touching` costs is derived.

Three places priced the loop at 4s on a one-module diff -
`bga/store_aggregate.py`, the narrowest name in the tree, on one
machine. `UX-606` had already replaced that sample in the guard with a
distribution over every module the map names, and the prose beside it
went on quoting the sample.

Seconds cannot be guarded here at all: they are a property of the
machine (`UX-551`), so a figure in seconds fails on a slower laptop for
no defect. What can be is the **selection** - how many of the suite's
test files a one-module diff runs - which is a property of the tree and
is what the guard already computes.

So `tools/dev_touching.py` computes it, `--spread --write` puts it in
the documents, and these clauses hold the documents to it. A derived
figure no tool writes is a typed one that drifts more slowly.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_touching  # noqa: E402

#: Per document, how many lines pricing the loop must carry the figure.
#: An equality, not a floor: a site that drops it is the defect, and
#: `test_the_document_is_what_the_tool_would_write` cannot see that -
#: a document with no figure at all is one the rewriter leaves alone.
SITES = {"docs/contributing/fixing-guide.md": 2}

#: `UX-471`'s guard forbids `CLAUDE.md` a count the tree changes under
#: it, and 462 test files is one. So that row prices the loop in
#: nothing and points at the guide, which is what its `make test` row
#: already does - held here so the seconds cannot come back instead.
DEFERS = ("CLAUDE.md",)

#: A wall-clock claim: `4s`, `~4s`, `20 s`. `11-124` is not one, and
#: neither is `UX-551` - the lookbehind is what makes that true.
DURATION = re.compile(r"(?<![\w.-])~?\d+(?:\.\d+)?\s*s(?![\w])")


def cost_lines(name):
    """The lines of `name` that price this loop: those naming the target.

    The subject, not the argument. A guard that grepped the whole
    document would be answered by the paragraph explaining why the
    figure is there.
    """
    text = (REPO / name).read_text(encoding="utf-8")
    return [line for line in text.splitlines() if "make test-touching" in line]


class TestTheDocumentsCarryTheComputedFigure:

    def test_the_sites_are_real_and_price_the_loop(self):
        """The vacuity floor. Every clause below reads `cost_lines`, and
        an empty one passes all of them."""
        assert SITES and DEFERS, "no document is held to anything"
        for name in (*SITES, *DEFERS):
            assert (REPO / name).exists(), name
            assert cost_lines(name), f"{name} does not name `make test-touching`"

    def test_the_tool_writes_exactly_the_documents_declared_here(self):
        """A site the tool rewrites and no clause counts would be
        maintained and unheld."""
        assert set(SITES) == set(dev_touching.COST_SITES), (
            f"declared {sorted(SITES)}, the tool writes "
            f"{sorted(dev_touching.COST_SITES)}")
        assert not set(DEFERS) & set(dev_touching.COST_SITES), (
            "a document cannot both defer the figure and be written it")

    @pytest.mark.parametrize("name", sorted(DEFERS))
    def test_a_deferring_document_states_no_figure_of_its_own(self, name):
        """`UX-471`: a second copy that decays. The row says where the
        figure is instead of holding one."""
        text = (REPO / name).read_text(encoding="utf-8")
        assert not dev_touching.FIGURE_RE.search(text), (
            f"{name} carries its own copy of the figure")
        assert any("guide" in line for line in cost_lines(name)), (
            f"{name} prices the loop with neither a figure nor a pointer")

    @pytest.mark.parametrize("name", sorted(SITES))
    def test_each_cost_line_carries_the_figure(self, name):
        row = dev_touching.figure()
        carrying = [line for line in cost_lines(name) if row in line]
        assert len(carrying) == SITES[name], (
            f"{name}: {len(carrying)} line(s) price the loop at {row!r}, "
            f"expected {SITES[name]}. "
            f"Run `python3 tools/dev_touching.py --spread --write`.")

    @pytest.mark.parametrize("name", sorted((*SITES, *DEFERS)))
    def test_no_cost_line_prices_the_loop_in_seconds(self, name):
        """The defect this item was filed for: a duration read as the
        cost. It is one machine's, and no local instrument can check
        it."""
        timed = [line for line in cost_lines(name)
                 if DURATION.search(line)]
        assert timed == [], (
            f"{name} prices `make test-touching` in seconds: {timed}")

    @pytest.mark.parametrize("name", sorted(SITES))
    def test_the_document_is_what_the_tool_would_write(self, name):
        """The drift direction: a figure that was current and is not.
        The rewriter is the same one `--write` runs, so a red here is
        fixed by running it rather than by typing a number."""
        text = (REPO / name).read_text(encoding="utf-8")
        assert dev_touching.write_figure(text, dev_touching.figure()) == text, (
            f"{name} carries a stale figure. "
            f"Run `python3 tools/dev_touching.py --spread --write`.")


class TestTheFigureIsMeasured:

    def test_the_spread_reads_the_mapped_population(self):
        """`UX-606`'s population, and the floor under it: a spread over
        an empty map would satisfy every clause above."""
        got = dev_touching.spread()
        assert got["modules"] >= 60, got
        assert got["files"] >= 200, got
        assert got["min"] <= got["median"] <= got["max"], got

    def test_the_figure_interpolates_and_is_not_a_constant(self):
        """A string returned whatever the tree says would be a typed
        figure with an extra step in front of it."""
        made = dev_touching.figure(
            {"min": 1, "max": 2, "median": 3, "files": 4, "modules": 5})
        assert made == "1-2 of 4 test files, median 3", made
        assert made != dev_touching.figure()

    def test_the_rewriter_replaces_a_stale_figure_and_nothing_else(self):
        """What `--write` does, on text this test owns."""
        stale = "cost: 9-9 of 9 test files, median 9 - and 4s elsewhere\n"
        fixed = dev_touching.write_figure(stale, "1-2 of 3 test files, median 4")
        assert fixed == "cost: 1-2 of 3 test files, median 4 - and 4s elsewhere\n"

    def test_the_option_prints_what_the_clauses_read(self, capsys):
        """The tool and the guard are one figure, or the tool is a
        second copy of it."""
        assert dev_touching.main(["--spread"]) == 0
        assert capsys.readouterr().out.strip() == dev_touching.figure()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
