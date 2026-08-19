"""UX-107: two record streams, one process list.

With `UX-106`'s spine running, every *dynamically*-linked process is
recorded twice - once by the ptrace spine and once by the LD_PRELOAD
hook - while a static process has only the spine's record. Measured on
`examples/06` before this join existed: 1635 spine records beside 1485
hook records, and a report claiming 1644 processes with their CPU time
counted twice.

These cover the join, the provenance it stamps on every entry, the
coverage arithmetic built on that, and the one property that matters
more than any of them: a capture taken before the spine existed must
parse into exactly what it always did.
"""
import copy
import os
import shutil

import pytest

from tools.bst_native_build_tracer import (
    COVERAGE_BOTH,
    COVERAGE_HOOK_ONLY,
    COVERAGE_SPINE_ONLY,
    CPU_RECONCILIATION_TOLERANCE_US,
    MERGE_START_TOLERANCE_S,
    compute_declared_vs_used,
    compute_element_opens_coverage,
    compute_stream_coverage,
    merge_record_streams,
    pair_events,
    parse_trace_log,
)


def _record(pid, src, start, *, invocation="inv-a", element="work.bst", **extra):
    record = {
        "pid": pid,
        "ppid": 1,
        "element": element,
        "invocation": invocation,
        "cmd": f"/bin/true {pid}",
        "start_ts": start,
        "end_ts": start + 1.0,
        "duration_s": 1.0,
        "open": False,
        "src": src,
    }
    record.update(extra)
    return record


