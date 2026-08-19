"""UX-123: three record-level defects, none build-breaking, each quietly
distorting the data.

The largest by far: `sh -c "gcc …"` execs in place, so one pid produces
N STARTs and one END. Pairing the END with the *first* START billed the
pid's whole CPU, peak RSS and exit status to the **pre-exec** image.
Measured on freedesktop-sdk: 7,384 records misfiled that way, including
`sh -c -e python -P -mbuild …` carrying 195,219us that `python` spent.
"""
from tools.bst_native_build_tracer import (
    MERGE_START_TOLERANCE_S,
    count_fork_only_exits,
    count_unmatched_ends,
    merge_record_streams,
    pair_events,
    parse_trace_log,
)


def _events(*lines):
    return parse_trace_log("\n".join(lines))


class TestOnePidIsOneProcess:
    LOG = (
        "START pid=9 ppid=1 ts=100.0 element=e.bst inv=a src=spine cmd=sh -c -e gcc a.c",
        "START pid=9 ppid=1 ts=100.1 element=e.bst inv=a src=spine cmd=gcc a.c",
        "START pid=9 ppid=1 ts=100.2 element=e.bst inv=a src=spine cmd=cc1 a.c",
        "END pid=9 ppid=1 ts=104.0 element=e.bst inv=a src=spine "
        "utime=3.0 stime=0.5 maxrss_kb=2048 exit=0 cmd=cc1 a.c",
    )

    def test_the_chain_collapses_into_one_record(self):
        records = pair_events(_events(*self.LOG))

        assert len(records) == 1
        assert records[0]["exec_chain"] == 3

    def test_named_for_the_last_image_and_spanning_the_whole_life(self):
        """`/proc/<pid>/stat` and `getrusage` are both per-*pid* and
        cumulative across execs, so the figures belong to the process
        rather than to any one of its images - and the last image is what
        a profiler means by "the process"."""
        record, = pair_events(_events(*self.LOG))

        assert record["cmd"] == "cc1 a.c"          # not `sh -c -e gcc a.c`
        assert record["start_ts"] == 100.0         # ...but the whole lifetime
        assert record["end_ts"] == 104.0
        assert record["cpu_us"] == 3_500_000
        assert record["exit_status"] == "0"

    def test_and_the_surplus_stops_counting_as_an_unobserved_exit(self):
        """The two earlier images used to be reported as processes that
        never exited. Measured on the freedesktop-sdk head: 37 -> 16."""
        records = pair_events(_events(*self.LOG))

        assert [r["open"] for r in records] == [False]

    def test_an_ordinary_process_is_untouched(self):
        records = pair_events(_events(
            "START pid=2 ppid=1 ts=1.0 element=e.bst inv=a src=spine cmd=true",
            "END pid=2 ppid=1 ts=2.0 element=e.bst inv=a src=spine "
            "utime=0.1 stime=0.0 exit=0 cmd=true",
        ))

        assert len(records) == 1
        assert records[0]["exec_chain"] == 1
        assert records[0]["cmd"] == "true"


class TestForkWithoutExec:
    def test_an_exit_for_a_pid_that_never_exec_d_is_counted_not_listed(self):
        """`PTRACE_EVENT_EXIT` fires for every tracee, including a
        fork-without-exec child - which is the same program as its parent
        and wears the parent's cmdline. Dropped from the process list and
        counted, because a record class that is neither shown nor
        mentioned is indistinguishable from one that never happened."""
        events = _events(
            "START pid=2 ppid=1 ts=1.0 element=e.bst inv=a src=spine cmd=sh -c gcc",
            "END pid=3 ppid=2 ts=1.5 element=e.bst inv=a src=spine "
            "utime=0.0 stime=0.0 exit=0 cmd=sh -c gcc",
            "END pid=2 ppid=1 ts=2.0 element=e.bst inv=a src=spine "
            "utime=0.1 stime=0.0 exit=0 cmd=sh -c gcc",
        )

        assert count_fork_only_exits(events) == 1
        assert [r["pid"] for r in pair_events(events)] == [2]

    def test_zero_is_reported_as_zero(self):
        """"None occurred" and "none were looked for" have to look
        different, which is why this is a count rather than a warning."""
        assert count_fork_only_exits(_events(
            "START pid=2 ppid=1 ts=1.0 element=e.bst inv=a src=spine cmd=true",
            "END pid=2 ppid=1 ts=2.0 element=e.bst inv=a src=spine "
            "utime=0.0 stime=0.0 exit=0 cmd=true",
        )) == 0


class TestTheJoinTakesTheNearestNotTheFirst:
    def test_a_recycled_pid_cannot_capture_a_later_record(self):
        """A `--unshare-pid` sandbox recycles small pids quickly - this
        repository's own tests assert that it does - so a stale unmatched
        hook record could capture a later spine record simply by being
        first in the list."""
        def _record(pid, src, start, cmd):
            return {
                "pid": pid, "ppid": 1, "element": "e.bst", "invocation": "a",
                "cmd": cmd, "start_ts": start, "end_ts": start + 0.1,
                "duration_s": 0.1, "open": False, "src": src, "exec_chain": 1,
            }

        tolerance = MERGE_START_TOLERANCE_S
        merged = merge_record_streams([
            # Two hook records for one recycled pid, the stale one first.
            _record(2, "hook", 10.0, "the earlier holder"),
            _record(2, "hook", 10.0 + tolerance * 0.9, "the one that matches"),
            _record(2, "spine", 10.0 + tolerance * 0.9, "the one that matches"),
        ])
        joined = [r for r in merged if r["coverage"] == "spine+hook"]

        assert len(joined) == 1
        assert joined[0]["start_ts"] == 10.0 + tolerance * 0.9


