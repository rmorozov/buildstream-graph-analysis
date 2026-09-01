"""UX-481: an artifact arrives by being built or by being pulled.

`UX-60` closed one hole in the replay's readiness model - a BUILD that
did not wait for its own element's FETCH - and the same hole was open
one edge over. `clamp_task_starts` built each BUILD's edges from
`build_task_by_element`, a map keyed on `TaskKind.BUILD`; a dependency
that came off the remote cache produces a `PULL` and **no** `BUILD`, so
the lookup missed, the edge vanished, and the replay was free to start
the dependent at `t=0`.

That is not an odd fixture. It is the shape of every cache-hit build,
which is the common case in CI and the one `run-mode-incremental`
exists to name. On `tests/fixtures/a_build_that_pulls` - three
elements pulled at 1.0s each and one built for 9.0s on top of them -
it scored the replay against a schedule that could not have happened:

```text
a schedule that respects the pulls   3.0 + 9.0 = 12.0s
the replay's makespan  T_C                       9.0s
WARNING bga.validation.invariants: Model score reduced: T_C (9000000) < LB (12000000)
```

The two questions this file holds are the same one asked twice: *when*
was an upstream element's artifact ready (`_element_build_finish`, for
ready times) and *which task* should a dependent wait on
(`clamp_task_starts`, for replay). They were two maps built from one
`if` each, which is why they were wrong together.
"""
import contextlib
import io
import json
import pathlib

from bga.ingest.models import (DependencyEdge, Element, Graph, TaskKey,
                               TaskKind, TaskSpan)
from bga.normalize.timestamps import _element_build_finish, clamp_task_starts

REPO = pathlib.Path(__file__).resolve().parents[2]
PULLS = REPO / "tests/fixtures/a_build_that_pulls/run"


def _graph(*edges):
    names = sorted({name for edge in edges for name in edge})
    return Graph(
        elements=[Element(uid=name) for name in names],
        dependencies=[DependencyEdge(predecessor=pred, successor=succ)
                      for pred, succ in edges],
    )


def _span(element, kind, start, finish):
    return (TaskSpan(
        task_key=TaskKey(element_uid=element, task_kind=kind, phase=kind.value),
        ts_us=start, dur_us=finish - start, resources=[],
        primary_resource=None), start, finish)


def _deps_of(tasks, element, kind=TaskKind.BUILD):
    task = next(t for t in tasks
                if t.task_key.element_uid == element
                and t.task_key.task_kind == kind)
    return [str(dep) for dep in task.dependencies]


