"""UX-156: a build that did not finish must not verdict as if it did.

Round 16 reproduced `Verdict: IMPROVED (-65.6%)` on a build where one
element failed to compile and four never ran. Of course it was faster.
The extraction knew - `run-context.json` carried `build_outcome` - and
the verdict, the analysis banner and the baseline choice all ignored it.
"""
import json

from bga.compare import (
    ComparisonResult, _build_failure_detail, _describe_build_failures,
)
from bga.report.text import format_compare_text
from tools.bga_snapshot import _healthy_baseline, _snapshot_failed


class _Result:
    """The parts of `AnalysisResult` the detail builder reads."""

    def __init__(self, violations):
        self.violations = violations


def _failed_violation(elements, built=0, scheduled=7, cached=6):
    return {'type': 'build_failed', 'failed_count': len(elements),
            'failed_elements': list(elements),
            'built_count': built, 'scheduled_count': scheduled,
            # UX-164 item 3: how many of the rest were cache hits rather
            # than losses.
            'cached_count': cached}


class TestTheDetailComesOffTheViolation:
    def test_it_reads_names_and_counts(self):
        detail = _build_failure_detail(
            "candidate", _Result([_failed_violation(["lib-d.bst"])]))
        assert detail == {'run': 'candidate', 'failed_elements': ['lib-d.bst'],
                          'built': 0, 'scheduled': 7, 'cached': 6,
                          'interrupted': False}

    def test_a_capture_with_no_queue_summary_yields_no_counts(self):
        """`build_outcome` predates `queue_summary` on some captures, and a
        refusal that invents "0 of 0" is worse than one that just names
        the element."""
        violation = _failed_violation(["lib-d.bst"])
        violation['built_count'] = violation['scheduled_count'] = None
        violation['cached_count'] = None
        detail = _build_failure_detail("candidate", _Result([violation]))
        assert detail['built'] is None and detail['scheduled'] is None
        assert "scheduled" not in _describe_build_failures([detail])

    def test_the_counts_are_not_recoverable_from_the_analysis_result(self):
        """Pins why the analyzer records them at all: `AnalysisResult`
        exposes no `run_context`, so a downstream `getattr` for the queue
        summary silently returns None on every real run - which is how the
        first version of this dropped the clause everywhere."""
        from bga.analyzer import AnalysisResult
        assert not hasattr(AnalysisResult, 'run_context')


class TestTheVerdictRefuses:
    def _comparison(self, **kwargs):
        details = kwargs.pop('details', [
            {'run': 'candidate', 'failed_elements': ['lib-d.bst'],
             'built': 0, 'scheduled': 7, 'cached': 6}])
        base = dict(
            baseline_confidence=1.0, candidate_confidence=1.0,
            attribution_deltas={}, low_confidence=False,
            baseline_run_id="b", candidate_run_id="c",
            baseline_metrics={'total_duration_us': 40_150_000},
            candidate_metrics={'total_duration_us': 13_800_000},
            deltas={'total_duration_us': -26_350_000},
            verdict=f"not comparable ({_describe_build_failures(details)})",
            failed_runs=['candidate'], failed_run_details=details,
        )
        base.update(kwargs)
        return ComparisonResult(**base)

    def test_the_verdict_line_is_the_refusal_not_a_direction(self):
        text = format_compare_text(self._comparison())
        verdict = [ln for ln in text.splitlines() if ln.startswith("Verdict:")]
        assert verdict == ["Verdict: NOT COMPARABLE"]
        assert "IMPROVED" not in text

    def test_it_names_the_element_and_how_far_the_build_got(self):
        text = format_compare_text(self._comparison())
        assert "lib-d.bst" in text
        # UX-164 item 3 changed this wording deliberately: "0 of 7
        # scheduled" counted six cache hits as casualties, overstating
        # the damage sevenfold.
        assert "0 built, 6 already cached" in text

    def test_the_delta_is_still_shown_but_marked_as_not_a_verdict(self):
        """The partial numbers stay for a reader who wants them; what must
        not happen is presenting them *as* the verdict."""
        text = format_compare_text(self._comparison())
        assert "Not a verdict, for reference only" in text
        assert "-26.35s" in text or "-26.3s" in text

    def test_a_healthy_comparison_keeps_the_single_line_form(self):
        healthy = ComparisonResult(
            baseline_confidence=1.0, candidate_confidence=1.0,
            attribution_deltas={}, low_confidence=False,
            baseline_run_id="b", candidate_run_id="c",
            baseline_metrics={'total_duration_us': 40_150_000},
            candidate_metrics={'total_duration_us': 13_800_000},
            deltas={'total_duration_us': -26_350_000},
            verdict="improved",
        )
        text = format_compare_text(healthy)
        assert any(ln.startswith("Verdict: IMPROVED  (total duration")
                   for ln in text.splitlines())
        assert "Not a verdict" not in text


