"""P3-04: resource-holder tests (Part 8, depends on P1-01's real
holder-tracking implementation).

`BlameChainAnalyzer.classify_resource_wait` derives holders directly
from observed [start_us, finish_us) overlaps with the waiting task's
[ready_us, start_us) window - tested directly against a small
BlameChainAnalyzer built from hand-constructed NormalizedTask objects,
no run-dir/JSON fixture needed.
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
    occupies PROCESS for the entire wait window."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder = _task("holder.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {})
    assert is_wait is True
    assert info["blocking_tasks"] == {"holder.bst|BUILD|BUILD|0": 1.0}
    assert info["ambiguous"] is False
    assert info["explained_us"] == 10000


def test_multiple_simultaneous_holders_time_weighted_split():
    """Wait window [0, 10000): holder_a occupies the first 7000us (70%),
    holder_b occupies the last 3000us (30%) - matches the spec's own
    Part 8.2 worked example proportions."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    holder_a = _task("holder_a.bst", ready_us=0, start_us=0, finish_us=7000)
    holder_b = _task("holder_b.bst", ready_us=0, start_us=7000, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder_a, holder_b])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {})
    assert is_wait is True
    assert info["blocking_tasks"] == {
        "holder_a.bst|BUILD|BUILD|0": 0.7,
        "holder_b.bst|BUILD|BUILD|0": 0.3,
    }
    assert info["ambiguous"] is False


def test_holder_changes_mid_wait_both_appear_with_correct_shares():
    """A third holder overlaps only part of the window, alongside a
    holder present for the whole window - both must appear, weighted by
    their actual overlap, not just presence/absence."""
    # full_span holds DOWNLOAD the entire 20000us wait.
    full_span = _task("full_span.bst", ready_us=0, start_us=0, finish_us=20000, resources=(Resource.DOWNLOAD,))
    # mid_change only overlaps [5000, 15000) of the wait window (10000us).
    mid_change = _task("mid_change.bst", ready_us=0, start_us=5000, finish_us=15000)
    waiting_needs = _task("waiting.bst", ready_us=0, start_us=20000, finish_us=30000,
                           resources=(Resource.PROCESS, Resource.DOWNLOAD))
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting_needs, full_span, mid_change])

    is_wait, info = analyzer.classify_resource_wait(waiting_needs, {}, {})
    assert is_wait is True
    # full_span explains the entire 20000us window (DOWNLOAD); mid_change
    # explains 10000us of it (PROCESS) - shares are independent per the
    # blocking_tasks dict (each holder's share of the wait window it
    # actually overlapped, not normalized against each other).
    assert info["blocking_tasks"]["full_span.bst|BUILD|BUILD|0"] == 1.0
    assert info["blocking_tasks"]["mid_change.bst|BUILD|BUILD|0"] == 0.5
    assert info["ambiguous"] is False


def test_no_identifiable_holder_is_unknown_not_fabricated():
    """waiting.bst waits, but no other task overlaps its wait window at
    all - must report UNKNOWN/ambiguous, never invent a holder."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    unrelated = _task("unrelated.bst", ready_us=0, start_us=15000, finish_us=25000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, unrelated])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {})
    assert is_wait is True
    assert info["blocking_tasks"] == "UNKNOWN"
    assert info["ambiguous"] is True
    assert info["explained_us"] == 0


def test_partial_explanation_is_still_marked_ambiguous():
    """A holder explains only part of the wait window - the unexplained
    remainder must still mark the whole interval ambiguous, not silently
    treat partial coverage as full explanation."""
    waiting = _task("waiting.bst", ready_us=0, start_us=10000, finish_us=20000)
    partial_holder = _task("partial.bst", ready_us=0, start_us=0, finish_us=4000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, partial_holder])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {})
    assert is_wait is True
    assert info["blocking_tasks"] == {"partial.bst|BUILD|BUILD|0": 0.4}
    assert info["ambiguous"] is True
    assert info["explained_us"] == 4000


def test_task_with_no_wait_is_not_a_resource_wait():
    task = _task("prompt.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[task])
    is_wait, info = analyzer.classify_resource_wait(task, {}, {})
    assert is_wait is False
    assert info is None


def test_task_with_no_resources_is_never_a_resource_wait():
    task = _task("no_res.bst", ready_us=0, start_us=10000, finish_us=20000, resources=())
    holder = _task("holder.bst", ready_us=0, start_us=0, finish_us=10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[task, holder])
    is_wait, info = analyzer.classify_resource_wait(task, {}, {})
    assert is_wait is False
    assert info is None