class TestTheReplayWaitsForAPulledDependency:

    def test_a_build_waits_on_its_dependency_s_pull(self):
        """The edge that was missing. `dep.bst` never builds - it came
        off the cache - so a map keyed on BUILD alone offered nothing to
        wait for."""
        spans = [_span("dep.bst", TaskKind.PULL, 0, 1_000_000),
                 _span("app.bst", TaskKind.BUILD, 0, 9_000_000)]
        tasks, _violations = clamp_task_starts(
            spans, {}, _graph(("dep.bst", "app.bst")))

        assert "dep.bst|PULL|PULL|0" in _deps_of(tasks, "app.bst")

    def test_a_pulled_element_is_ready_when_its_pull_finishes(self):
        """The other half, and the one the *floor* reads. Ready times
        take their predecessor finishes from `_element_build_finish`,
        which had no entry for an element that only pulled."""
        spans = [_span("dep.bst", TaskKind.PULL, 0, 1_000_000)]

        assert _element_build_finish(spans) == {"dep.bst": 1_000_000}

    def test_a_build_still_wins_where_an_element_did_both(self):
        """The precedence, decided rather than left to iteration order:
        a pull followed by a build did not produce the artifact the
        dependent consumed, so the BUILD is the edge."""
        spans = [_span("dep.bst", TaskKind.PULL, 0, 1_000_000),
                 _span("dep.bst", TaskKind.BUILD, 1_000_000, 5_000_000),
                 _span("app.bst", TaskKind.BUILD, 0, 9_000_000)]
        tasks, _violations = clamp_task_starts(
            spans, {}, _graph(("dep.bst", "app.bst")))

        deps = _deps_of(tasks, "app.bst")
        assert "dep.bst|BUILD|BUILD|0" in deps, deps
        assert not any(dep.startswith("dep.bst|PULL") for dep in deps), deps
        assert _element_build_finish(spans)["dep.bst"] == 5_000_000

    def test_a_trailing_push_still_gates_nothing(self):
        """`P1-27`'s rule, which this change must not undo: a PUSH
        finishes *after* the artifact exists, so gating a dependent on
        it over-constrains ready times. Widening the map to "the task
        that produced the artifact" is a different claim from widening
        it to "any task", and this is the clause that keeps them
        apart."""
        spans = [_span("dep.bst", TaskKind.BUILD, 0, 4_000_000),
                 _span("dep.bst", TaskKind.PUSH, 4_000_000, 9_000_000),
                 _span("app.bst", TaskKind.BUILD, 0, 2_000_000)]
        tasks, _violations = clamp_task_starts(
            spans, {}, _graph(("dep.bst", "app.bst")))

        assert _element_build_finish(spans)["dep.bst"] == 4_000_000
        assert _deps_of(tasks, "app.bst") == ["dep.bst|BUILD|BUILD|0"]

    def test_a_push_on_its_own_is_still_not_an_artifact_arriving(self):
        """The half of `P1-27` the clause above cannot see, and a
        mutation found it: adding `PUSH` to the artifact kinds leaves
        the case above green, because BUILD outranks it and the element
        has one.

        This is the shape where the two claims come apart - an element
        already in the local cache, neither built nor pulled this run,
        pushed to the remote. Reading its PUSH as "the artifact arrived
        at 9.0s" would hold a dependent five seconds past the moment it
        could really have started.
        """
        spans = [_span("dep.bst", TaskKind.PUSH, 4_000_000, 9_000_000),
                 _span("app.bst", TaskKind.BUILD, 0, 2_000_000)]
        tasks, _violations = clamp_task_starts(
            spans, {}, _graph(("dep.bst", "app.bst")))

        assert "dep.bst" not in _element_build_finish(spans)
        assert _deps_of(tasks, "app.bst") == []

    def test_an_element_that_neither_built_nor_pulled_offers_no_edge(self):
        """The absence stays an absence. `clamp_task_starts`'s own
        comment - "an upstream element with no BUILD task contributes no
        edge, rather than a wrong one" - is the rule, and only the set
        of kinds that count has moved."""
        spans = [_span("dep.bst", TaskKind.TRACK, 0, 1_000_000),
                 _span("app.bst", TaskKind.BUILD, 0, 9_000_000)]
        tasks, _violations = clamp_task_starts(
            spans, {}, _graph(("dep.bst", "app.bst")))

        assert "dep.bst" not in _element_build_finish(spans)
        assert _deps_of(tasks, "app.bst") == []


class TestTheCommittedFixtureScoresItsOwnSchedule:
    """`UX-459` committed the capture; this is what it was for."""

    @staticmethod
    def _analyze():
        from bga.cli import main

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            main(["analyze", str(PULLS), "--format", "json", "--diagnostics"])
        return json.loads(out.getvalue()), err.getvalue()

    def test_it_reports_no_reduced_model_score(self):
        """The row's Acceptance Test, as a clause. It reddens on the
        code as it stood: `Model score reduced: T_C (9000000) < LB
        (12000000)`."""
        _payload, stderr = self._analyze()

        assert "Model score reduced" not in stderr, stderr

    def test_the_replay_finishes_no_sooner_than_the_floor(self):
        """The arithmetic behind the warning, asserted rather than left
        to the log. Three 1.0s pulls run serially, then a 9.0s build:
        no schedule finishes before 12.0s, and the replay now agrees."""
        payload, _stderr = self._analyze()
        floors = payload["floors"]

        assert floors["t_c"] >= floors["lb"], floors
        assert floors["lb"] == 12_000_000, floors
        assert floors["t_c"] == 12_000_000, floors

    def test_the_model_score_is_whole(self):
        """What the warning was reducing. A reader of a cache-hit build
        was being handed a confidence number marked down by the
        analyser disagreeing with itself."""
        payload, _stderr = self._analyze()

        assert payload["confidence"]["model_score"] == 1.0, payload["confidence"]
