"""UX-115: the CI comment, rendered.

The design doc's sketch has been quoted in five task files and produced
by nothing. These cover the properties that make it worth posting rather
than the exact prose: that it names elements instead of counting them,
that a gate nobody asked for cannot be mistaken for a gate that passed,
that a missing Plane 2 capture reads as missing rather than as clean, and
that the numbers in it are the same ones the exit code was computed from.

The last of those is the one that would rot silently: a renderer that
re-derived a threshold would drift from `_compare_exit_code` and the
comment would explain a verdict the pipeline did not reach.
"""
import argparse
import json
import subprocess
import sys

from bga.report.ci_comment import MARKER, render_ci_comment

EXIT_OK = 0
EXIT_REGRESSION = 4
EXIT_EFFICIENCY_REGRESSION = 5

D = 4_000_000
B = 4


def _args(**overrides):
    base = dict(
        fail_on_regression=False, fail_on_efficiency_regression=False,
        min_efficiency=None, fail_on_inefficient_additions=False,
        max_addition_stretch=None, regression_threshold=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def _write_run(tmp_path, name, elements, deps, spans, builders=B):
    run_dir = tmp_path / name
    run_dir.mkdir()
    identity = {"manifest_hash": "ci-comment-fixture", "targets": list(elements)}
    end = max(start + dur for _, start, dur in spans)
    (run_dir / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": 1000,
        "resource_capacities": {"PROCESS": builders},
        "run_identity": identity,
        "wall_clock": {"start_us": 0, "end_us": end},
    }))
    (run_dir / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid, "requested_target": True} for uid in elements],
        "dependencies": [
            {"predecessor": a, "successor": b, "dependency_type": "build"}
            for a, b in deps
        ],
        "run_identity_hash": identity["manifest_hash"],
    }))
    (run_dir / "trace.json").write_text(json.dumps({
        "run_identity_hash": identity["manifest_hash"],
        "spans": [
            {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": start, "dur_us": dur,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"}
            for uid, start, dur in spans
        ],
        "phases": [],
    }))
    return run_dir


def _base(tmp_path, name="base"):
    """Four leaves off one root, packed onto four builders."""
    elements = ["root.bst"] + [f"e{i}.bst" for i in range(4)]
    deps = [("root.bst", f"e{i}.bst") for i in range(4)]
    spans = [("root.bst", 0, D)] + [(f"e{i}.bst", D, D) for i in range(4)]
    return _write_run(tmp_path, name, elements, deps, spans)


def _grown(tmp_path, name, serialized):
    """The same graph plus `lib-g.bst`/`lib-h.bst`, added well or badly."""
    elements = ["root.bst"] + [f"e{i}.bst" for i in range(4)] + ["lib-g.bst", "lib-h.bst"]
    deps = [("root.bst", f"e{i}.bst") for i in range(4)]
    spans = [("root.bst", 0, D)] + [(f"e{i}.bst", D, D) for i in range(4)]
    if serialized:
        deps += [("e3.bst", "lib-g.bst"), ("lib-g.bst", "lib-h.bst")]
        spans += [("lib-g.bst", 2 * D, D), ("lib-h.bst", 3 * D, D)]
    else:
        deps += [("root.bst", "lib-g.bst"), ("root.bst", "lib-h.bst")]
        spans += [("lib-g.bst", D, D), ("lib-h.bst", D, D)]
    return _write_run(tmp_path, name, elements, deps, spans, builders=8)


def _compare(baseline, candidate):
    from pathlib import Path

    from bga.compare import compare_runs
    return compare_runs(Path(baseline), Path(candidate))


class TestNamingRatherThanCounting:
    def test_a_serialized_addition_is_named_with_its_duration(self, tmp_path):
        """`Bottlenecks Identified: 2` is worse than useless - nobody runs
        the JSON query by hand. The whole point is the element name."""
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))

        comment = render_ci_comment(comparison, _args())

        assert "`lib-g.bst`" in comment
        assert "`lib-h.bst`" in comment
        assert "4.0s" in comment

    def test_a_serialized_addition_is_marked_as_on_the_path(self, tmp_path):
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))

        comment = render_ci_comment(comparison, _args())

        assert "yes — new on the path" in comment

    def test_a_well_added_element_is_reported_as_absorbed(self, tmp_path):
        """The good case has to be legible too, or a reviewer learns to
        skip the table."""
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "good", serialized=False))

        comment = render_ci_comment(comparison, _args())

        assert "absorbed by existing parallelism" in comment
        assert "yes — new on the path" not in comment

    def test_a_change_that_adds_nothing_says_so(self, tmp_path):
        comparison = _compare(_base(tmp_path), _base(tmp_path, "same"))

        comment = render_ci_comment(comparison, _args())

        assert "added none and moved none onto the critical path" in comment