class TestMergeStreams:
    def test_pre_spine_capture_passes_through_unchanged(self):
        """The property every old capture depends on: with no spine
        records, nothing is joined, nothing is dropped, and the only
        addition is the provenance that says so."""
        records = [_record(2, "hook", 1.0, cpu_us=1000),
                   _record(3, "hook", 2.0, cpu_us=2000)]
        before = copy.deepcopy(records)
        merged = merge_record_streams(records)

        assert len(merged) == 2
        assert [r["coverage"] for r in merged] == [COVERAGE_HOOK_ONLY] * 2
        for got, want in zip(merged, before):
            assert {k: v for k, v in got.items() if k != "coverage"} == want

    def test_the_double_count_this_task_exists_to_prevent(self):
        """One process, two records, one entry - and its CPU counted
        once. Summing the raw streams gives 3000us for a process that
        used 1500."""
        records = [
            _record(2, "spine", 1.000, cpu_us=1500),
            _record(2, "hook", 1.002, cpu_us=1500),
        ]
        merged = merge_record_streams(records)

        assert len(merged) == 1
        assert merged[0]["coverage"] == COVERAGE_BOTH
        assert sum(r["cpu_us"] for r in merged) == 1500

    def test_hook_contributes_only_what_it_alone_measures(self):
        records = [
            _record(2, "spine", 1.0, cpu_us=1500, max_rss_kb=900,
                    exit_status="exited:0"),
            _record(2, "hook", 1.001, cpu_us=1490, max_rss_kb=880,
                    children_cpu_us=42, children_max_rss_kb=77),
        ]
        entry, = merge_record_streams(records)

        # The lifecycle is the spine's: it starts at the kernel's
        # exec-stop and ends at the exit-stop, so it brackets the hook's
        # constructor and destructor on every one of 822 real pairs.
        assert entry["max_rss_kb"] == 900
        assert entry["exit_status"] == "exited:0"
        # The hook supplies the reaped-children figures ...
        assert entry["children_cpu_us"] == 42
        assert entry["children_max_rss_kb"] == 77
        # ... and the CPU time, which is the one field where its
        # measurement is the better of the two: `getrusage` resolves
        # microseconds where `/proc/<pid>/stat` truncates to 10ms ticks.
        assert entry["cpu_us"] == 1490
        assert entry["cpu_source"] == "hook"
        # Both survive as evidence, neither is added to or averaged with
        # the other (UX-53).
        assert entry["spine_cpu_us"] == 1500
        assert entry["hook_cpu_us"] == 1490
        assert entry["hook_max_rss_kb"] == 880

    def test_static_process_is_spine_only(self):
        records = [_record(2, "spine", 1.0), _record(3, "hook", 1.0)]
        by_pid = {r["pid"]: r for r in merge_record_streams(records)}

        assert by_pid[2]["coverage"] == COVERAGE_SPINE_ONLY
        assert by_pid[3]["coverage"] == COVERAGE_HOOK_ONLY

    def test_a_hook_record_the_spine_missed_survives_as_hook_only(self):
        """Not dropped, and not silently folded in: a process the spine
        did not see while the spine was running is itself a fact worth
        keeping."""
        records = [_record(2, "spine", 1.0), _record(9, "hook", 5.0)]
        merged = merge_record_streams(records)

        assert len(merged) == 2
        assert merged[-1]["pid"] == 9
        assert merged[-1]["coverage"] == COVERAGE_HOOK_ONLY

    def test_same_pid_in_different_sandboxes_does_not_cross_join(self):
        """Pids are namespaced per sandbox and every sandbox starts from
        the same small numbers, so the invocation id is what makes the
        pair unique."""
        records = [
            _record(2, "spine", 1.0, invocation="inv-a"),
            _record(2, "hook", 1.0, invocation="inv-b"),
        ]
        merged = merge_record_streams(records)

        assert len(merged) == 2
        assert {r["coverage"] for r in merged} == {
            COVERAGE_SPINE_ONLY, COVERAGE_HOOK_ONLY}

    def test_reused_pid_pairs_with_the_nearer_start(self):
        """One sandbox, one pid, two lifetimes. The join is on the START
        stamp, so the second exec does not steal the first's hook
        record."""
        records = [
            _record(2, "spine", 1.0, cpu_us=10),
            _record(2, "hook", 1.001, cpu_us=10),
            _record(2, "spine", 90.0, cpu_us=20),
            _record(2, "hook", 90.001, cpu_us=20),
        ]
        merged = merge_record_streams(records)

        assert len(merged) == 2
        assert [r["coverage"] for r in merged] == [COVERAGE_BOTH] * 2
        assert [r["cpu_us"] for r in merged] == [10, 20]

    def test_start_stamps_beyond_tolerance_are_different_processes(self):
        records = [
            _record(2, "spine", 1.0),
            _record(2, "hook", 1.0 + MERGE_START_TOLERANCE_S * 2),
        ]
        merged = merge_record_streams(records)

        assert len(merged) == 2
        assert {r["coverage"] for r in merged} == {
            COVERAGE_SPINE_ONLY, COVERAGE_HOOK_ONLY}

    def test_open_records_join_too(self):
        """A process killed before it could write an END has a START from
        each stream, and must still be one process."""
        spine = _record(2, "spine", 1.0)
        hook = _record(2, "hook", 1.002)
        for record in (spine, hook):
            record.update(open=True, end_ts=None, duration_s=None)
        merged = merge_record_streams([spine, hook])

        assert len(merged) == 1
        assert merged[0]["open"] is True

    def test_through_the_real_parser(self):
        """The same join, reached the way a capture reaches it: raw lines
        from both mechanisms in one log file."""
        log = "\n".join([
            "START pid=2 ppid=1 ts=1.000 element=work.bst inv=s1 src=spine "
            "cmd=/bin/gcc a.c",
            "START pid=2 ppid=1 ts=1.001 element=work.bst inv=s1 cmd=/bin/gcc a.c",
            "END pid=2 ppid=1 ts=3.000 element=work.bst inv=s1 src=spine "
            "utime=1.0 stime=0.5 maxrss_kb=2048 exit=exited:0 cmd=/bin/gcc a.c",
            "END pid=2 ppid=1 ts=3.001 element=work.bst inv=s1 utime=1.0 stime=0.5 "
            "cutime=0.1 cstime=0.0 maxrss_kb=2048 cmaxrss_kb=64 cmd=/bin/gcc a.c",
            "START pid=3 ppid=2 ts=1.500 element=work.bst inv=s1 src=spine "
            "cmd=/bin/busybox ls",
            "END pid=3 ppid=2 ts=1.900 element=work.bst inv=s1 src=spine "
            "utime=0.0 stime=0.1 maxrss_kb=512 exit=exited:0 cmd=/bin/busybox ls",
        ])
        merged = merge_record_streams(pair_events(parse_trace_log(log)))

        assert len(merged) == 2
        by_pid = {r["pid"]: r for r in merged}
        assert by_pid[2]["coverage"] == COVERAGE_BOTH
        assert by_pid[2]["cpu_us"] == 1_500_000
        assert by_pid[2]["children_cpu_us"] == 100_000
        assert by_pid[3]["coverage"] == COVERAGE_SPINE_ONLY
        assert "children_cpu_us" not in by_pid[3]
        # 1.5s + 0.1s, each counted once.
        assert sum(r["cpu_us"] for r in merged) == 1_600_000


