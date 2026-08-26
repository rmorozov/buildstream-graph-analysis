"""UX-297: parsing and pairing are one pass, and it holds no events.

The read half of `UX-297` landed in round 39 and left one clause open:
extraction still materialized the whole event list, because
`pair_events` sorted it globally before pairing. This file guards the
pass that replaced it.

**The property the sort was buying, and the weaker one that is true.**
Pairing needs a key's own events in order - a key being one process
seen through one mechanism (`_pair_key`), whose START and END are
written by one writer in that order. A *global* sort is far stronger,
and it is what forced the list to exist. Measured on the two real
captures this repository carries:

```text
                      events   keys   global inv.   per-key inv.
examples/01 raw           64     40             0              0
examples/06 plane2.gz   1485    813             2              0
```

`examples/06` is the discriminating case: the file is **not** globally
ordered and **is** per-key ordered, so the weaker property is the one
that actually holds on a real capture. The clauses below assert both
halves - that the streaming pass agrees with the sorting one
record-for-record, and that the input it agreed on was genuinely out of
global order, so the agreement is evidence rather than a tautology.

**What it bought**, end to end on a generated 200,000-process trace
(`load_and_summarize`, same file, worktree at the pre-change commit
against this tree):

```text
                   before      after
peak RSS          288.3 MB   259.5 MB
wall               8.2 s      7.1 s
report digest   b7e6c5f4f1798c9e - identical
```

and inside one extraction, where the plateau moved:

```text
                        before     after
events parsed          247.4 MB      -      (400,000 dicts, never built now)
records paired         249.0 MB   221.1 MB
folded, records freed   46.1 MB    42.8 MB
```

The remaining floor is the record list itself - 185.8 MB of the 221.1
here - which `merge_record_streams` joins whole and which the start
order every downstream reader sees is sorted from. That is
`O(processes)`, not `O(events)`, and windowing it is a different
question with a different measurement behind it (`UX-313`).
"""
import gzip
import os
import random
import subprocess
import sys

import pytest

from tools.bst_native_build_tracer import (
    _pair_key,
    count_unmatched_ends,
    pair_events,
    parse_trace_lines,
    stream_records,
    stream_trace_events,
)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# **Both of these are gitignored.** They exist on this machine and not
# in a clone, so the clauses that read them are skipped where they are
# absent - the measurements in this file's header came from them and are
# worth having exactly, but a guard whose only data is an untracked path
# passes locally and fails in CI before an assertion runs.
#
# The paths are written as whole strings rather than assembled from
# `os.path.join` fragments, deliberately:
# `test_a_guard_reads_only_what_a_clone_has.py` scans test files for
# path-like literals, and a path split across `join` arguments is
# invisible to it. That is how this file got past it - and the guard now
# reads fragments too, so the next one does not.
RAW_CAPTURE = os.path.join(
    REPO_ROOT,
    "examples/01-resource-contention/.bga/tmp/trace-qmy4cnf0/bind/trace.log")
GZ_CAPTURE = os.path.join(
    REPO_ROOT,
    "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z"
    "/plane2.log.gz")


def _needs(path):
    return pytest.mark.skipif(not os.path.exists(path),
                              reason="no real capture in this tree")


CAPTURES = [
    pytest.param(RAW_CAPTURE, open, id="examples-01-raw",
                 marks=_needs(RAW_CAPTURE)),
    pytest.param(GZ_CAPTURE, lambda p: gzip.open(p, "rt", errors="ignore"),
                 id="examples-06-plane2-gz", marks=_needs(GZ_CAPTURE)),
]


def _events(path, opener):
    with opener(path) as handle:
        return parse_trace_lines(handle)


def _inversions(events):
    """Global and per-key timestamp inversions, in file order."""
    global_inv = sum(1 for a, b in zip(events, events[1:]) if b["ts"] < a["ts"])
    last = {}
    per_key = 0
    for event in events:
        key = _pair_key(event)
        if key in last and event["ts"] < last[key]:
            per_key += 1
        last[key] = event["ts"]
    return global_inv, per_key