class TestGatesCannotLookLikePasses:
    def test_a_gate_that_was_not_requested_says_so(self, tmp_path):
        """A comment showing only the gates that ran would read as a clean
        bill of health from a pipeline that checked nothing - the failure
        UX-87 recorded against the efficiency gate itself."""
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))

        comment = render_ci_comment(comparison, _args())

        assert comment.count("not requested") == 3

    def test_a_failing_marginal_gate_states_the_stretch_and_the_limit(self, tmp_path):
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))

        comment = render_ci_comment(
            comparison, _args(fail_on_inefficient_additions=True))

        assert "| Marginal efficiency | FAIL |" in comment
        assert "stretch 1.00 > 0.50" in comment

    def test_a_passing_marginal_gate_states_the_same_numbers(self, tmp_path):
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "good", serialized=False))

        comment = render_ci_comment(
            comparison, _args(fail_on_inefficient_additions=True))

        assert "| Marginal efficiency | pass |" in comment
        assert "stretch 0.00" in comment

    def test_a_gate_with_nothing_to_judge_is_not_a_pass(self, tmp_path):
        """`marginal_efficiency` is None when the change added no measured
        work. Rendering that as `pass` would be the same lie in markdown
        that `UX-87` found in an exit code."""
        comparison = _compare(_base(tmp_path), _base(tmp_path, "same"))

        comment = render_ci_comment(
            comparison, _args(fail_on_inefficient_additions=True))

        assert "| Marginal efficiency | not applied |" in comment
        assert "an empty check, not a pass" in comment


class TestTheCommentAgreesWithTheExitCode:
    """The property that would rot silently: the renderer calls the same
    predicates `_compare_exit_code` does, so a threshold cannot drift
    between the verdict a pipeline acted on and the one it explained."""

    def _run(self, baseline, candidate, *flags):
        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "compare", str(baseline), str(candidate),
             "--format", "ci-comment", *flags],
            capture_output=True, text=True,
        )

    def test_a_failing_marginal_gate_exits_5_and_the_comment_says_fail(self, tmp_path):
        result = self._run(
            _base(tmp_path), _grown(tmp_path, "bad", serialized=True),
            "--fail-on-inefficient-additions",
        )

        assert result.returncode == EXIT_EFFICIENCY_REGRESSION
        assert "| Marginal efficiency | FAIL |" in result.stdout

    def test_a_passing_marginal_gate_exits_0_and_the_comment_says_pass(self, tmp_path):
        result = self._run(
            _base(tmp_path), _grown(tmp_path, "good", serialized=False),
            "--fail-on-inefficient-additions",
        )

        assert result.returncode == EXIT_OK
        assert "| Marginal efficiency | pass |" in result.stdout

    def test_the_comment_is_printed_even_when_the_gate_fails(self, tmp_path):
        """A failing pipeline must still show why - the same rule the text
        report already follows."""
        result = self._run(
            _base(tmp_path), _grown(tmp_path, "bad", serialized=True),
            "--fail-on-inefficient-additions",
        )

        assert result.stdout.startswith(MARKER)


class TestWhatWasNotMeasured:
    def test_without_plane_2_the_never_read_column_is_absent_and_named(self, tmp_path):
        """"Nothing was staged and never read" and "nobody looked" are
        different claims. An empty column would assert the first."""
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))

        comment = render_ci_comment(comparison, _args())

        assert "Declared, never read" not in comment
        assert "absent — not empty" in comment

    def test_with_plane_2_the_column_names_the_unread_dependency(self, tmp_path):
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))
        native = {"declared_vs_used": {"available": True, "unused_candidates": [
            {"element": "lib-h.bst", "dependency": "lib-g.bst",
             "staged_files": 12, "opened_files": 0, "evidence": "..."},
        ]}}

        comment = render_ci_comment(comparison, _args(), native_report=native)

        assert "Declared, never read" in comment
        assert "| `lib-h.bst` | 4.0s | yes — new on the path | `lib-g.bst` |" in comment
        assert "absent — not empty" not in comment

    def test_a_plane_2_report_that_could_not_run_the_analysis_is_not_data(self, tmp_path):
        """`available: false` is what a capture with no `--project-dir`
        produces. Reading it as "no unused dependencies" would invent a
        finding out of a missing input."""
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))
        native = {"declared_vs_used": {"available": False, "note": "..."}}

        comment = render_ci_comment(comparison, _args(), native_report=native)

        assert "absent — not empty" in comment