# --- UX-133: the edges UX-123's fixes left ------------------------------

class TestPidReuseDoesNotFabricateAProcess:
    """`pending.clear()` collapsed whatever was queued for a pid. If an
    END went missing and the pid was then reused, the next END produced
    **one** record spanning two distinct processes, wearing
    `exec_chain=2` as though it were an ordinary chain - the same
    quantity UX-123 introduced to make collapses visible, silently
    reporting a merge that is not one.

    `execve` cannot change a process's parent, so a START whose ppid
    differs from the open chain's is proof of a different process.
    """

    LOG = (
        "START pid=9 ppid=1 ts=100.0 element=e.bst inv=a src=spine cmd=first",
        # …no END for pid 9; killed, or the log was truncated here.
        "START pid=9 ppid=7 ts=200.0 element=e.bst inv=a src=spine cmd=second",
        "END pid=9 ppid=7 ts=201.0 element=e.bst inv=a src=spine "
        "utime=1.0 stime=0.0 maxrss_kb=1024 exit=0 cmd=second",
    )

    def test_two_processes_stay_two_records(self):
        records = pair_events(_events(*self.LOG))

        assert len(records) == 2, records
        assert sorted(r["cmd"] for r in records) == ["first", "second"]

    def test_neither_record_spans_both_lifetimes(self):
        """The fabricated record ran 100.0 -> 201.0, a 101-second
        "process" out of two that lived a fraction of that."""
        records = pair_events(_events(*self.LOG))
        closed = [r for r in records if not r["open"]]

        assert [r["duration_s"] for r in closed] == [1.0]

    def test_the_lost_end_is_labelled_rather_than_merged(self):
        records = pair_events(_events(*self.LOG))
        lost = next(r for r in records if r["open"])

        assert lost["cmd"] == "first"
        assert lost["open_reason"] == "end-lost-pid-reused"
        assert lost["duration_s"] is None

    def test_a_real_exec_chain_is_still_collapsed(self):
        """The discriminator has to leave UX-123's fix alone: an exec in
        place keeps the parent, so the chain stays one process."""
        records = pair_events(_events(
            "START pid=9 ppid=1 ts=100.0 element=e.bst inv=a src=spine cmd=sh -c gcc",
            "START pid=9 ppid=1 ts=100.1 element=e.bst inv=a src=spine cmd=gcc",
            "END pid=9 ppid=1 ts=104.0 element=e.bst inv=a src=spine "
            "utime=3.0 stime=0.5 maxrss_kb=2048 exit=0 cmd=gcc",
        ))

        assert len(records) == 1
        assert records[0]["exec_chain"] == 2
        assert records[0]["cmd"] == "gcc"

    def test_an_ordinary_open_record_keeps_its_own_reason(self):
        """A START with no END at all is the common case - killed by a
        signal, or still running when the capture stopped - and must not
        be relabelled as a pid reuse."""
        records = pair_events(_events(
            "START pid=9 ppid=1 ts=100.0 element=e.bst inv=a src=spine cmd=lonely",
        ))

        assert records[0]["open_reason"] == "no-observed-exit"


class TestUnmatchedEndsAreCountedForWhatTheyAre:
    def test_a_reused_pid_no_longer_hides_a_fork_only_exit(self):
        """`seen_start` was never cleared, so an exec -> exit ->
        reused-as-fork-only pid had its second END matched against the
        first process's START and went uncounted."""
        counts = count_unmatched_ends(_events(
            "START pid=9 ppid=1 ts=100.0 element=e.bst inv=a src=spine cmd=first",
            "END pid=9 ppid=1 ts=101.0 element=e.bst inv=a src=spine "
            "utime=1.0 stime=0.0 maxrss_kb=1024 exit=0 cmd=first",
            # pid 9 comes back as a fork-without-exec child: an exit, no start.
            "END pid=9 ppid=1 ts=102.0 element=e.bst inv=a src=spine "
            "utime=0.0 stime=0.0 maxrss_kb=512 exit=0 cmd=first",
        ))

        assert counts["fork_only"] == 1

    def test_a_hook_orphan_is_not_called_a_fork_only_child(self):
        """Only the spine sees a fork-without-exec exit: the hook is
        loaded *by* the linker at exec, so it cannot be present in a
        process that never exec'd. A hook END with no START is a
        truncated log, and saying otherwise states something the record
        cannot support."""
        counts = count_unmatched_ends(_events(
            "END pid=9 ppid=1 ts=102.0 element=e.bst inv=a src=hook "
            "utime=0.0 stime=0.0 maxrss_kb=512 exit=0 cmd=orphan",
        ))

        assert counts == {"fork_only": 0, "unmatched": 1}

    def test_the_spine_orphan_is_still_a_fork_only_child(self):
        counts = count_unmatched_ends(_events(
            "END pid=9 ppid=1 ts=102.0 element=e.bst inv=a src=spine "
            "utime=0.0 stime=0.0 maxrss_kb=512 exit=0 cmd=parent-cmdline",
        ))

        assert counts == {"fork_only": 1, "unmatched": 0}

    def test_the_old_entry_point_still_answers_its_own_question(self):
        """`count_fork_only_exits` has callers; it is now the spine half
        of the pair rather than the whole of it."""
        events = _events(
            "END pid=9 ppid=1 ts=102.0 element=e.bst inv=a src=spine "
            "utime=0.0 stime=0.0 maxrss_kb=512 exit=0 cmd=x",
            "END pid=8 ppid=1 ts=103.0 element=e.bst inv=a src=hook "
            "utime=0.0 stime=0.0 maxrss_kb=512 exit=0 cmd=y",
        )

        assert count_fork_only_exits(events) == 1
