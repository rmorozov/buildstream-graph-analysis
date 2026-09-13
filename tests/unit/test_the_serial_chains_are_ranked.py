"""UX-830: the serial chains, ranked by weighted duration.

`longest_serial_chain` keeps one exhibit - the longest walk from a
*root*, in elements, stopping the instant it branches
(`_find_longest_serial_chain_from`). On every fixture measured here
that root branches immediately (`lib0.bst`, `toolchain.bst`), so the
"longest chain" published today is length 1 - `a_chain_beside_a_crowd`
and `shared_base_wide` alike, and the scale run too. `serial_chains[0]`
is the real chain a reader wants; the Acceptance Test's "equal to
today's longest chain" does not hold on any fixture here (it does on
`golden`, the task file's Outcome), so this file asserts what the task
falls back to instead: descending weighted duration, a bounded
`wall_share`, a `best_split` drawn from the chain, an interior member
that is 1-in-1-out, and the scale run's count and folded cell. A
diamond (`A,B -> C -> D -> E`) is planted rather than found: none of
the three fixtures here has the shape, though `macro_micro`'s
`lib-f.bst`/`app.bst` do (`test_one_table_many_views.py`), which is
where a chain sailing through a join instead of ending there first
showed.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

import networkx as nx

from bga.ingest.loader import load_all
from bga.structural.analyzer import ElementDependencyGraph, StructuralAnalyzer, build_edg
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

ACBC = os.path.join(REPO, "tests", "fixtures", "a_chain_beside_a_crowd", "run")
SBW = os.path.join(REPO, "tests", "fixtures", "shared_base_wide", "run")

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: `UX-836`'s own scoping: `querySelectorAll` on the table reaches into
#: the nested tables its folded cells hold, so rows are read off the
#: table's *own* `tbody`'s direct children, not the subtree.
SERIAL_CHAINS_JS = r"""
(() => {
  const table = document.querySelector('table[data-table="serial_chains"]');
  if (!table) return null;
  const body = [...table.children].find((c) => c.tagName === "TBODY");
  const rows = body
    ? [...body.children].filter((tr) => tr.tagName === "TR" && !tr.hidden)
    : [];
  return rows.map((tr) => {
    const td = [...tr.children].find(
      (c) => c.getAttribute("data-column") === "members");
    return {
      raw: td ? td.getAttribute("data-raw") : null,
      folded: !!(td && td.querySelector("details")),
    };
  });
})()
"""


def _analyze(run):
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", run,
         "--format", "json", "--diagnostics"],
        capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _graph_for(run):
    """The gating graph `serial_chains` was computed over - not
    published in the payload, so a walk is checked against the same
    graph the analyzer built it from."""
    _, graph, _ = load_all(pathlib.Path(run))
    return build_edg(graph).G


def _assert_ranked(chains, graph):
    prev = None
    for i, row in enumerate(chains, start=1):
        assert row["rank"] == i
        if prev is not None:
            assert row["weighted_duration_us"] <= prev, "not descending"
        prev = row["weighted_duration_us"]
        assert 0.0 <= row["wall_share"] <= 1.0
        assert row["length"] == len(row["members"])
        assert row["best_split"] in row["members"]
        members = row["members"]
        # `UX-830`: every hop is a real edge; every hop past the first
        # (the chosen branch out of a possibly-branching start) does
        # not itself branch - `_find_longest_serial_chain_from`'s own
        # rule, read off the graph rather than restated.
        for a, b in zip(members, members[1:]):
            assert b in list(graph.successors(a)), f"{a}->{b} is not an edge"
        for mid in members[1:-1]:
            assert graph.out_degree(mid) == 1, f"{mid} branches mid-chain"
            assert graph.in_degree(mid) == 1, f"{mid} is a join mid-chain"


class TestTheSerialChainsAreRanked:
    def test_a_chain_beside_a_crowd_has_the_real_chain_first(self):
        payload = _analyze(ACBC)
        bn = payload["bottleneck"]
        chains = bn["serial_chains"]
        assert len(chains) == 7
        _assert_ranked(chains, _graph_for(ACBC))
        # The chain the fixture is named for - `lib0` through `lib3` -
        # wins on duration and covers the whole path (`wall_share` 1.0).
        assert chains[0]["members"] == ["lib0.bst", "lib1.bst",
                                        "lib2.bst", "lib3.bst"]
        assert chains[0]["wall_share"] == 1.0
        # Today's `longest_serial_chain` is `['lib0.bst']` - length 1,
        # because `lib0.bst` is the only root and it branches on its
        # first step. It does not equal `chains[0]` and legitimately
        # cannot: the two measure different things on this graph.
        assert bn["longest_serial_chain"] == ["lib0.bst"]
        assert chains[0]["members"] != bn["longest_serial_chain"]

    def test_the_wide_base_topology_has_six_length_two_chains(self):
        payload = _analyze(SBW)
        bn = payload["bottleneck"]
        chains = bn["serial_chains"]
        assert len(chains) == 6
        assert all(row["length"] == 2 for row in chains)
        _assert_ranked(chains, _graph_for(SBW))
        # Same shape as above: the base is the only root and branches
        # at once, so `longest_serial_chain` is `['toolchain.bst']`.
        assert bn["longest_serial_chain"] == ["toolchain.bst"]

    @pytest.mark.medium
    def test_the_scale_run_has_at_least_five_chains(self, tmp_path):
        run = pages.scale_run(tmp_path)
        payload = _analyze(str(run))
        bn = payload["bottleneck"]
        chains = bn["serial_chains"]
        assert len(chains) >= 5
        assert len(chains) <= 40  # `SERIAL_CHAINS_MAX`
        _assert_ranked(chains, _graph_for(run))
        # Today's longest chain is degenerate on this graph too - the
        # same root-branches-immediately shape as the two fixtures
        # above, measured rather than assumed.
        assert bn["serial_chain_length"] == 1

    def test_a_diamond_ends_each_chain_at_the_join_not_through_it(self):
        """The round-verifier's case: `A,B -> C -> D -> E`. The old walk
        checked only the *current* node's out-degree, so it sailed
        through `C` (two parents) instead of stopping there - `[A,C]`
        became `[A,C,D,E]`. `C` is the tail of two chains and the head
        of a third; nothing but `C` may repeat, and only at an end."""
        G = nx.DiGraph()
        G.add_edges_from([("A", "C"), ("B", "C"), ("C", "D"), ("D", "E")])
        edg = ElementDependencyGraph(G=G)
        sa = StructuralAnalyzer(edg, tasks={},
                                element_durations=dict.fromkeys(G.nodes(), 1))
        chains = sa._find_serial_chains()
        members = sorted(tuple(c.members) for c in chains)
        assert members == [("A", "C"), ("B", "C"), ("C", "D", "E")]
        seen = {}
        for chain in chains:
            for m in chain.members:
                seen.setdefault(m, []).append(chain.members)
        shared = {m: cs for m, cs in seen.items() if len(cs) > 1}
        assert set(shared) == {"C"}
        for chain_list in shared.values():
            for members in chain_list:
                assert "C" in (members[0], members[-1]), (
                    f"C is interior to {members}")


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def scale_rows(tmp_path_factory, browser):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("serial-chains-scale")
    run = pages.scale_run(into)
    page = into / "scale.html"
    view.export(str(run), str(page))
    return browser.measure(page.as_uri(), SERIAL_CHAINS_JS)


class TestTheBottleneckSectionDrawsTheRankedTable:
    """The browser half: a ranked table with a folded `members` cell,
    not the whole chain spelled out in one row."""

    @needs_browser
    @pytest.mark.medium
    def test_the_table_has_five_rows_and_folds_its_members(self, scale_rows):
        assert scale_rows, "no serial_chains table on the scale export"
        assert len(scale_rows) >= 5
        for row in scale_rows:
            members = json.loads(row["raw"])
            # `ARRAY_INLINE_ITEMS` (6): past it a cell folds rather
            # than spelling every member out - the styleguide §3a.1
            # rule, and the mechanism `boundedList`/`mapTable` already
            # give any array cell, not a new one.
            if len(members) > 6:
                assert row["folded"], f"{len(members)} members, unfolded"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