class TestEndToEndThroughTheRealComparison:
    """The guard the hand-built `ComparisonResult` above cannot give.

    Falsifying the refusal by neutering `compare.py`'s `if
    failed_run_details:` reddened **nothing** the first time: every other
    test in this file supplies the verdict string itself, so none of
    them exercised the decision to refuse. These drive `compare_runs`
    over real run directories instead.
    """

    _CONTEXT = {"trace_epsilon_us": 1000, "wall_start_us": 0,
                "wall_end_us": 200000, "max_jobs": 2,
                "resource_capacities": {"PROCESS": 2}}

    def _run_dir(self, tmp_path, name, dur, failed=()):
        run_dir = tmp_path / name
        run_dir.mkdir(parents=True)
        context = dict(self._CONTEXT)
        context["build_outcome"] = {"failed_elements": list(failed),
                                    "failed_count": len(failed)}
        context["queue_summary"] = {"build": {"processed": 0 if failed else 2,
                                              "skipped": 5, "failed": len(failed)}}
        (run_dir / "run-context.json").write_text(json.dumps(context))
        (run_dir / "graph.json").write_text(json.dumps(
            {"elements": [{"uid": "a.bst"}], "dependencies": []}))
        (run_dir / "trace.json").write_text(json.dumps({"spans": [{
            "task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": dur,
            "resources": ["PROCESS"], "primary_resource": "PROCESS"}],
            "phases": []}))
        return run_dir

    def test_a_failed_candidate_refuses_instead_of_reporting_improved(self, tmp_path):
        from bga.compare import compare_runs
        baseline = self._run_dir(tmp_path, "baseline", 40_000)
        candidate = self._run_dir(tmp_path, "candidate", 4_000, failed=["lib-d.bst"])

        comparison = compare_runs(baseline, candidate)

        assert comparison.verdict.startswith("not comparable")
        assert "lib-d.bst" in comparison.verdict
        assert "improved" not in comparison.verdict

    def test_the_same_two_runs_without_the_failure_do_report_improved(self, tmp_path):
        """The control: the refusal must come from the failure, not from
        the shape of the fixture."""
        from bga.compare import compare_runs
        baseline = self._run_dir(tmp_path, "baseline", 40_000)
        candidate = self._run_dir(tmp_path, "candidate", 4_000)

        assert compare_runs(baseline, candidate).verdict == "improved"

    def test_a_failed_baseline_refuses_too(self, tmp_path):
        from bga.compare import compare_runs
        baseline = self._run_dir(tmp_path, "baseline", 40_000, failed=["core.bst"])
        candidate = self._run_dir(tmp_path, "candidate", 4_000)

        comparison = compare_runs(baseline, candidate)

        assert comparison.verdict.startswith("not comparable")
        assert "the baseline build failed" in comparison.verdict

    def test_the_counts_survive_the_whole_path(self, tmp_path):
        """analyzer -> violation -> detail -> verdict, on real inputs."""
        from bga.compare import compare_runs
        baseline = self._run_dir(tmp_path, "baseline", 40_000)
        candidate = self._run_dir(tmp_path, "candidate", 4_000, failed=["lib-d.bst"])

        comparison = compare_runs(baseline, candidate)

        assert comparison.failed_run_details[0]['scheduled'] == 6
        # UX-164 item 3: built and cached, not a lump "scheduled".
        assert "0 built, 5 already cached" in comparison.verdict


class TestTheBaselineChoiceSkipsWreckage:
    def _snapshot(self, tmp_path, name, failed=()):
        run = tmp_path / name / "run"
        run.mkdir(parents=True)
        (run / "run-context.json").write_text(json.dumps(
            {"build_outcome": {"failed_elements": list(failed),
                               "failed_count": len(failed)}}))
        return str(tmp_path / name)

    def test_a_failed_snapshot_is_recognised(self, tmp_path):
        assert _snapshot_failed(self._snapshot(tmp_path, "a", ["lib-d.bst"]))
        assert not _snapshot_failed(self._snapshot(tmp_path, "b"))

    def test_a_capture_that_does_not_say_counts_as_healthy(self, tmp_path):
        """`build_outcome` is written unconditionally, so its absence means
        the capture predates UX-54. Refusing every older run would be a
        worse failure than the one this prevents."""
        older = tmp_path / "old" / "run"
        older.mkdir(parents=True)
        (older / "run-context.json").write_text("{}")
        assert not _snapshot_failed(str(tmp_path / "old"))

    def test_it_walks_back_past_the_failed_run_and_reports_the_skip(self, tmp_path):
        healthy = self._snapshot(tmp_path, "01-healthy")
        broken = self._snapshot(tmp_path, "02-broken", ["lib-d.bst"])
        chosen, skipped = _healthy_baseline([healthy, broken])
        assert chosen == healthy
        assert skipped == [broken]

    def test_the_newest_healthy_run_wins(self, tmp_path):
        old = self._snapshot(tmp_path, "01-healthy")
        newer = self._snapshot(tmp_path, "02-healthy")
        assert _healthy_baseline([old, newer]) == (newer, [])

    def test_all_failed_means_no_baseline_rather_than_the_least_bad(self, tmp_path):
        a = self._snapshot(tmp_path, "01", ["x.bst"])
        b = self._snapshot(tmp_path, "02", ["y.bst"])
        chosen, skipped = _healthy_baseline([a, b])
        assert chosen is None
        assert skipped == [a, b]