class TestStreamCoverage:
    def test_counts_the_three_classes_and_the_opens_share(self):
        merged = merge_record_streams([
            _record(2, "spine", 1.0), _record(2, "hook", 1.001),
            _record(3, "spine", 2.0),
            _record(4, "spine", 3.0),
        ])
        coverage = compute_stream_coverage(merged)

        assert coverage["processes"] == 3
        assert coverage["by_coverage"] == {COVERAGE_BOTH: 1, COVERAGE_SPINE_ONLY: 2}
        assert coverage["opens_covered_processes"] == 1
        assert coverage["opens_coverage"] == pytest.approx(1 / 3)

    def test_cpu_measured_twice_is_a_free_test(self):
        """UX-53's pattern: `getrusage` at exit against `/proc/<pid>/stat`
        at the exit-stop. Agreement is reported as agreement; the point
        is that "we checked" and "we could not check" look different."""
        merged = merge_record_streams([
            _record(2, "spine", 1.0, cpu_us=1_000_000),
            _record(2, "hook", 1.001, cpu_us=1_000_000 + 5_000),
        ])
        coverage = compute_stream_coverage(merged)

        assert coverage["cpu_reconciled_processes"] == 1
        assert coverage["cpu_disagreement_count"] == 0

    def test_a_real_disagreement_is_named_not_averaged(self):
        merged = merge_record_streams([
            _record(2, "spine", 1.0, cpu_us=1_000_000),
            _record(2, "hook", 1.001, cpu_us=1_000_000
                    + CPU_RECONCILIATION_TOLERANCE_US * 4),
        ])
        coverage = compute_stream_coverage(merged)

        assert coverage["cpu_disagreement_count"] == 1
        worst, = coverage["cpu_disagreements"]
        assert worst["pid"] == 2
        assert worst["delta_us"] == CPU_RECONCILIATION_TOLERANCE_US * 4
        # Both figures survive; neither is replaced by their mean.
        assert worst["spine_cpu_us"] == 1_000_000
        assert worst["hook_cpu_us"] > worst["spine_cpu_us"]

    def test_a_process_seen_by_one_mechanism_cannot_be_reconciled(self):
        coverage = compute_stream_coverage(
            merge_record_streams([_record(2, "spine", 1.0, cpu_us=5)]))

        assert coverage["cpu_reconciled_processes"] == 0
        assert coverage["cpu_disagreement_count"] == 0


class TestElementOpensCoverage:
    def test_silent_without_a_second_stream(self):
        """No spine, no measurement - and a guess dressed as a
        measurement is exactly what this task removes."""
        merged = merge_record_streams([_record(2, "hook", 1.0)])

        assert compute_element_opens_coverage(merged) == {}

    def test_per_element_share(self):
        merged = merge_record_streams([
            _record(2, "spine", 1.0, element="dyn.bst"),
            _record(2, "hook", 1.001, element="dyn.bst"),
            _record(3, "spine", 2.0, element="mixed.bst", invocation="inv-b"),
            _record(3, "hook", 2.001, element="mixed.bst", invocation="inv-b"),
            _record(4, "spine", 2.5, element="mixed.bst", invocation="inv-b"),
            _record(5, "spine", 3.0, element="static.bst", invocation="inv-c"),
        ])
        coverage = compute_element_opens_coverage(merged)

        assert coverage["dyn.bst"]["opens_coverage"] == 1.0
        assert coverage["mixed.bst"]["opens_coverage"] == 0.5
        assert coverage["mixed.bst"]["spine_only"] == 1
        assert coverage["static.bst"]["opens_coverage"] == 0.0
        assert coverage["static.bst"]["processes"] == 1