class TestTheTwoEntryPointsAgree:
    @pytest.mark.parametrize("path,opener", CAPTURES)
    def test_the_streamed_records_are_the_sorted_ones(self, path, opener):
        """Record for record, on both real captures."""
        events = _events(path, opener)
        assert events, f"{path} parsed to nothing"
        streamed = sorted(stream_records(iter(events)),
                          key=lambda record: record["start_ts"])
        assert streamed == pair_events(list(events))

    @pytest.mark.parametrize("path,opener", CAPTURES)
    def test_the_counts_come_out_of_the_same_pass(self, path, opener):
        """`count_unmatched_ends` walked the events a second time. After
        the pass there are no events to walk, so the pass fills them -
        and it must fill them with the same answer."""
        events = _events(path, opener)
        counts = {}
        list(stream_records(iter(events), counts))
        assert counts == count_unmatched_ends(events)

    @_needs(RAW_CAPTURE)
    @_needs(GZ_CAPTURE)
    def test_a_capture_is_out_of_global_order_and_in_per_key_order(self):
        """The premise, asserted on the capture that carries it.

        Without this clause the agreement above could hold simply
        because the file was already sorted, which would make the whole
        pass untested. `examples/06` is not sorted: two events arrive
        out of global order, and none out of its own key's order.
        """
        raw_global, raw_per_key = _inversions(_events(RAW_CAPTURE, open))
        gz_events = _events(GZ_CAPTURE, lambda p: gzip.open(p, "rt", errors="ignore"))
        gz_global, gz_per_key = _inversions(gz_events)

        assert (raw_global, raw_per_key) == (0, 0)
        assert gz_global > 0, (
            "examples/06 is globally ordered now - the agreement above no "
            "longer distinguishes a streaming pass from a sorting one, and "
            "this file needs a capture that does")
        assert gz_per_key == 0, (
            f"{gz_per_key} events arrive before an earlier event of their own "
            "key - the property the streaming pass rests on does not hold")

    def test_the_premise_holds_on_a_capture_a_clone_has(self):
        """The same premise as the clause above, where CI can check it.

        The real captures are gitignored, so the clause that measures
        *them* skips there. This one generates a log with the same two
        properties - out of global order, in per-key order - so the
        thing the streaming pass rests on is asserted everywhere and
        only the figures are local.
        """
        lines = []
        for index in range(60):
            element = f"core-{index % 5:02d}.bst"
            pid = 1000 + index % 11
            lines.append(
                f"START pid={pid} ppid=1 ts={2000.0 + index * 2} "
                f"element={element} inv=inv-{index % 5:02d} cmd=cc f{index}.c")
            lines.append(
                f"END pid={pid} ppid=1 ts={2000.0 + index * 2 + 1} "
                f"element={element} inv=inv-{index % 5:02d} "
                f"utime=0.01 stime=0.01 maxrss_kb=512 cmd=cc f{index}.c")
        events = parse_trace_lines(lines)
        # Interleave across keys the way concurrent writers do, without
        # ever reordering one key's own two events.
        by_key = {}
        for event in events:
            by_key.setdefault(_pair_key(event), []).append(event)
        queues = list(by_key.values())
        interleaved = []
        while queues:
            for queue in list(queues):
                interleaved.append(queue.pop(0))
                if not queue:
                    queues.remove(queue)

        global_inv, per_key_inv = _inversions(interleaved)
        assert global_inv > 0, (
            "the generated log is globally ordered, so it cannot stand in "
            "for a real capture's interleaving")
        assert per_key_inv == 0
        streamed = sorted(stream_records(iter(interleaved)),
                          key=lambda record: record["start_ts"])
        assert streamed == pair_events(list(interleaved))

    def test_they_agree_when_the_global_order_is_deliberately_shuffled(self):
        """Interleaving taken past what any real writer would produce.

        Each key's own events keep their order; everything else is
        shuffled. That is the exact shape the pass claims to survive and
        the sort claims to be needed for, so it is the shape to break it
        on.
        """
        lines = []
        for index in range(400):
            element = f"core-{index % 7:02d}.bst"
            pid = 1000 + index % 53
            lines.append(
                f"START pid={pid} ppid=1 ts={1000.0 + index} element={element} "
                f"inv=inv-{index % 7:02d} cmd=/usr/bin/cc -c f{index}.c")
            lines.append(
                f"END pid={pid} ppid=1 ts={1000.5 + index} element={element} "
                f"inv=inv-{index % 7:02d} utime_us=1200 stime_us=300 "
                f"max_rss_kb=2048 cmd=/usr/bin/cc -c f{index}.c")
        events = parse_trace_lines(lines)

        by_key = {}
        for event in events:
            by_key.setdefault(_pair_key(event), []).append(event)
        rng = random.Random(297)
        queues = list(by_key.values())
        shuffled = []
        while queues:
            queue = rng.choice(queues)
            shuffled.append(queue.pop(0))
            if not queue:
                queues.remove(queue)

        global_inv, per_key_inv = _inversions(shuffled)
        assert global_inv > 100, "the shuffle did not disorder anything"
        assert per_key_inv == 0, "the shuffle broke the premise it was to preserve"

        streamed = sorted(stream_records(iter(shuffled)),
                          key=lambda record: record["start_ts"])
        assert streamed == pair_events(list(shuffled))
        assert len(streamed) == 400


