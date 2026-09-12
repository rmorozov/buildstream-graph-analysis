"""UX-677: per-element `max-jobs`, under the no-overcommit constraint.

The three decisions taken for this row: the evidence is `UX-675`'s raw
host CPU series joined to each element's own BUILD span, not `UX-676`'s
capped, ranked interval tables; thin evidence is a stated refusal, not
a number; and a guard checks the *published* recommendation against the
inequality itself, on `tests/fixtures/host_cpu` - a real capture of
`examples/06-macro-micro-optimization` - rather than the formula's
shape.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.cli import _max_jobs_advice
from bga.correlate import MIN_HOST_SAMPLES_IN_SPAN, compute_max_jobs_advice
from bga.ingest.models import Element, Graph, NormalizedTask, TaskKey, TaskKind
from bga.utilisation.envelope import intervals, wall_samples

FIXTURE = REPO / "tests" / "fixtures" / "host_cpu"


def _real_inputs():
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.analyze(FIXTURE / "run")
    host_samples = analyzer.read_host_samples()
    tasks = [{"element": t.task_key.element_uid, "start_us": t.start_us,
              "finish_us": t.finish_us} for t in analyzer.normalized_tasks]
    max_jobs = {e.uid: e.max_jobs for e in analyzer.graph.elements}
    return host_samples, tasks, max_jobs


class TestTheRealFixture:
    """`tests/fixtures/host_cpu`'s own README: `core.bst` is
    `notparallel` (max-jobs 1) while three cores idle; the other real
    elements are `-j4` but never overlap more than one other."""

    def test_core_bst_is_recommended_above_dash_j1(self):
        host_samples, tasks, max_jobs = _real_inputs()
        advice = compute_max_jobs_advice(host_samples, tasks, max_jobs)
        row = next(r for r in advice["elements"] if r["element"] == "core.bst")
        assert row["current_max_jobs"] == 1
        assert row["recommended_max_jobs"] > 1
        assert row["refusal"] is None

    def test_an_overlapping_dash_j4_element_is_recommended_down(self):
        """`lib-a.bst` never overlaps more than one other element at
        once on this 4-core host, so `-j4` is the other sign of the
        same defect the Motivation names."""
        host_samples, tasks, max_jobs = _real_inputs()
        advice = compute_max_jobs_advice(host_samples, tasks, max_jobs)
        row = next(r for r in advice["elements"] if r["element"] == "lib-a.bst")
        assert row["current_max_jobs"] == 4
        assert row["recommended_max_jobs"] == 2

    def test_thin_evidence_is_a_refusal_not_a_number(self):
        """`app.bst` (1.95s) and the zero-duration structural elements
        touch fewer than `MIN_HOST_SAMPLES_IN_SPAN` host-CPU intervals -
        the distribution this module's own docstring measures."""
        host_samples, tasks, max_jobs = _real_inputs()
        advice = compute_max_jobs_advice(host_samples, tasks, max_jobs)
        by_uid = {r["element"]: r for r in advice["elements"]}
        for uid in ("app.bst", "toolchain.bst", "all.bst"):
            row = by_uid[uid]
            assert row["samples_in_span"] < MIN_HOST_SAMPLES_IN_SPAN
            assert row["recommended_max_jobs"] is None
            assert row["refusal"] and str(MIN_HOST_SAMPLES_IN_SPAN) in row["refusal"]

    def test_the_published_recommendation_never_overcommits_cores(self):
        """The constraint itself, checked against the published output -
        not the formula's shape. At every host-CPU-sample instant, the
        sum of the *published* `recommended_max_jobs` for the elements
        building then must not exceed the host's real core count."""
        host_samples, tasks, max_jobs = _real_inputs()
        advice = compute_max_jobs_advice(host_samples, tasks, max_jobs)
        recommended = {r["element"]: r["recommended_max_jobs"]
                       for r in advice["elements"]}
        windows = intervals(wall_samples(host_samples))
        for window in windows:
            building = {t["element"] for t in tasks
                        if t["start_us"] < window["end_us"]
                        and t["finish_us"] > window["start_us"]}
            total = sum(recommended.get(uid) or 0 for uid in building)
            assert total <= advice["host_cores"], (window, building, total)


class TestTheSplitThatFits:
    """The Acceptance Test's own synthetic case: two `-j8` elements
    overlapping for their whole span on a 4-core host."""

    def test_two_dash_j8_elements_are_split_to_fit(self):
        host_samples = {
            # `wall_at_start`/`monotonic_at_start` both 0, so `at_us`
            # below is `t` in microseconds - the same clock the tasks'
            # `start_us`/`finish_us` are stated in.
            "header": {"schema": "host-samples/v1", "wall_at_start": 0.0,
                       "monotonic_at_start": 0.0},
            "samples": [
                {"t": 0.0, "cores": 4, "cpu_busy_cores": 3.9},
                {"t": 2.0, "cores": 4, "cpu_busy_cores": 3.9},
                {"t": 4.0, "cores": 4, "cpu_busy_cores": 3.9},
            ],
        }
        tasks = [
            {"element": "a.bst", "start_us": 0, "finish_us": 4_000_000},
            {"element": "b.bst", "start_us": 0, "finish_us": 4_000_000},
        ]
        max_jobs = {"a.bst": 8, "b.bst": 8}
        advice = compute_max_jobs_advice(host_samples, tasks, max_jobs)
        by_uid = {r["element"]: r for r in advice["elements"]}
        assert by_uid["a.bst"]["recommended_max_jobs"] == 2
        assert by_uid["b.bst"]["recommended_max_jobs"] == 2
        assert (by_uid["a.bst"]["recommended_max_jobs"]
                + by_uid["b.bst"]["recommended_max_jobs"]) <= 4


