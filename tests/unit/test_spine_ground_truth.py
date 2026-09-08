"""UX-108: the spine, checked against answers that are known in advance.

`examples/01-resource-contention` runs `sleep 3` and nothing else, eight
times in parallel, through static busybox. That makes it the one fixture
where Plane 2's numbers can be checked against arithmetic rather than
against themselves: ~0 CPU over ~3s wall, and eight elements doing
identical work must measure identically.

It is also the project whose Plane 2 capture was empty for as long as
Plane 2 existed, so none of this could be asked before `UX-106`.
"""
import os
import shutil
import time

import pytest

from tools.bst_native_build_tracer import (
    COVERAGE_SPINE_ONLY,
    # `UX-297`: the per-process rows live in the raw log now, not in the
    # report - which carries the reductions over them. This file is one
    # of the two callers that genuinely wants the rows, because it
    # checks them against arithmetic.
    load_records,
)

BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The `sleep 3` the elements run. UX-741: a `sleep` cannot finish early
# under any load, and cannot outrun the harness's own clock around the
# whole build - so the bound is `SLEEP_S <= duration_s <= harness span`,
# never a symmetric tolerance on a nominal (both sides stretch under
# contention; a fixed window round-trips through pass and fail as load
# changes, which a one-sided bound and an enclosing bound do not).
SLEEP_S = 3.0
# `sleep` uses no CPU. The spine reads `/proc/<pid>/stat`, which reports
# whole 10ms ticks, so "zero" means "below a couple of ticks" - measured
# at exactly 0 on every one of 24 processes.
IDLE_CPU_US = 30_000
# UX-797: 20 bare runs at organic load 9.5-14.6 (no hogs, box already
# loaded), max(durations)-min(durations) per run: 0.0078-0.0627s (see
# the task file's Outcome for all 20) - 2x the observed max (0.1254s),
# rounded up. Catches a sleeper stalled beyond that margin; it does not
# catch one stalled inside it (measured, not typed - so it cannot).
WALL_SPREAD_S = 0.13
# UX-741: Plane 1's per-element lag from Plane 2 is UX-110's axis, out
# of scope here - this only checks the two planes name the same element,
# their intervals overlap, and Plane 2 stays inside the harness's own
# enclosing span (both hold at any load; the lag's *size* does not).


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_the_spine_measures_sleep_3_as_three_seconds_of_nothing(tmp_path):
    """The known answer, and the self-consistency it implies."""
    from tests.unit._bst_env import isolated_bst_env
    from tools.bst_native_build_tracer import run_traced_build

    project = os.path.join(REPO_ROOT, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(project, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01 is not staged - run examples/stage_runtimes.sh")

    home = tmp_path / "home"
    home.mkdir()
    raw = tmp_path / "spine.log"
    plane1 = tmp_path / "plane1.log"
    previous = dict(os.environ)
    os.environ.update(isolated_bst_env(home))
    # UX-741: the enclosing bound - nothing the spine reports for one
    # process can exceed the harness's own wall clock around the whole
    # `bst build` that drove it, at any load.
    harness_start = time.monotonic()
    try:
        code = run_traced_build(
            project, ["bst", "--no-colors", "--builders", "2", "build", "all.bst"],
            str(raw), wrapped_log_path=str(plane1), trace_spine=True,
        )
        records = load_records(str(raw))
    finally:
        os.environ.clear()
        os.environ.update(previous)
    harness_span = time.monotonic() - harness_start

    assert code == 0
    assert records, "the spine saw nothing on a build that ran 8 real commands"
    assert {r["coverage"] for r in records} == {COVERAGE_SPINE_ONLY}

    # 1. The known answer. Every element runs one `sleep 3`, and the
    #    process that runs it must show the wall clock of a sleep and the
    #    CPU time of one - which is none.
    work = [r for r in records if r["element"].startswith("work-")]
    assert work, "no work-*.bst element was attributed a process"
    sleepers = {}
    for record in work:
        if record["duration_s"] is None:
            continue
        longest = sleepers.get(record["element"])
        if longest is None or record["duration_s"] > longest["duration_s"]:
            sleepers[record["element"]] = record
    assert len(sleepers) == 8, f"expected 8 work elements, got {sorted(sleepers)}"
    for element, record in sorted(sleepers.items()):
        assert record["duration_s"] >= SLEEP_S, (
            f"{element}: {record['duration_s']:.3f}s for a `sleep 3` "
            "- a sleep cannot finish early"
        )
        assert record["duration_s"] <= harness_span, (
            f"{element}: {record['duration_s']:.3f}s exceeds the harness's "
            f"own {harness_span:.3f}s span driving the whole build"
        )
        assert record.get("cpu_us", 0) <= IDLE_CPU_US, (
            f"{element}: {record['cpu_us']}us of CPU for a process that slept"
        )

    # 2a. Eight elements doing identical work measure identically on CPU
    #     time, which no load moves - catches a sleeper that burned CPU
    #     while still under the per-element IDLE_CPU_US bound.
    cpu_by_element = {element: r.get("cpu_us", 0) for element, r in sleepers.items()}
    lo_element = min(cpu_by_element, key=cpu_by_element.get)
    hi_element = max(cpu_by_element, key=cpu_by_element.get)
    spread = cpu_by_element[hi_element] - cpu_by_element[lo_element]
    assert spread < IDLE_CPU_US, (
        f"{hi_element}: {cpu_by_element[hi_element]}us of CPU spreads "
        f"{spread}us from {lo_element}'s {cpu_by_element[lo_element]}us "
        "- not identical work"
    )

    # 2b. And on wall clock, against WALL_SPREAD_S (measured above) -
    #     catches a sleeper stalled well past its siblings while still
    #     inside the per-element SLEEP_S/harness_span bounds and idle on
    #     CPU, which 2a cannot see.
    dur_by_element = {element: r["duration_s"] for element, r in sleepers.items()}
    lo_d = min(dur_by_element, key=dur_by_element.get)
    hi_d = max(dur_by_element, key=dur_by_element.get)
    wall_spread = dur_by_element[hi_d] - dur_by_element[lo_d]
    assert wall_spread < WALL_SPREAD_S, (
        f"{hi_d}: {dur_by_element[hi_d]:.3f}s spreads {wall_spread:.3f}s "
        f"from {lo_d}'s {dur_by_element[lo_d]:.3f}s - not identical work"
    )


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_the_two_planes_agree_on_how_long_each_element_took(tmp_path):
    """One build, both planes, per-element intervals compared.

    UX-741: agreement is expressed as what holds at any load - the two
    planes name the same element, their intervals overlap, and Plane 2
    stays inside the harness's own enclosing span - not as a magnitude
    both planes stretch under contention (`PLANE_AGREEMENT_S` did, and
    reddened on the *short* side under load; see the task file). The
    lag's size is UX-110's axis, not this clause's.
    """
    from tests.unit._bst_env import isolated_bst_env
    from tools.bst_native_build_tracer import build_spans_from_wrapped_log, run_traced_build

    project = os.path.join(REPO_ROOT, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(project, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01 is not staged - run examples/stage_runtimes.sh")

    home = tmp_path / "home"
    home.mkdir()
    raw = tmp_path / "spine.log"
    plane1 = tmp_path / "plane1.log"
    previous = dict(os.environ)
    os.environ.update(isolated_bst_env(home))
    # Plane 1's spans are wall-clock, Plane 2's are `CLOCK_MONOTONIC`
    # (UX-185's `bga-clocks` anchor pattern) - this pair translates one
    # onto the other so their intervals can be compared directly.
    harness_wall_before = time.time()
    harness_mono_before = time.monotonic()
    try:
        code = run_traced_build(
            project, ["bst", "--no-colors", "--builders", "2", "build", "all.bst"],
            str(raw), wrapped_log_path=str(plane1), trace_spine=True,
        )
        records = load_records(str(raw))
    finally:
        os.environ.clear()
        os.environ.update(previous)
    harness_span = time.monotonic() - harness_mono_before

    assert code == 0
    spans = {s["element"]: s for s in build_spans_from_wrapped_log(str(plane1))}
    assert spans, "Plane 1 produced no build spans from the wrapped log"

    by_element = {}
    for record in records:
        if record["end_ts"] is None:
            continue
        window = by_element.setdefault(
            record["element"], [record["start_ts"], record["end_ts"]])
        window[0] = min(window[0], record["start_ts"])
        window[1] = max(window[1], record["end_ts"])

    compared = 0
    for element, (start, end) in sorted(by_element.items()):
        plane1_span = spans.get(element)
        if plane1_span is None:
            continue
        compared += 1
        p1_start = harness_mono_before + (plane1_span["start"] - harness_wall_before)
        p1_end = harness_mono_before + (plane1_span["end"] - harness_wall_before)
        assert p1_start <= end and start <= p1_end, (
            f"{element}: Plane 2 [{start:.3f}, {end:.3f}] does not overlap "
            f"Plane 1 [{p1_start:.3f}, {p1_end:.3f}] - UX-110, not this clause"
        )
        assert (end - start) <= harness_span, (
            f"{element}: Plane 2 {(end - start):.3f}s exceeds the harness's "
            f"own {harness_span:.3f}s span driving the whole build"
        )
    assert compared >= 8, f"only {compared} element(s) had spans in both planes"