_NO_EVENT_LIST = """
import sys
import tools.bst_native_build_tracer as tracer

def refuse(*_args, **_kwargs):
    raise AssertionError("the extraction built a whole event list")

tracer.parse_trace_lines = refuse
tracer.parse_trace_log = refuse
tracer.pair_events = refuse
tracer.count_unmatched_ends = refuse
report = tracer.load_and_summarize(sys.argv[1])
print(report["process_count"])
"""

_TIMELINE_NO_EVENT_LIST = """
import sys
import tools.bst_native_build_tracer as tracer
import tools.bga_timeline as timeline

def refuse(*_args, **_kwargs):
    raise AssertionError("the timeline built a whole event list")

tracer.parse_trace_lines = refuse
tracer.parse_trace_log = refuse
tracer.pair_events = refuse
print(timeline.pick_anchor(sys.argv[1]), len(timeline.element_spans(sys.argv[1])))
"""


def _write_trace(path, processes):
    with open(path, "w", encoding="utf-8") as handle:
        for index in range(processes):
            element = f"core-{index % 4:02d}.bst"
            handle.write(
                f"START pid={1000 + index} ppid=1 ts={1000.0 + index} "
                f"element={element} inv=inv-{index % 4:02d} "
                f"cmd=/usr/bin/cc -c f{index}.c\n")
            handle.write(
                f"END pid={1000 + index} ppid=1 ts={1000.5 + index} "
                f"element={element} inv=inv-{index % 4:02d} utime_us=1200 "
                f"stime_us=300 max_rss_kb=2048 cmd=/usr/bin/cc -c f{index}.c\n")