class TestDeclaredVsUsedCoverage:
    """UX-46 computes over the processes the hook could enter. Saying
    which share that is turns "no unused dependencies" back into a claim
    with a scope."""

    DECLARED = {"work.bst": ["dep.bst"]}
    CONTENTS = {"dep.bst": {"/usr/include/a.h", "/usr/include/b.h", "/usr/lib/c.a"}}

    def test_an_all_static_element_is_uncovered_as_a_measurement(self):
        analysis = compute_declared_vs_used(
            {}, self.DECLARED, self.CONTENTS,
            opens_coverage={"work.bst": {
                "processes": 24, "opens_covered": 0, "spine_only": 24,
                "opens_coverage": 0.0}},
        )

        assert analysis["unused_candidates"] == []
        entry, = analysis["uncovered_elements"]
        assert entry["element"] == "work.bst"
        # Counted, not supposed: "0 of 24" rather than "it may be".
        assert "0 of 24 process(es)" in entry["reason"]
        assert "may be" not in entry["reason"]

    def test_partial_coverage_is_uncovered_by_the_same_rule_as_dropped_paths(self):
        """A process the hook never entered could have opened the very
        file this analysis is about to call unread - which is exactly why
        a truncated read set already made an element uncovered."""
        analysis = compute_declared_vs_used(
            {"work.bst": {"paths": {"/usr/include/z.h"}, "dropped": 0,
                          "processes": 5}},
            self.DECLARED, self.CONTENTS,
            opens_coverage={"work.bst": {
                "processes": 10, "opens_covered": 4, "spine_only": 6,
                "opens_coverage": 0.4}},
        )

        assert analysis["unused_candidates"] == []
        entry, = analysis["uncovered_elements"]
        assert "4 of 10 process(es) (40%)" in entry["reason"]

    def test_full_coverage_still_yields_candidates_with_the_share_stated(self):
        analysis = compute_declared_vs_used(
            {"work.bst": {"paths": {"/usr/include/z.h"}, "dropped": 0,
                          "processes": 7}},
            self.DECLARED, self.CONTENTS,
            opens_coverage={"work.bst": {
                "processes": 7, "opens_covered": 7, "spine_only": 0,
                "opens_coverage": 1.0}},
        )

        candidate, = analysis["unused_candidates"]
        assert candidate["dependency"] == "dep.bst"
        assert analysis["uncovered_elements"] == []
        assert analysis["opens_coverage"]["hook_covered_processes"] == 7
        assert analysis["opens_coverage"]["elements_fully_covered"] == 1

    def test_without_the_spine_the_analysis_is_exactly_what_it_was(self):
        opens = {"work.bst": {"paths": {"/usr/include/z.h"}, "dropped": 0,
                              "processes": 7}}
        before = compute_declared_vs_used(opens, self.DECLARED, self.CONTENTS)
        after = compute_declared_vs_used(
            opens, self.DECLARED, self.CONTENTS, opens_coverage={})

        assert before == after
        assert before["opens_coverage"] is None
        assert len(before["unused_candidates"]) == 1


class TestAggregateReconciliation:
    """A per-process tolerance cannot see a *systematic* offset. On a real
    `examples/06` capture 663 pairs each agreed to within one clock tick
    and still totalled 58.47s against 54.14s - 7.4% - because the hook's
    destructor runs before the process is finished."""

    def test_the_offset_every_pair_hides(self):
        merged = merge_record_streams([
            record
            for pid in range(2, 102)
            for record in (
                _record(pid, "spine", float(pid), cpu_us=1_000_000),
                _record(pid, "hook", pid + 0.001, cpu_us=960_000),
            )
        ])
        coverage = compute_stream_coverage(merged)

        # Every pair is inside the tolerance ...
        assert coverage["cpu_disagreement_count"] == 0
        # ... and the totals are 4% apart, in the direction the mechanism
        # predicts: the spine reads later, so it reads more.
        aggregate = coverage["cpu_aggregate"]
        assert aggregate["processes"] == 100
        assert aggregate["delta_us"] == 100 * 40_000
        # Against the hook's total: 4.0s of 96.0s, the figure actually used.
        assert aggregate["delta_pct"] == pytest.approx(40_000 / 960_000 * 100)

    def test_absent_when_nothing_was_measured_twice(self):
        coverage = compute_stream_coverage(
            merge_record_streams([_record(2, "spine", 1.0, cpu_us=5)]))

        assert coverage["cpu_aggregate"] is None


