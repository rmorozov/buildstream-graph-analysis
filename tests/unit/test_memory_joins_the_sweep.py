"""UX-678: memory as a second replay resource beside builders.

The sweep's own knee (`bga sweep`) says "eight builders buy 40%" on a
machine whose RAM fits four of these elements at once, and the envelope
that knows that never joined the sweep. These build the same graph two
ways - each element's peak RSS never crossing host RAM, and crossing it
at capacity 4 - and check the memory-feasible ceiling and the binding
constraint `capacity_sweep` now computes from its own replayed
concurrency, not a top-N sum.
"""
import json
import subprocess
import sys

from bga.ingest.models import NormalizedTask, RunContext, TaskKey, TaskKind
from bga.replay.scheduler import ReplayScheduler
from bga.report.text import format_sweep_text

GIB = 1024 ** 3
FIXTURE_RUN = "tests/fixtures/macro_micro/run"
FIXTURE_PLANE2 = "tests/fixtures/macro_micro/plane2.json"


def _bga(args):
    return subprocess.run(
        [sys.executable, "-c",
         f"from bga.cli import main; raise SystemExit(main({args!r}))"],
        capture_output=True, text=True)


def _task(uid, dur_us):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=dur_us,
    )


def _scheduler(count=8):
    """`count` independent, equal-cost tasks - one wave at capacity
    `count`, so the graph's own knee sits at the builder cap and never
    hides the memory ceiling behind a scheduling one."""
    tasks = [_task(f"w{i}.bst", 1_000_000) for i in range(count)]
    return ReplayScheduler(
        tasks, RunContext(resource_capacities={"PROCESS": count}))


def test_memory_binds_before_the_builder_cap():
    """The guard: each element peaks at 2 GiB, host RAM is 6.5 GiB -
    the sum crosses it at capacity 4 (8 GiB) while capacity 3 (6 GiB)
    still fits and the builder cap is 8."""
    peak_rss = {f"w{i}.bst": 2 * GIB for i in range(8)}
    result = _scheduler(8).capacity_sweep(
        resource="PROCESS", min_capacity=1, max_capacity=8,
        peak_rss_bytes=peak_rss, host_memory_bytes=int(6.5 * GIB),
    )
    assert result.knee_points["PROCESS"] == 8
    assert result.memory_knee_points["PROCESS"] == 3
    assert result.binding_constraints["PROCESS"] == {
        "name": "memory", "builders": 3}


def test_builder_bound_when_memory_never_binds():
    """The mirror: host RAM covers every swept capacity, so the graph's
    own knee is the tighter ceiling and is named."""
    peak_rss = {f"w{i}.bst": 2 * GIB for i in range(8)}
    result = _scheduler(8).capacity_sweep(
        resource="PROCESS", min_capacity=1, max_capacity=8,
        peak_rss_bytes=peak_rss, host_memory_bytes=32 * GIB,
    )
    assert result.memory_knee_points["PROCESS"] == 8
    assert result.binding_constraints["PROCESS"] == {
        "name": "builders", "builders": 8}


def test_no_measured_peak_leaves_the_sweep_unchanged():
    """Absent inputs never masquerade as an unbounded ceiling - no
    `memory_knee_points`/`binding_constraints` entry at all, and the
    graph knee is exactly what `capacity_sweep` reported before this
    item (`UX-30`)."""
    result = _scheduler(8).capacity_sweep(
        resource="PROCESS", min_capacity=1, max_capacity=8,
    )
    assert result.memory_knee_points == {}
    assert result.binding_constraints == {}
    assert result.knee_points["PROCESS"] == 8


def test_zero_fitting_builders_is_a_real_answer_not_an_absence():
    """Even one element's peak already exceeds host RAM: the memory cap
    is 0, published rather than dropped the way an unmeasured `knee`
    is - `0` and "no data" must stay distinguishable."""
    peak_rss = {f"w{i}.bst": 8 * GIB for i in range(8)}
    result = _scheduler(8).capacity_sweep(
        resource="PROCESS", min_capacity=1, max_capacity=8,
        peak_rss_bytes=peak_rss, host_memory_bytes=1 * GIB,
    )
    assert result.memory_knee_points["PROCESS"] == 0
    assert result.binding_constraints["PROCESS"] == {
        "name": "memory", "builders": 0}


def test_sweep_text_names_memory_as_the_bound():
    peak_rss = {f"w{i}.bst": 2 * GIB for i in range(8)}
    result = _scheduler(8).capacity_sweep(
        resource="PROCESS", min_capacity=1, max_capacity=8,
        peak_rss_bytes=peak_rss, host_memory_bytes=int(6.5 * GIB),
    )
    text = format_sweep_text("PROCESS", result)
    assert "Recommendation: memory-bound at 3 builder(s)" in text


def test_sweep_text_names_builders_as_the_bound():
    peak_rss = {f"w{i}.bst": 2 * GIB for i in range(8)}
    result = _scheduler(8).capacity_sweep(
        resource="PROCESS", min_capacity=1, max_capacity=8,
        peak_rss_bytes=peak_rss, host_memory_bytes=32 * GIB,
    )
    text = format_sweep_text("PROCESS", result)
    assert "Recommendation: builder-bound at 8 builder(s)" in text


def test_peak_rss_and_host_memory_needs_both_halves():
    """UX-678's CLI-side input gate: a measured peak RSS with no host
    memory total, or the reverse, is `(None, None)` rather than a
    partial join the sweep would silently read as complete."""
    from bga.cli import _peak_rss_and_host_memory

    native_report = {"peak_memory": {"per_element": {
        "core.bst": {"peak_rss_kb": 2_000_000}}}}
    host_samples = {"header": {"mem_total_kb": 8_000_000}}

    assert _peak_rss_and_host_memory(None, native_report) == (None, None)
    assert _peak_rss_and_host_memory(host_samples, None) == (None, None)
    assert _peak_rss_and_host_memory(host_samples, native_report) == (
        {"core.bst": 2_000_000 * 1024}, 8_000_000 * 1024)


def test_bga_sweep_plane2_runs_end_to_end_in_text():
    """The real CLI path: `_attach_plane2_capacity` now runs ahead of
    the format branch for both formats, and `_finish_capacity_
    recommendation` used to read `result.floors` on the ad-hoc holder
    `_produce_sweep_output` builds, which has no such attribute."""
    result = _bga(["sweep", FIXTURE_RUN, "--plane2", FIXTURE_PLANE2,
                   "--format", "text"])
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr, result.stderr
    assert "Capacity Sweep: PROCESS" in result.stdout


def test_bga_sweep_plane2_runs_end_to_end_in_json():
    """The mirror in JSON - the format this item's own reorder newly
    reached, since JSON used to return before `_attach_plane2_capacity`
    ever ran."""
    result = _bga(["sweep", FIXTURE_RUN, "--plane2", FIXTURE_PLANE2,
                   "--format", "json"])
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "sweep/v1"
    assert "memory_knee_points" in payload
    assert "binding_constraints" in payload