class TestTheAnswerIsWrittenDown:
    """Four hand-worked processes, because equality is not enough.

    Every clause above compares the two entry points, and they share
    one implementation - so a change to `stream_records` moves both
    sides and the comparison stays true. That is the trap `UX-297`'s
    own `M2` fell into on the first pass. Falsified here: dropping the
    still-open records from the end of the pass leaves every equality
    clause green (both sides lose them together), and reddens this one.

    The trace below carries one of each thing the pass has to tell
    apart: a process that pairs, a START still open when the capture
    ended, a hook END with no START (a truncated log - the hook is
    loaded *by* the linker at exec, so it cannot be a fork-only child),
    and a spine END with no START (which is exactly a fork-only child,
    because `PTRACE_EVENT_EXIT` fires whether or not the process
    exec'd).
    """

    LOG = [
        "START pid=2 ppid=1 ts=1.0 element=e.bst inv=a cmd=paired",
        "END pid=2 ppid=1 ts=2.0 element=e.bst inv=a utime_us=10 stime_us=5",
        "START pid=3 ppid=1 ts=1.5 element=e.bst inv=a cmd=still-running",
        "END pid=4 ppid=1 ts=3.0 element=e.bst inv=a utime_us=1 stime_us=1",
        "END pid=5 ppid=1 ts=3.5 element=e.bst inv=a src=spine "
        "utime_us=1 stime_us=1",
    ]

    def test_the_pass_yields_exactly_these_records(self):
        counts = {}
        records = sorted(stream_records(iter(parse_trace_lines(self.LOG))),
                         key=lambda record: record["start_ts"])

        assert [(r["pid"], r["cmd"], r["open"]) for r in records] == [
            (2, "paired", False),
            (3, "still-running", True),
        ], "an open record is a process, not an omission"
        assert records[0]["duration_s"] == 1.0
        assert records[1]["duration_s"] is None, (
            "a process with no observed exit must not get a fabricated end")
        assert records[1]["open_reason"] == "no-observed-exit"

        list(stream_records(iter(parse_trace_lines(self.LOG)), counts))
        assert counts == {"fork_only": 1, "unmatched": 1}, (
            "the spine END is a fork-without-exec child and the hook END is "
            "a truncated log; one number for both states what neither "
            "record can support")


class TestNothingOnTheseTwoPathsBuildsAList:
    """The list-building entry points made fatal, inside a child.

    `UX-168` left a `handle.read()` under a comment that claimed to
    stream, which is why that item's own guard is written this way. The
    same shape catches the same regression here: a caller that reaches
    for `parse_trace_lines` again gets a list again, and no RSS number
    would say so on a fixture small enough to run in CI.
    """

    def _run(self, source, log):
        completed = subprocess.run(
            [sys.executable, "-c", source, str(log)],
            cwd=REPO_ROOT, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stderr
        return completed.stdout.strip()

    def test_the_analysis_never_builds_one(self, tmp_path):
        log = tmp_path / "trace.log"
        _write_trace(log, 40)
        assert self._run(_NO_EVENT_LIST, log) == "40"

    def test_the_timeline_passes_never_build_one(self, tmp_path):
        log = tmp_path / "trace.log"
        _write_trace(log, 40)
        assert self._run(_TIMELINE_NO_EVENT_LIST, log) == "core-00.bst 4"


class TestTheOldEntryPointStillMeansWhatItSaid:
    """`pair_events` is a wrapper now. Its contract is not."""

    def test_it_still_returns_a_start_sorted_list(self):
        events = parse_trace_lines([
            "START pid=3 ppid=1 ts=2.0 element=a.bst inv=a cmd=second",
            "END pid=3 ppid=1 ts=2.5 element=a.bst inv=a utime_us=1 stime_us=1",
            "START pid=2 ppid=1 ts=1.0 element=a.bst inv=a cmd=first",
            "END pid=2 ppid=1 ts=3.0 element=a.bst inv=a utime_us=1 stime_us=1",
        ])
        records = pair_events(list(events))
        assert [r["cmd"] for r in records] == ["first", "second"]
        assert isinstance(records, list)

    def test_consume_still_empties_the_list_it_was_given(self):
        events = parse_trace_lines([
            "START pid=2 ppid=1 ts=1.0 element=a.bst inv=a cmd=only",
            "END pid=2 ppid=1 ts=2.0 element=a.bst inv=a utime_us=1 stime_us=1",
        ])
        given = list(events)
        records = pair_events(given, consume=True)
        assert given == []
        assert len(records) == 1 and not records[0]["open"]

    def test_the_parser_still_pours_into_a_list(self):
        lines = ["START pid=2 ppid=1 ts=1.0 element=a.bst inv=a cmd=only"]
        assert parse_trace_lines(lines) == list(stream_trace_events(lines))
