"""UX-48: idle capacity must be split by whether work was ready to run.

`IDLE_UNDERPARALLEL` was declared in `CPUBucket`, read by `idle_share`, and
never assigned anywhere - the code said so itself ("For now, assign all
to IDLE_NO_TASKS"). So every run booked its whole idle capacity to
`IDLE_NO_TASKS`.

The two buckets recommend opposite fixes:

- `IDLE_NO_TASKS`   - nothing could run. The graph is too narrow;
                      restructure dependencies (a macro change).
- `IDLE_UNDERPARALLEL` - work was ready and nothing ran it. Raise
                      `--builders` (one flag).

So the failure was not a missing number but active misdirection: a
builder-starved run was told to go restructure an already-optimal graph.

A task is *pending* over `[ready_us, start_us)`, where `ready_us` is a
real `max(finish(predecessors))` computed in bga/normalize/timestamps.py.
Idle capacity in a slice with something pending is `UNDERPARALLEL`.
"""
from bga.utilisation import CPUAccounting, CPUBucket, UtilizationAnalyzer


def _interval(task_key, ready_us, start_us, end_us):
    return {
        "task_key": task_key,
        "ready_us": ready_us,
        "start_us": start_us,
        "end_us": end_us,
        "cpu_usage_us": end_us - start_us,
        "concurrent_tasks": [task_key],
    }


def _analyze(task_intervals, effective_cpus, wall_clock_us):
    analyzer = UtilizationAnalyzer(
        cpu_accounting=CPUAccounting(
            effective_cpus=effective_cpus, accounting_method="cgroup"
        ),
        wall_clock_us=wall_clock_us,
    )
    return analyzer.analyze(task_intervals=task_intervals, occupancy_segments=[])


def test_ready_but_unscheduled_work_is_underparallel_not_no_tasks():
    """Four tasks ready at t=0 on a 4-CPU host, but only two ever run at
    once - the builder-starved case. Two slots sat free for 10s while
    two tasks waited."""
    result = _analyze(
        [
            _interval("a", 0, 0, 10_000_000),
            _interval("b", 0, 0, 10_000_000),
            _interval("c", 0, 10_000_000, 20_000_000),
            _interval("d", 0, 10_000_000, 20_000_000),
        ],
        effective_cpus=4,
        wall_clock_us=20_000_000,
    )

    # Capacity 4 x 20s = 80s; useful 4 x 10s = 40s; so 40s idle total.
    # [0s, 10s): a and b run, c and d pending -> 2 free x 10s = 20s
    #            of genuinely underparallel capacity.
    # [10s, 20s): c and d run, nothing pending -> the remaining 20s is
    #            correctly NO_TASKS, not underparallel.
    assert result.buckets[CPUBucket.IDLE_UNDERPARALLEL] == 20_000_000
    assert result.buckets[CPUBucket.IDLE_NO_TASKS] == 20_000_000


def test_serialized_graph_reports_no_tasks_not_underparallel():
    """A chain: each task becomes ready only when its predecessor
    finishes, so nothing is ever waiting. All idle is NO_TASKS, and that
    correctly points the user at the graph rather than at `--builders`.
    """
    result = _analyze(
        [
            _interval("a", 0, 0, 10_000_000),
            _interval("b", 10_000_000, 10_000_000, 20_000_000),
        ],
        effective_cpus=4,
        wall_clock_us=20_000_000,
    )

    assert result.buckets[CPUBucket.IDLE_UNDERPARALLEL] == 0
    assert result.buckets[CPUBucket.IDLE_NO_TASKS] > 0


def test_waiting_with_no_free_capacity_is_not_underparallel():
    """The distinction that stops this becoming "any queue is a
    problem": four tasks pending while all four CPUs are busy is
    saturation, not underparallelism. More builders would not help.
    """
    result = _analyze(
        [
            _interval(f"run{i}", 0, 0, 10_000_000) for i in range(4)
        ] + [
            _interval(f"wait{i}", 0, 10_000_000, 20_000_000) for i in range(4)
        ],
        effective_cpus=4,
        wall_clock_us=20_000_000,
    )

    assert result.buckets[CPUBucket.IDLE_UNDERPARALLEL] == 0


def test_split_preserves_reconciliation_exactly():
    """This moves time between buckets and must neither create nor
    destroy any - I9 reconciliation reports 0.00% error today and must
    keep doing so."""
    result = _analyze(
        [
            _interval("a", 0, 0, 7_000_000),
            _interval("b", 0, 3_000_000, 11_000_000),
            _interval("c", 0, 11_000_000, 13_000_000),
        ],
        effective_cpus=3,
        wall_clock_us=20_000_000,
    )

    assert sum(result.buckets.values()) == result.capacity_cpu_us
    assert result.unaccounted_us == 0
    assert result.reconciliation_error_share == 0.0


def test_underparallel_never_exceeds_total_idle():
    result = _analyze(
        [_interval("solo", 0, 0, 1_000_000)],
        effective_cpus=8,
        wall_clock_us=1_000_000,
    )

    idle = (
        result.buckets[CPUBucket.IDLE_NO_TASKS]
        + result.buckets[CPUBucket.IDLE_UNDERPARALLEL]
    )
    assert result.buckets[CPUBucket.IDLE_UNDERPARALLEL] <= idle
    assert result.buckets[CPUBucket.IDLE_NO_TASKS] >= 0


def test_absent_ready_data_does_not_claim_nothing_was_ready():
    """A run with no `ready_us` at all must not be reported as confident
    `NO_TASKS` on the strength of missing data - underparallel is 0
    because it is unmeasured, and the intervals carry no pending window
    to contradict that."""
    intervals = [
        {
            "task_key": "a",
            "start_us": 0,
            "end_us": 5_000_000,
            "cpu_usage_us": 5_000_000,
            "concurrent_tasks": ["a"],
        }
    ]
    result = _analyze(intervals, effective_cpus=4, wall_clock_us=10_000_000)

    assert result.buckets[CPUBucket.IDLE_UNDERPARALLEL] == 0


def test_no_capacity_means_both_idle_buckets_stay_zero():
    """Unchanged behaviour from P1-33/UX-17: without a real capacity
    there is nothing for idle to be a portion of."""
    analyzer = UtilizationAnalyzer(cpu_accounting=CPUAccounting(), wall_clock_us=10_000_000)
    result = analyzer.analyze(
        task_intervals=[_interval("a", 0, 5_000_000, 10_000_000)],
        occupancy_segments=[],
    )

    assert result.buckets[CPUBucket.IDLE_NO_TASKS] == 0
    assert result.buckets[CPUBucket.IDLE_UNDERPARALLEL] == 0


def test_absolute_epoch_timestamps_are_handled():
    """Real captures carry absolute epoch microseconds while
    `wall_clock_us` is a duration. An earlier draft clamped the sweep to
    `[0, wall_clock_us]` and silently discarded every real boundary,
    reporting 0 on the very run this task is about."""
    epoch = 1_786_905_639_850_000
    result = _analyze(
        [
            _interval("a", epoch, epoch, epoch + 10_000_000),
            _interval("b", epoch, epoch, epoch + 10_000_000),
            _interval("c", epoch, epoch + 10_000_000, epoch + 20_000_000),
        ],
        effective_cpus=4,
        wall_clock_us=20_000_000,
    )

    assert result.buckets[CPUBucket.IDLE_UNDERPARALLEL] > 0
