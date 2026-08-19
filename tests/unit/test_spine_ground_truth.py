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

import pytest

from tools.bst_native_build_tracer import (
    COVERAGE_SPINE_ONLY,
    load_and_summarize,
)

BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The `sleep 3` the elements run. Generous on the upper side because a
# loaded runner delays the process's own teardown, and tight on the lower
# side because nothing can make a `sleep 3` finish early.
SLEEP_S = 3.0
SLEEP_TOLERANCE_S = 0.5
# `sleep` uses no CPU. The spine reads `/proc/<pid>/stat`, which reports
# whole 10ms ticks, so "zero" means "below a couple of ticks" - measured
# at exactly 0 on every one of 24 processes.
IDLE_CPU_US = 30_000
# UX-108: how far Plane 1's per-element task span may sit from the
# spine's. Measured on a real build: six of eight elements agree to 7ms,
# and two disagree by 0.32s - Plane 1's wrapped log is stamped when the
# wrapper *reads* a line, and BuildStream flushes in bursts. Filed as
# UX-110; the tolerance here is what lets this assert the agreement that
# does hold without asserting the lag away.
PLANE_AGREEMENT_S = 1.0


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_the_spine_measures_sleep_3_as_three_seconds_of_nothing(tmp_path):
    """The known answer, and the self-consistency it implies."""
    from tools.bst_native_build_tracer import run_traced_build
    from tests.unit._bst_env import isolated_bst_env

    project = os.path.join(REPO_ROOT, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(project, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01's runtime is not staged - run examples/stage_runtimes.sh")

    home = tmp_path / "home"
    home.mkdir()
    raw = tmp_path / "spine.log"
    plane1 = tmp_path / "plane1.log"
    previous = dict(os.environ)
    os.environ.update(isolated_bst_env(home))
    try:
        code = run_traced_build(
            project, ["bst", "--no-colors", "--builders", "2", "build", "all.bst"],
            str(raw), wrapped_log_path=str(plane1), trace_spine=True,
        )
        report = load_and_summarize(str(raw))
    finally:
        os.environ.clear()
        os.environ.update(previous)

    assert code == 0
    records = report["processes"]
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
        assert abs(record["duration_s"] - SLEEP_S) < SLEEP_TOLERANCE_S, (
            f"{element}: {record['duration_s']:.3f}s for a `sleep 3`"
        )
        assert record.get("cpu_us", 0) <= IDLE_CPU_US, (
            f"{element}: {record['cpu_us']}us of CPU for a process that slept"
        )

    # 2. Eight elements doing identical work measure identically. This is
    #    what makes the numbers above a measurement rather than a
    #    coincidence - and it is the property Plane 1 does not have here.
    durations = [r["duration_s"] for r in sleepers.values()]
    assert max(durations) - min(durations) < 0.1, sorted(durations)


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_the_two_planes_agree_on_how_long_each_element_took(tmp_path):
    """One build, both planes, per-element durations compared.

    The task asks for the spine's spans to bracket Plane 1's task spans.
    They do not, in either direction, and the reason is Plane 1's rather
    than the spine's: its wrapped log is stamped when the wrapper reads a
    line, and BuildStream flushes in bursts, so two of eight identical
    elements came out 0.32s short of the `sleep 3` they ran. Agreement
    within a stated tolerance is what can honestly be asserted, and the
    disagreement itself is UX-110.
    """
    from tools.bst_native_build_tracer import build_spans_from_wrapped_log, run_traced_build
    from tests.unit._bst_env import isolated_bst_env

    project = os.path.join(REPO_ROOT, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(project, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01's runtime is not staged - run examples/stage_runtimes.sh")

    home = tmp_path / "home"
    home.mkdir()
    raw = tmp_path / "spine.log"
    plane1 = tmp_path / "plane1.log"
    previous = dict(os.environ)
    os.environ.update(isolated_bst_env(home))
    try:
        code = run_traced_build(
            project, ["bst", "--no-colors", "--builders", "2", "build", "all.bst"],
            str(raw), wrapped_log_path=str(plane1), trace_spine=True,
        )
        report = load_and_summarize(str(raw))
    finally:
        os.environ.clear()
        os.environ.update(previous)

    assert code == 0
    spans = {
        s["element"]: s["end"] - s["start"]
        for s in build_spans_from_wrapped_log(str(plane1))
    }
    assert spans, "Plane 1 produced no build spans from the wrapped log"

    by_element = {}
    for record in report["processes"]:
        if record["end_ts"] is None:
            continue
        window = by_element.setdefault(
            record["element"], [record["start_ts"], record["end_ts"]])
        window[0] = min(window[0], record["start_ts"])
        window[1] = max(window[1], record["end_ts"])

    compared = 0
    for element, (start, end) in sorted(by_element.items()):
        plane1_duration = spans.get(element)
        if plane1_duration is None:
            continue
        compared += 1
        assert abs((end - start) - plane1_duration) < PLANE_AGREEMENT_S, (
            f"{element}: Plane 2 {(end - start):.3f}s against Plane 1 "
            f"{plane1_duration:.3f}s"
        )
    assert compared >= 8, f"only {compared} element(s) had spans in both planes"