# UX-229 added a folded "why" block, and the budget above measures the
# wrong thing against it. The budget exists because *a comment that
# needs scrolling gets collapsed* - and a `<details>` is one line until
# a reviewer chooses otherwise, which is the opposite of scroll. So the
# count is of what the sidebar shows: everything outside a fold, plus
# one line for the fold itself.
def _visible_lines(comment: str) -> int:
    shown, folded = 0, False
    for line in comment.splitlines():
        if line.startswith("<details"):
            folded, shown = True, shown + 1
            continue
        if line.startswith("</details>"):
            folded = False
            continue
        if not folded:
            shown += 1
    return shown


class TestThePropertiesAPipelineDependsOn:
    def test_the_marker_leads_the_comment(self, tmp_path):
        """A job greps for it to decide between editing its comment and
        posting a new one; if it moves, every posted comment is orphaned
        and the pipeline starts appending."""
        comparison = _compare(_base(tmp_path), _base(tmp_path, "same"))

        assert render_ci_comment(comparison, _args()).startswith(MARKER + "\n")

    def test_the_rendering_is_deterministic(self, tmp_path):
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))

        first = render_ci_comment(comparison, _args())
        second = render_ci_comment(comparison, _args())

        assert first == second

    def test_a_clean_change_stays_short_enough_to_read(self, tmp_path):
        """The sketch is ~6 lines and the budget is 40. A comment that
        needs scrolling is a comment that gets collapsed."""
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "good", serialized=False))

        assert _visible_lines(render_ci_comment(comparison, _args())) <= 40

    def test_a_large_addition_collapses_rather_than_scrolls(self, tmp_path):
        elements = ["root.bst"] + [f"n{i}.bst" for i in range(30)]
        deps = [("root.bst", f"n{i}.bst") for i in range(30)]
        spans = [("root.bst", 0, D)] + [(f"n{i}.bst", D, D) for i in range(30)]
        candidate = _write_run(tmp_path, "many", elements, deps, spans, builders=32)
        comparison = _compare(_write_run(
            tmp_path, "root-only", ["root.bst"], [], [("root.bst", 0, D)]), candidate)

        comment = render_ci_comment(comparison, _args())

        assert "more |" in comment
        assert _visible_lines(comment) <= 40
        # And the folded material cannot grow without bound either: a
        # `<details>` a reviewer opens is still a thing they read.
        assert len(comment.splitlines()) <= 60

    def test_the_run_instances_distinguish_two_pushes(self, tmp_path):
        """UX-95: two comments on two pushes carry identical identity
        hashes; only the instant tells them apart."""
        comparison = _compare(_base(tmp_path), _grown(tmp_path, "bad", serialized=True))

        comment = render_ci_comment(comparison, _args())

        assert "baseline " in comment.splitlines()[-1]
        assert "candidate " in comment.splitlines()[-1]

    def test_a_failed_build_is_called_out_above_the_gates(self, tmp_path):
        """UX-54: no scheduling verdict is meaningful for a build that did
        not complete, and the comment must say so before its table."""
        baseline = _base(tmp_path)
        candidate = _grown(tmp_path, "bad", serialized=True)
        context = json.loads((candidate / "run-context.json").read_text())
        # `build_outcome.failed_elements` is what the extractor carries and
        # `AnalysisResult.violations` reads (UX-54).
        context["build_outcome"] = {"failed_elements": ["lib-h.bst"], "failed_count": 1}
        (candidate / "run-context.json").write_text(json.dumps(context))

        comparison = _compare(baseline, candidate)
        assert comparison.failed_runs == ["candidate"]

        comment = render_ci_comment(comparison, _args())

        assert "did not complete" in comment
        assert comment.index("did not complete") < comment.index("| Gate |")