class TestTheMemoryConstraint:
    """Decision 3's other half: the sum of measured peak RSS for the
    elements building at once must not exceed the host's own measured
    memory. `core.bst` and `lib-a.bst` really do overlap in
    `host_cpu`'s own capture (see `TestTheRealFixture`); the peak RSS
    figures here are the ones this row's Acceptance Test names as
    missing from any committed fixture, stated directly instead."""

    def test_an_overcommitting_overlap_is_a_refusal(self):
        host_samples, tasks, max_jobs = _real_inputs()
        peak_rss_bytes = {"core.bst": 3_000_000_000, "lib-a.bst": 2_000_000_000}
        advice = compute_max_jobs_advice(
            host_samples, tasks, max_jobs, peak_rss_bytes=peak_rss_bytes,
            host_memory_bytes=4_000_000_000)
        by_uid = {r["element"]: r for r in advice["elements"]}
        for uid in ("core.bst", "lib-a.bst"):
            assert by_uid[uid]["recommended_max_jobs"] is None
            assert by_uid[uid]["refusal"] and "memory" in by_uid[uid]["refusal"] \
                or "bytes" in by_uid[uid]["refusal"]

    def test_room_in_memory_leaves_the_cpu_number_alone(self):
        host_samples, tasks, max_jobs = _real_inputs()
        peak_rss_bytes = {"core.bst": 1_000_000, "lib-a.bst": 1_000_000}
        advice = compute_max_jobs_advice(
            host_samples, tasks, max_jobs, peak_rss_bytes=peak_rss_bytes,
            host_memory_bytes=4_000_000_000)
        row = next(r for r in advice["elements"] if r["element"] == "core.bst")
        assert row["recommended_max_jobs"] == 2
        assert row["refusal"] is None


class _FakeAnalyzer:
    """The shape `_max_jobs_advice` reads: `read_host_samples()`,
    `.graph`, `.normalized_tasks` - a fresh double per test rather than
    the real analyzer, so a BUILD+FETCH pair can be asserted without a
    capture (`tests/fixtures/host_cpu` is warm on sources and has none,
    `UX-808`'s own Motivation)."""

    def __init__(self, host_samples, graph, normalized_tasks):
        self._host_samples = host_samples
        self.graph = graph
        self.normalized_tasks = normalized_tasks

    def read_host_samples(self):
        return self._host_samples


class TestOneRowPerBuiltElement:
    """UX-808: a cold element carries a FETCH task beside its BUILD
    task; the advice must judge it once, on the BUILD span, not twice."""

    _HOST_SAMPLES = {
        "header": {"schema": "host-samples/v1", "wall_at_start": 0.0,
                   "monotonic_at_start": 0.0},
        "samples": [
            {"t": 0.0, "cores": 4, "cpu_busy_cores": 3.9},
            {"t": 2.0, "cores": 4, "cpu_busy_cores": 3.9},
            {"t": 4.0, "cores": 4, "cpu_busy_cores": 3.9},
        ],
    }

    def _inputs(self):
        graph = Graph(elements=[Element(uid="a.bst", max_jobs=4)])
        tasks = [
            NormalizedTask(
                task_key=TaskKey(element_uid="a.bst", task_kind=TaskKind.FETCH,
                                  phase="fetch"),
                ready_us=0, start_us=0, finish_us=1_000_000, dependencies=[],
                resources=[], primary_resource=None,
            ),
            NormalizedTask(
                task_key=TaskKey(element_uid="a.bst", task_kind=TaskKind.BUILD,
                                  phase="build"),
                ready_us=0, start_us=1_000_000, finish_us=5_000_000,
                dependencies=[], resources=[], primary_resource=None,
            ),
        ]
        return _FakeAnalyzer(self._HOST_SAMPLES, graph, tasks)

    def test_a_build_and_fetch_task_yield_one_row(self):
        advice = _max_jobs_advice(self._inputs(), native_report={})
        assert len([r for r in advice["elements"] if r["element"] == "a.bst"]) == 1


class TestWhatItRefusesToSay:
    def test_no_host_series_means_no_block(self):
        assert compute_max_jobs_advice({}, [], {}) == {}

    def test_a_series_with_no_core_count_means_no_block(self):
        host_samples = {
            "header": {"wall_at_start": 1000.0, "monotonic_at_start": 0.0},
            "samples": [{"t": 0.0, "cpu_busy_cores": 1.0},
                        {"t": 2.0, "cpu_busy_cores": 1.0}],
        }
        assert compute_max_jobs_advice(host_samples, [], {}) == {}