class TestPairingKeepsTheStreamsApart:
    """`pair_events` pairs a START with an END per `(invocation, pid)`.
    With both mechanisms writing, that key alone pops the spine's START
    for the hook's END and vice versa - and the process count, the
    coverage classes and the durations all still look right, so nothing
    downstream notices. Measured on a real `examples/07` capture: pid 9's
    `cc1plus` reported `utime=0.013204` under `src=spine`, a resolution
    `/proc/<pid>/stat` cannot produce."""

    LOG = "\n".join([
        "START pid=9 ppid=8 ts=100.100 element=base.bst inv=a src=spine cmd=cc1plus",
        "START pid=9 ppid=8 ts=100.106 element=base.bst inv=a cmd=cc1plus",
        # The hook's destructor runs first, with microsecond rusage ...
        "END pid=9 ppid=8 ts=100.190 element=base.bst inv=a utime=0.013204 "
        "stime=0.017606 cutime=0.001000 cstime=0.000000 maxrss_kb=20432 "
        "cmaxrss_kb=0 cmd=cc1plus",
        # ... and the kernel's exit-stop after it, with whole ticks.
        "END pid=9 ppid=8 ts=100.191 element=base.bst inv=a utime=0.010000 "
        "stime=0.010000 maxrss_kb=20700 exit=0 src=spine cmd=cc1plus",
    ])

    def test_each_record_keeps_its_own_measurement(self):
        by_src = {r["src"]: r for r in pair_events(parse_trace_log(self.LOG))}

        assert by_src["spine"]["cpu_us"] == 20_000
        assert by_src["spine"]["exit_status"] == "0"
        assert by_src["hook"]["cpu_us"] == 30_810
        assert "exit_status" not in by_src["hook"]

    def test_and_the_merged_entry_prefers_the_finer_one(self):
        entry, = merge_record_streams(pair_events(parse_trace_log(self.LOG)))

        assert entry["coverage"] == COVERAGE_BOTH
        assert entry["cpu_us"] == 30_810
        assert entry["cpu_source"] == "hook"
        assert entry["spine_cpu_us"] == 20_000
        # The lifecycle is the spine's, which brackets the hook's own.
        assert entry["start_ts"] == 100.100
        assert entry["end_ts"] == 100.191
        assert entry["exit_status"] == "0"


class TestCpuProvenance:
    def test_a_static_process_keeps_the_truncated_figure_and_is_counted(self):
        """Nothing finer exists for it, so the figure stands - and the
        count of processes it applies to is published, because a build
        made of short static processes has a CPU total that is a lower
        bound and must not read as exact."""
        merged = merge_record_streams([
            _record(2, "spine", 1.0, cpu_us=0),
            _record(3, "spine", 2.0, cpu_us=10_000),
        ])

        assert [r["cpu_source"] for r in merged] == ["spine", "spine"]
        assert compute_stream_coverage(merged)["cpu_from_spine_only"] == 2

    def test_a_hook_record_the_spine_missed_has_no_source_of_its_own(self):
        merged = merge_record_streams([
            _record(2, "spine", 1.0, cpu_us=10_000),
            _record(9, "hook", 5.0, cpu_us=1_234),
        ])
        by_pid = {r["pid"]: r for r in merged}

        assert by_pid[9]["cpu_us"] == 1_234
        assert "cpu_source" not in by_pid[9]
        assert compute_stream_coverage(merged)["cpu_from_spine_only"] == 1


BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_a_static_build_reports_itself_unmeasurable_rather_than_clean(tmp_path):
    """UX-107's acceptance on `examples/01-resource-contention`, whose
    every build command is static busybox.

    The dangerous output here is not a wrong number, it is a *confident*
    one: with no opens observed, declared-vs-used must say it could not
    look rather than report no unused dependencies. Run against a real
    build because the claim is about a real build's report.
    """
    from tools.bst_native_build_tracer import load_and_summarize, run_traced_build
    from tests.unit._bst_env import isolated_bst_env

    project = os.path.join(REPO_ROOT, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(project, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01's runtime is not staged - run examples/stage_runtimes.sh")

    home = tmp_path / "home"
    home.mkdir()
    raw = tmp_path / "dual.log"
    previous = dict(os.environ)
    os.environ.update(isolated_bst_env(home))
    try:
        code = run_traced_build(
            project, ["bst", "--no-colors", "build", "all.bst"], str(raw),
            trace_spine=True,
        )
        report = load_and_summarize(str(raw), project_dir=project)
    finally:
        os.environ.clear()
        os.environ.update(previous)

    assert code == 0
    coverage = report["stream_coverage"]
    # Every process, and every one of them invisible to the hook.
    assert set(coverage["by_coverage"]) == {COVERAGE_SPINE_ONLY}
    assert coverage["opens_coverage"] == 0.0
    assert coverage["cpu_from_spine_only"] == coverage["processes"]

    analysis = report["declared_vs_used"]
    assert analysis["available"] is True
    assert analysis["unused_candidates"] == []
    uncovered = {e["element"]: e["reason"] for e in analysis["uncovered_elements"]}
    assert uncovered, "every element here is unmeasurable and none said so"
    for reason in uncovered.values():
        assert "process(es) run for this element were reachable" in reason
    assert analysis["opens_coverage"]["hook_covered_processes"] == 0
