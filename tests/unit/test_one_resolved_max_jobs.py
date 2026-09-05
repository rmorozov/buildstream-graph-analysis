"""UX-377: one resolved `max-jobs`, from the capture that has it.

Native `max-jobs` is what reaches `make -jN`, the right-hand factor of
`UX-116`'s founding question and the input the whole
`UX-12`/`15`/`16`/`17`/`21` capacity chain keys off. BuildStream gives
it three routes and `bga` recovered it from one — the command line,
which `NATIVE_MAX_JOBS_RE` reads out of the wrapper's own
`Executing command:` line. Measured on one project, one host:

```text
route                              scheduler.native_max_jobs   graph per-element
default (nothing set)                              None                   4
$XDG_CONFIG_HOME/buildstream.conf: 2               None                   2
bst --max-jobs 2 build                                2                   4
```

Two defects, one per column. The run-level value was absent on the two
routes people use, while `graph.json` in the same snapshot held the
resolved value — and `bga analyze` said so: *"Capacity checks did not
run for this run - missing: native_max_jobs"*. And the one route that
did record it got the graph wrong, because `bga snapshot` re-derives the
graph with its own `bst show` that does not replay the build's options.
A cold capture under `bst --max-jobs 2 build` ran `make -j2` in five
sandboxes and its graph said 4.

After, the same three routes, with what the sandboxes actually ran:

```text
default              run=4  src=resolved_from_graph     graph=[4]  ran -j4
user config: 2       run=2  src=resolved_from_graph     graph=[2]  ran -j2
bst --max-jobs 2     run=2  src=parsed_from_invocation  graph=[2]  ran -j2
```

and the capacity chain runs on the default capture:
*"Capacity: builders 4 x max-jobs 2 on 4 core(s): memory binds at 1"*.
"""
import ast
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools._run_context_common import (
    NATIVE_MAX_JOBS_OPERATOR_DECLARED,
    NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION,
    NATIVE_MAX_JOBS_RESOLVED_FROM_GRAPH,
    add_cpu_capacity_fields,
    typical_resolved_max_jobs,
)


def _graph(*max_jobs):
    return {"elements": [{"uid": f"e{i}.bst", "max_jobs": value}
                         for i, value in enumerate(max_jobs)]}


class TestTheGraphKnowsWhatTheRunResolved:
    def test_the_typical_value_is_the_maximum(self):
        """The same rule `serialization_points.typical_max_jobs` uses,
        deliberately: they are the same quantity, and having the run
        level and the per-element comparison disagree would be the
        defect rather than a detail."""
        assert typical_resolved_max_jobs(_graph(4, 4, 4)) == 4

    def test_a_notparallel_element_does_not_lower_the_run(self):
        """An element pinned to one job is a *finding against* the run's
        parallelism, not evidence the run had none."""
        assert typical_resolved_max_jobs(_graph(4, 1, 4)) == 4

    def test_a_graph_with_no_resolved_value_says_nothing(self):
        assert typical_resolved_max_jobs(_graph(None, None)) is None
        assert typical_resolved_max_jobs({"elements": []}) is None
        assert typical_resolved_max_jobs({}) is None


