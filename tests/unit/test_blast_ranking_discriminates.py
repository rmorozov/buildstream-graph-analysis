"""UX-179: the discriminating case UX-173's acceptance named and nobody built.

UX-173 promised: *"a synthetic graph where a stack-heavy blast
outnumbers a cmake-heavy one ranks below it by cost while the raw count
says otherwise - asserted. Mutation: treating stacks as building kinds
reddens the discriminating case."*

Round 19 proved it did not exist, by reverting the cost sorter to
count-only order and running the class: **3 passed**. On the golden
fixture the two orders are identical, and the closing assertion
(`len(set(weights)) > 1 or len(set(counts)) > 1`) never compared them.

So this file builds the fixture. The graph is chosen so the two orders
*disagree*: a cheap element with many descendants against an expensive
one with few.
"""
import os
import shutil
import subprocess

import pytest

from bga.diagnostics.analyzer import DiagnosticsAnalyzer
from bga.ingest.models import (
    DependencyEdge,
    Element,
    Graph,
    NormalizedTask,
    TaskKey,
    TaskKind,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _task(uid, dur_us):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="build"),
        ready_us=0, start_us=0, finish_us=dur_us,
        resources={"PROCESS": 1}, primary_resource="PROCESS",
    )


def _discriminating():
    """`wide.bst` touches more elements; `deep.bst` touches costlier ones.

    ```text
    wide.bst  -> s1..s4   (four stacks, 1s each)      count 4, cost  4s
    deep.bst  -> c1, c2   (two cmakes, 60s each)      count 2, cost 120s
    ```

    By count `wide` ranks first; by measured rebuild time `deep` does.
    That disagreement is the whole point of the fixture - without it a
    guard cannot tell the two orders apart.
    """
    elements = (
        [Element(uid="wide.bst", element_kind="manual"),
         Element(uid="deep.bst", element_kind="manual")]
        + [Element(uid=f"s{i}.bst", element_kind="stack") for i in range(1, 5)]
        + [Element(uid=f"c{i}.bst", element_kind="cmake") for i in range(1, 3)]
    )
    deps = (
        [DependencyEdge(predecessor="wide.bst", successor=f"s{i}.bst",
                        dependency_type="build") for i in range(1, 5)]
        + [DependencyEdge(predecessor="deep.bst", successor=f"c{i}.bst",
                          dependency_type="build") for i in range(1, 3)]
    )
    tasks = (
        [_task("wide.bst", 1_000_000), _task("deep.bst", 1_000_000)]
        + [_task(f"s{i}.bst", 1_000_000) for i in range(1, 5)]
        + [_task(f"c{i}.bst", 60_000_000) for i in range(1, 3)]
    )
    return Graph(elements=elements, dependencies=deps), tasks


def _ranked(graph, tasks):
    """Through the real pipeline: `analyze_graph`, then the sorter."""
    from bga.graph.edg import analyze_graph

    analysis = analyze_graph(graph, tasks)
    analyzer = DiagnosticsAnalyzer(normalized_tasks=tasks, graph_analysis=analysis)
    results = analyzer.compute_blast_radius()
    return [(r.element_uid, r.downstream_count, r.downstream_weighted_duration_us)
            for r in results]


class TestTheTwoOrdersDisagreeAndCostWins:
    def test_the_fixture_really_discriminates(self):
        """Guard the guard: if these agreed, the test below proves nothing."""
        graph, tasks = _discriminating()
        ranked = _ranked(graph, tasks)
        by_count = [uid for uid, _c, _w in
                    sorted(ranked, key=lambda r: r[1], reverse=True)]
        by_cost = [uid for uid, _c, _w in
                   sorted(ranked, key=lambda r: r[2], reverse=True)]
        assert by_count[0] == "wide.bst", by_count
        assert by_cost[0] == "deep.bst", by_cost
        assert by_count != by_cost

    def test_the_published_order_is_the_cost_order(self):
        graph, tasks = _discriminating()
        ranked = _ranked(graph, tasks)
        assert ranked[0][0] == "deep.bst", (
            f"the ranking put the wider blast first, not the costlier one: "
            f"{[r[0] for r in ranked]}"
        )
        # And `wide.bst`, which the count ranks first, is behind it.
        order = [uid for uid, _c, _w in ranked]
        assert order.index("deep.bst") < order.index("wide.bst")

    def test_the_original_mutation_reddens_here(self):
        """UX-173's own words: "treating stacks as building kinds reddens
        the discriminating case".

        The kind split is what makes `wide.bst`'s four descendants
        cheap-and-structural rather than real work, so a caller reading
        the split gets a different answer than one reading the count.
        """
        from bga import sources

        graph, _tasks = _discriminating()
        kinds = {e.uid: e.element_kind for e in graph.elements}
        wide_blast = [f"s{i}.bst" for i in range(1, 5)] + ["wide.bst"]
        deep_blast = [f"c{i}.bst" for i in range(1, 3)] + ["deep.bst"]

        assert sources.split_by_kind(wide_blast, kinds) == (1, 4)
        assert sources.split_by_kind(deep_blast, kinds) == (3, 0)
        # If stacks counted as building, the two would be indistinguishable
        # on the axis the split exists to separate.
        assert sources.split_by_kind(wide_blast, kinds)[0] != len(wide_blast)

    def test_an_unmeasured_run_falls_back_to_the_count_and_says_so(self):
        graph, _tasks = _discriminating()
        ranked = [(uid, count) for uid, count, _w in _ranked(graph, [])]
        assert ranked[0][0] == "wide.bst", (
            "with no durations the count is the only order there is"
        )


BST_AVAILABLE = shutil.which("bst") is not None
FIXTURE_PROJECT = os.path.join(REPO_ROOT, "tests", "fixtures", "bst_show_project")


class TestTheMemoDropIsWired:
    @pytest.mark.bst
    @pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH")
    def test_a_real_extraction_into_a_snapshot_drops_the_memo(self, tmp_path):
        """UX-179: through `extract_run`, not by calling the helper.

        The UX-177 guard called `_drop_size_memo` directly, so deleting
        its call site reddened nothing. It also has to be a *successful*
        extraction: a failed one never reaches the write, and rightly
        leaves the memo alone, so a failing fixture would prove the
        opposite of what it looks like.
        """
        from bga import run_store
        from tests.unit._bst_env import isolated_bst_env
        from tools.bst_extract_run import extract_run

        snapshot = tmp_path / "20260820T120000Z"
        run = snapshot / "run"
        run.mkdir(parents=True)
        (run / "filler.json").write_text("x" * 100)
        run_store.snapshot_size_bytes(str(snapshot))
        memo = snapshot / run_store.SIZE_CACHE_NAME
        assert memo.exists(), "the memo was never written - nothing to drop"

        log = tmp_path / "build.log"
        proc = subprocess.run(
            ["bst", "-C", FIXTURE_PROJECT, "--no-colors", "build", "app.bst"],
            capture_output=True, text=True, env=isolated_bst_env(tmp_path),
        )
        log.write_text(proc.stdout + proc.stderr)
        extract_run(FIXTURE_PROJECT, str(log), str(run), log_format="auto")

        assert (run / "graph.json").exists(), "the extraction did not succeed"
        assert not memo.exists(), (
            "the extraction rewrote the run and left the size memo standing"
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
