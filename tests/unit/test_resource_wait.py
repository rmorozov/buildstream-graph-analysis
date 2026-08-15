"""P3-04 (P1-31: made capacity-aware): resource-holder tests (Part 8).

`BlameChainAnalyzer.classify_resource_wait` only classifies (a prefix
of) a wait interval as RESOURCE_WAIT where a required resource was
genuinely saturated (occupancy >= capacity) - not merely "some other
task with the same resource type overlaps in time" (P1-31's fix; the
previous version's tests all passed `resource_capacity={}`, which never
exercised the capacity check at all - every scenario below now passes
real, non-empty capacity).
"""
from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.ingest.models import NormalizedTask, Resource, TaskKey, TaskKind


def _task(uid, ready_us, start_us, finish_us, resources=(Resource.PROCESS,)):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=ready_us, start_us=start_us, finish_us=finish_us,
        resources=list(resources),
    )


def test_single_identifiable_holder():
    """waiting.bst is ready at 0 but can't start until 10000 - holder.bst
    occupies PROCESS for the entire wait window; capacity=1 means that
    single holder alone saturates it throughout."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder = _task("holder.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is True
    assert info["blocking_tasks"] == {"holder.bst|BUILD|BUILD|0": 1.0}
    assert info["ambiguous"] is False
    assert info["explained_us"] == 10000


def test_multiple_simultaneous_holders_time_weighted_split():
    """Wait window [0, 10000): holder_a occupies the first 7000us (70%),
    holder_b occupies the last 3000us (30%), capacity=1 - each alone
    saturates PROCESS during its own span, so the whole window is a
    saturated prefix, matching the spec's own Part 8.2 worked example
    proportions."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder_a = _task("holder_a.bst", ready_us=0, start_us=0, finish_us=7000)
    holder_b = _task("holder_b.bst", ready_us=0, start_us=7000, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder_a, holder_b])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is True
    assert info["blocking_tasks"] == {
        "holder_a.bst|BUILD|BUILD|0": 0.7,
        "holder_b.bst|BUILD|BUILD|0": 0.3,
    }
    assert info["ambiguous"] is False


def test_two_simultaneous_holders_under_capacity_two():
    """capacity=2, two holders simultaneously active for the whole
    window - genuinely saturated (occupancy 2 >= capacity 2); both
    holders attributed by their real (full) overlap."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder_a = _task("holder_a.bst", ready_us=0, start_us=0, finish_us=10000)
    holder_b = _task("holder_b.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(
        normalized_tasks=[waiting, holder_a, holder_b],
    )

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 2})
    assert is_wait is True
    assert info["explained_us"] == 10000
    assert info["blocking_tasks"] == {
        "holder_a.bst|BUILD|BUILD|0": 1.0,
        "holder_b.bst|BUILD|BUILD|0": 1.0,
    }
    assert info["ambiguous"] is False


def test_one_holder_under_capacity_two_is_not_resource_wait():
    """capacity=2, only one holder active (one spare slot) - a real spare
    slot exists, so this is NOT resource-wait (falls through to
    scheduler-wait/dependency-wait instead) - the exact counterexample
    the pre-P1-31 implementation got wrong."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder = _task("holder.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 2})
    assert is_wait is False
    assert info is None


def test_saturation_changes_mid_wait_splits_the_interval():
    """capacity=2: two holders occupy [0, 6000) (saturated), then one of
    them finishes, leaving only one holder for [6000, 10000) (a real
    spare slot - not saturated). Only the genuinely saturated prefix
    [0, 6000) is explained as resource-wait."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder_a = _task("holder_a.bst", ready_us=0, start_us=0, finish_us=10000)
    holder_b = _task("holder_b.bst", ready_us=0, start_us=0, finish_us=6000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder_a, holder_b])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 2})
    assert is_wait is True
    assert info["explained_us"] == 6000
    assert info["blocking_tasks"] == {
        "holder_a.bst|BUILD|BUILD|0": 1.0,
        "holder_b.bst|BUILD|BUILD|0": 1.0,
    }
    assert info["ambiguous"] is False


def test_unknown_capacity_falls_through_not_fabricated():
    """No capacity entry at all for the required resource - never
    fabricated as either saturated or available; falls through
    (is_resource_wait=False), the same "absence of capacity data is not
    evidence of unavailability" discipline _resource_available_at uses."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder = _task("holder.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {})
    assert is_wait is False
    assert info is None


def test_multi_resource_only_saturated_resource_counts_as_holder():
    """waiting needs PROCESS+DOWNLOAD. full_span holds DOWNLOAD for the
    entire 20000us window (capacity=1, always saturated). mid_change
    holds PROCESS only during [5000, 15000) (capacity=1, saturated only
    there). Per-sub-interval holder attribution: full_span explains the
    whole window (DOWNLOAD alone is sufficient reason the task couldn't
    start, throughout); mid_change is only counted for the sub-interval
    where PROCESS specifically was the saturated resource."""
    full_span = _task("full_span.bst", ready_us=0, start_us=0, finish_us=20000, resources=(Resource.DOWNLOAD,))
    mid_change = _task("mid_change.bst", ready_us=0, start_us=5000, finish_us=15000)
    waiting_needs = _task("waiting.bst", ready_us=0, start_us=20000, finish_us=30000,
                           resources=(Resource.PROCESS, Resource.DOWNLOAD))
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting_needs, full_span, mid_change])

    is_wait, info = analyzer.classify_resource_wait(
        waiting_needs, {}, {Resource.PROCESS: 1, Resource.DOWNLOAD: 1},
    )
    assert is_wait is True
    assert info["explained_us"] == 20000
    assert info["blocking_tasks"]["full_span.bst|BUILD|BUILD|0"] == 1.0
    assert info["blocking_tasks"]["mid_change.bst|BUILD|BUILD|0"] == 0.5
    assert info["ambiguous"] is False


def test_no_overlap_at_all_falls_through():
    """waiting.bst waits, but no other task overlaps its wait window at
    all - no saturation possible, falls through rather than fabricating
    a holder."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    unrelated = _task("unrelated.bst", ready_us=0, start_us=15000, finish_us=25000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, unrelated])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is False
    assert info is None


def test_task_with_no_wait_is_not_a_resource_wait():
    task = _task("prompt.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[task])
    is_wait, info = analyzer.classify_resource_wait(task, {}, {Resource.PROCESS: 1})
    assert is_wait is False
    assert info is None


def test_task_with_no_resources_is_never_a_resource_wait():
    task = _task("no_res.bst", ready_us=0, start_us=10000, finish_us=20000, resources=())
    holder = _task("holder.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[task, holder])
    is_wait, info = analyzer.classify_resource_wait(task, {}, {Resource.PROCESS: 1})
    assert is_wait is False
    assert info is None
