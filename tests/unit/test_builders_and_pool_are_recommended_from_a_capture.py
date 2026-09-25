"""UX-1005 track A: `bga analyze` recommends a builder count and a pool
size, each with the reading it came from - builders from the replay's
ready-set width, the pool from UX-1004's recorded knee, never from
`max_jobs`/`host_cpu_count` directly (the Decision's own two mutations).
"""
from bga.correlate import compute_builder_pool_recommendation, compute_ready_set_width
from bga.ingest.models import NormalizedTask, RunContext, TaskKey, TaskKind
from bga.replay.scheduler import ReplayScheduler


def _task(uid, dur_us=1_000_000):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=dur_us,
    )


def _wide_and_narrow_scheduler(configured_max_jobs=32):
    """One giant plus 24 narrow siblings, all ready at once - the
    `13-mixed-graph` shape the Graviton reading below was measured on.
    `configured_max_jobs` is deliberately far from the real ready-set
    width (25): a recommendation reading it instead of the replay would
    print a number this fixture never earns.
    """
    tasks = [_task("giant.bst", 8_000_000)]
    tasks += [_task(f"narrow-{i:02d}.bst", 1_000_000) for i in range(1, 25)]
    context = RunContext(resource_capacities={"PROCESS": configured_max_jobs},
                          max_jobs=configured_max_jobs, host_cpu_count=16)
    return ReplayScheduler(tasks, context)


class TestReadySetWidth:
    def test_ready_set_width_is_the_graphs_own_peak_concurrency(self):
        """25 tasks, no dependencies: every one is ready at once - the
        ready-set width is the population, not the configured capacity."""
        scheduler = _wide_and_narrow_scheduler(configured_max_jobs=32)
        assert compute_ready_set_width(scheduler) == 25

    def test_ready_set_width_is_not_the_configured_max_jobs(self):
        """UX-1005 Decision mutation: builders from `max_jobs` reddens
        this - `max_jobs` here is 4, the real ready-set width is still 25."""
        scheduler = _wide_and_narrow_scheduler(configured_max_jobs=4)
        assert compute_ready_set_width(scheduler) == 25

    def test_a_serial_chain_has_ready_set_width_one(self):
        """A single dependency chain never has two ready tasks at once -
        the width the naive `max_jobs`-reading mutation could not produce
        by accident, since a wide `max_jobs` would still print more than 1."""
        first = NormalizedTask(task_key=TaskKey("a.bst", TaskKind.BUILD, "BUILD", 0),
                                ready_us=0, start_us=0, finish_us=1_000_000)
        second = NormalizedTask(task_key=TaskKey("b.bst", TaskKind.BUILD, "BUILD", 0),
                                 ready_us=0, start_us=1_000_000, finish_us=2_000_000,
                                 dependencies=[first.task_key])
        scheduler = ReplayScheduler(
            [first, second],
            RunContext(resource_capacities={"PROCESS": 8}, max_jobs=8, host_cpu_count=16))
        assert compute_ready_set_width(scheduler) == 1


class TestPoolFromTheCalibratedKnee:
    def test_pool_is_the_calibrated_knee_when_supplied(self):
        recommendation = compute_builder_pool_recommendation(
            ready_set_width=25, host_cpu_count=16, critical_path_max_jobs=8,
            calibrated_cores=2)
        assert recommendation["pool_size"] == 2
        assert "UX-1004" in recommendation["pool_reading"]

    def test_pool_is_not_the_raw_host_cpu_count_when_a_knee_is_supplied(self):
        """UX-1005 Decision mutation: pool from `host_cpu_count` reddens
        this - the calibrated knee (2) differs from the host's raw 16
        cores, so reading `host_cpu_count` instead prints the wrong pool."""
        recommendation = compute_builder_pool_recommendation(
            ready_set_width=25, host_cpu_count=16, critical_path_max_jobs=8,
            calibrated_cores=2)
        assert recommendation["pool_size"] != 16

    def test_pool_falls_back_to_host_cpu_count_uncalibrated_when_no_knee(self):
        recommendation = compute_builder_pool_recommendation(
            ready_set_width=25, host_cpu_count=16, critical_path_max_jobs=8)
        assert recommendation["pool_size"] == 16
        assert "uncalibrated" in recommendation["pool_reading"]


class TestTheSafeCapIsHonestAboutAdmission:
    def test_safe_cap_is_the_cores_the_critical_path_element_leaves_free(self):
        """16 host cores, the critical path's own element needs 8 for its
        native max-jobs: the safe cap is the other 8, not the ready-set
        width of 25 - the Graviton reading this predictor must not repeat
        (33 jobs on 16 cores: 4 builders wall ~143s beat 32 builders'
        ~208s, examples/13-mixed-graph, 3 repeats, cold cache)."""
        recommendation = compute_builder_pool_recommendation(
            ready_set_width=25, host_cpu_count=16, critical_path_max_jobs=8)
        assert recommendation["ready_set_width"] == 25
        assert recommendation["safe_builder_cap"] == 8
        assert recommendation["safe_builder_cap"] < recommendation["ready_set_width"]

    def test_no_recommendation_without_a_ready_set_width_or_host_cores(self):
        assert compute_builder_pool_recommendation(None, 16, 8) == {}
        assert compute_builder_pool_recommendation(25, None, 8) == {}