class TestThreeSourcesAndTheOrderAmongThem:
    def test_the_operator_still_wins(self):
        context = {}
        add_cpu_capacity_fields(context, native_max_jobs=8,
                                parsed_native_max_jobs=4,
                                graph_native_max_jobs=2)
        assert context["native_max_jobs"] == 8
        assert context["native_max_jobs_source"] == (
            NATIVE_MAX_JOBS_OPERATOR_DECLARED)

    def test_the_invocation_beats_the_graph(self):
        """`UX-29`'s route keeps its precedence: a flag on the command
        line is what the build was *told*, and the graph is a
        re-resolution."""
        context = {}
        add_cpu_capacity_fields(context, parsed_native_max_jobs=4,
                                graph_native_max_jobs=2)
        assert context["native_max_jobs"] == 4
        assert context["native_max_jobs_source"] == (
            NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION)

    def test_the_graph_answers_when_nothing_else_does(self):
        """The default capture, and the user-config capture. Before
        this, both published nothing."""
        context = {}
        add_cpu_capacity_fields(context, graph_native_max_jobs=2)
        assert context["native_max_jobs"] == 2
        assert context["native_max_jobs_source"] == (
            NATIVE_MAX_JOBS_RESOLVED_FROM_GRAPH)

    def test_none_of_the_three_publishes_nothing(self):
        """`UX-12`'s rule, unchanged: absent rather than a guessed
        default, so a consumer can tell 'unmeasured' from 'one'."""
        context = {}
        add_cpu_capacity_fields(context)
        assert "native_max_jobs" not in context
        assert "native_max_jobs_source" not in context

    def test_the_three_sources_have_three_names(self):
        assert len({NATIVE_MAX_JOBS_OPERATOR_DECLARED,
                    NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION,
                    NATIVE_MAX_JOBS_RESOLVED_FROM_GRAPH}) == 3


class TestTheGraphIsExtractedWithTheBuildsOwnOptions:
    def test_run_bst_show_puts_the_options_before_the_subcommand(self):
        """`--max-jobs` is a *top-level* `bst` option, not a `bst show`
        one: `bst show --max-jobs 2` is `No such option`. Asserted on
        the argv this builds rather than on a real `bst`, because the
        placement is the whole content of the claim."""
        import tools.bst_show_to_graph as graph_tool
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            raise RuntimeError("stop here - the argv is what is asserted")

        original = graph_tool.subprocess.Popen
        graph_tool.subprocess.Popen = fake_run
        try:
            with pytest.raises(RuntimeError, match="stop"):
                graph_tool.run_bst_show("/nowhere", ["all.bst"],
                                        bst_options=["--max-jobs", "2"])
        finally:
            graph_tool.subprocess.Popen = original
        cmd = seen["cmd"]
        assert cmd[1:3] == ["--max-jobs", "2"], cmd
        assert cmd[3] == "show", (
            f"the option landed after the subcommand: {cmd[:5]}")

    def test_no_options_reproduces_the_old_argv(self):
        import tools.bst_show_to_graph as graph_tool
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            raise RuntimeError("stop")

        original = graph_tool.subprocess.Popen
        graph_tool.subprocess.Popen = fake_run
        try:
            with pytest.raises(RuntimeError, match="stop"):
                graph_tool.run_bst_show("/nowhere", ["all.bst"])
        finally:
            graph_tool.subprocess.Popen = original
        assert seen["cmd"][:2] == ["bst", "show"], seen["cmd"]

    def test_the_extraction_replays_what_the_invocation_carried(self):
        """Structural, on the parse tree: `extract_run` must build the
        replayed options from the *scheduler's* parsed value and hand
        them to `extract_graph`. A guard on source order would go green
        for any rearrangement."""
        tree = ast.parse((REPO / "tools/bst_extract_run.py").read_text(
            encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)
                 and n.func.id == "extract_graph"]
        assert calls, "extract_run no longer calls extract_graph"
        assert any(k.arg == "bst_options" for call in calls
                   for k in call.keywords), (
            "the graph is extracted without the build's own options, so its "
            "per-element max_jobs describes a fresh resolution rather than "
            "the build")

    def test_the_run_context_is_offered_the_graphs_value(self):
        tree = ast.parse((REPO / "tools/bst_extract_run.py").read_text(
            encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)
                 and n.func.id == "add_cpu_capacity_fields"]
        assert calls
        assert any(k.arg == "graph_native_max_jobs" for call in calls
                   for k in call.keywords), (
            "the run context is not offered the graph's resolved value, so a "
            "default capture publishes None and the capacity chain stays "
            "inert with the number in the next file")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
