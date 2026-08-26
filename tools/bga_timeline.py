"""UX-188: one timeline, both planes, one command.

Field feedback: *"recheck that we can produce chrome:tracing compatible
output for plane2 capture — maybe we can make some kind of merge tool
that can merge timeline from plane 1 and plane 2."*

Round 20 ground-truthed it and found the pieces already there:
`bga log-to-chrome` renders a snapshot's Plane 1 log, every extraction
writes `run/chrome_trace.json`, and `bga native-to-chrome combined
<plane1_chrome> <raw_log> <out> --anchor-element X` is precisely the
plane merge the field asked for. Three things kept a user from reaching
it, and none of them was the merge:

1. Snapshots did not retain the raw Plane 2 log the combined mode reads
   (`UX-188` item 1 - they do now, gzipped).
2. Wrong input succeeded silently (item 3 - it refuses now).
3. **Nobody composed it.** Reaching the merged timeline took three
   commands with invented paths, which is the pre-`UX-126` shape that
   `bga snapshot` exists to end.

This is item 2: the one command. It composes what already works rather
than reimplementing it, so the merged trace is byte-identical to what
the three-command form produced.

The anchor: `combined` aligns Plane 2's monotonic clock onto Plane 1's
wall clock using one element that appears in both. Given no
`--anchor-element`, this picks the longest-running element the Plane 2
capture actually traced - the one whose span is least sensitive to a
small alignment error.
"""
import argparse
import gzip
import json
import os
import shutil
import sys
import tempfile
from typing import Dict, List, Optional

HELP = """Render one Chrome-trace timeline for a snapshot, both planes in it.

Plane 1's element schedule always; Plane 2's process lanes underneath it
when the snapshot kept its raw trace log (`bga snapshot` keeps one by
default). Open the result with Perfetto (https://ui.perfetto.dev) or
chrome://tracing.
"""

RAW_LOG_NAME = "plane2.log.gz"
WRAPPED_LOG_NAME = "build.log"
RUN_SUBDIR = "run"

# `UX-298`: the two shapes this command can write. TrackEvent is
# Perfetto's own - a stream of packets, written as the records arrive
# and gzipped on the way out - and it is the default because it is what
# the tool the events are for reads natively. Chrome JSON stays for
# `chrome://tracing` and for anyone whose pipeline already parses it;
# it is the compatibility path, not the current one.
FORMAT_TRACKEVENT = "trackevent"
FORMAT_CHROME = "chrome"
FORMATS = (FORMAT_TRACKEVENT, FORMAT_CHROME)

DEFAULT_OUTPUT = {
    FORMAT_TRACKEVENT: "timeline.perfetto-trace.gz",
    FORMAT_CHROME: "timeline.json",
}

# Perfetto counts in nanoseconds; both planes here count in
# microseconds, and Plane 2 in seconds before that.
NS_PER_US = 1000

# --------------------------------------------------------------------------
# `UX-308`: the trace dictionary's slice half.
#
# A slice used to carry its name and nothing else, and for Plane 2 that
# name is the command **truncated to 120 characters** - so the argv tail
# that tells two compiler invocations apart was not in the trace at all.
# Everything below was already in the record or the run directory; none
# of it is new capture.
#
# These keys are a **contract**, not a convenience. They are what a
# details panel shows, what `extract_arg(arg_set_id, 'debug.<key>')`
# selects on, and what `UX-312`'s canned questions are written against -
# so renaming one silently breaks a query someone saved. The guard holds
# the emitted set and this table equal in both directions.
#
# Order is the order a reader meets them: the thing they opened the
# slice for first.
PLANE2_ANNOTATIONS = (
    ("cmd", "the full command line, untruncated - the slice name is the "
            "first 120 characters and this is the rest"),
    ("src", "which mechanism recorded it: `hook` (the LD_PRELOAD hook, "
            "loaded at exec) or `spine` (the ptrace supervisor)"),
    ("cpu_us", "CPU microseconds this process itself used, from its own "
               "`getrusage` at exit or the spine's read at the exit-stop"),
    ("max_rss_kb", "peak resident kilobytes of this process alone - never "
                   "summed with another's, which never held it at the same "
                   "moment"),
    ("exit_status", "how it ended, in the spine's own vocabulary: a "
                    "decimal exit code, or `signal:N` for a process the "
                    "kernel killed. The hook cannot see one - its "
                    "destructor runs before the process has a status, and "
                    "not at all when it is killed - so a hook-only record "
                    "carries no key rather than a zero"),
    ("exec_chain", "how many `execve`s this one record collapses - a shell "
                   "that exec'd a compiler is one process and two commands"),
)

PLANE1_ANNOTATIONS = (
    ("element", "the BuildStream element this task is for"),
    ("element_kind", "its kind from the run's own graph (`cmake`, `import`, "
                     "`manual`, ...), or `unknown` where the capture "
                     "recorded none"),
    ("task_type", "what the scheduler was doing: `build`, `fetch`, `pull`, "
                  "`push`, `track`"),
    ("outcome", "the status BuildStream's log closed the task with - "
                "`SUCCESS`, `FAILURE`, `CACHED` or `SKIPPED`. The cache "
                "outcome is the last two, and only where the log states it"),
)

# The one category, and the one already-pinned constant it earns
# (`EVENT_CATEGORY_IIDS`, reserved by `UX-298` and unused until now).
# A category is what makes a class of slice filterable in the UI and
# selectable in SQL, and "the work that failed" is the class a reader
# opening a broken build's trace is looking for.
CATEGORY_FAILED = "failed"


def _plane2_annotations(record: dict):
    """`PLANE2_ANNOTATIONS`, filled from one record.

    A key whose field the record does not carry is **absent**, not
    empty: a hook record has no `exit_status` because the hook cannot
    see one, and writing `0` there would state that the process
    succeeded.
    """
    values = {
        "cmd": record.get("cmd") or None,
        "src": record.get("src"),
        "cpu_us": record.get("cpu_us"),
        "max_rss_kb": record.get("max_rss_kb"),
        "exit_status": record.get("exit_status"),
        "exec_chain": record.get("exec_chain"),
    }
    return [(key, values[key]) for key, _ in PLANE2_ANNOTATIONS
            if values[key] is not None]


# The one value that means "this process succeeded". `spine.c` writes
# `exit=%d` for a normal exit and `exit=signal:%d` for a killed one, so
# the status is a **string with a vocabulary**, not a number - and
# `"0"` is the whole of the success half of it. Comparing it to the
# integer `0` would have called every process a failure; comparing
# truthiness would have called `"0"` a failure too.
EXIT_STATUS_OK = "0"


def _plane2_categories(record: dict):
    """`failed` on a process that did not exit 0, and on nothing else.

    A record with no `exit_status` at all is **not** categorised: the
    hook cannot observe one, so its absence is missing evidence rather
    than evidence of success, and marking those slices either way would
    state something the capture does not know.
    """
    status = record.get("exit_status")
    if status is None or str(status) == EXIT_STATUS_OK:
        return ()
    return (CATEGORY_FAILED,)


def element_kinds(snapshot: str) -> dict:
    """element uid -> its kind, from the run's own graph.

    `UX-308`. The kind is a Plane 1 fact that Plane 1's *log* never
    states - it is in `run/graph.json`, which the capture already wrote
    and which is one small entry per element. A snapshot without one
    (or with one this reader cannot parse) yields `{}` and every task
    annotates `unknown`, which is the honest answer rather than a
    missing key.
    """
    path = os.path.join(snapshot, RUN_SUBDIR, "graph.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            graph = json.load(handle)
    except (OSError, ValueError):
        return {}
    kinds = {}
    for element in graph.get("elements") or ():
        uid = element.get("uid")
        if uid:
            kinds[uid] = element.get("element_kind") or "unknown"
    return kinds


def _plane1_outcomes(events) -> dict:
    """`id(begin event)` -> the status its own end reported.

    The outcome is only known when the task closes, and the annotations
    ride the **begin** (`slice_begin`'s own rule). Plane 1 is a handful
    of tasks already held as a list, so pairing B to E by track and
    order costs nothing and puts the whole answer on one packet - rather
    than splitting a slice's facts across two, which a reader would have
    to reassemble.
    """
    open_by_tid: Dict[int, list] = {}
    outcomes = {}
    for event in events:
        phase = event.get("ph")
        if phase == "B":
            open_by_tid.setdefault(event.get("tid", 0), []).append(event)
        elif phase == "E":
            pending = open_by_tid.get(event.get("tid", 0))
            if pending:
                began = pending.pop()
                status = (event.get("args") or {}).get("Status")
                if status:
                    outcomes[id(began)] = status
    return outcomes


# --------------------------------------------------------------------------
# `UX-309`: the arrows.
#
# A flow is one id on two slices, and Perfetto infers the direction from
# their timestamps - "the earliest event with the same flow ID becomes
# the source". So the emitter is told "this slice is in flow F" and
# "this one ends it", never "from A to B", and an edge whose two slices
# are in the wrong time order would be drawn **backwards**. That is the
# one way this can state something false, so it is checked rather than
# assumed: an edge whose source does not begin before its sink is
# dropped and counted, and the count is in the render result.
#
# Two relations qualify, and only two. `graph.json`'s dependency edges
# are a Plane 1 fact the trace never said; `ppid` inside one sandbox is
# a Plane 2 fact the record already carries. There is no captured
# relation between one element's process and another's, and a flow that
# invented one would be a lie the UI draws in bold.
FLOW_DEPENDENCY = "dependency"
FLOW_EXEC = "parent"


def dependency_edges(snapshot: str):
    """`(predecessor, successor)` for every build-order edge in the run.

    From `run/graph.json`, which the capture already wrote. A snapshot
    without one yields nothing rather than raising: the timeline's job
    is to draw what it has.
    """
    path = os.path.join(snapshot, RUN_SUBDIR, "graph.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            graph = json.load(handle)
    except (OSError, ValueError):
        return []
    edges = []
    for edge in graph.get("dependencies") or ():
        predecessor, successor = edge.get("predecessor"), edge.get("successor")
        if predecessor and successor and predecessor != successor:
            edges.append((predecessor, successor))
    return edges


def _last_to_end(spans):
    """The begin event of the slice that ended last, or `None`."""
    return max(spans, key=lambda pair: pair[1])[0] if spans else None


def _first_to_begin(spans):
    """The begin event of the slice that started first, or `None`."""
    return min(spans, key=lambda pair: pair[0]["ts"])[0] if spans else None


def _plane1_flows(plane1_events, edges, first_flow_id):
    """Which begin-event carries which flow id, for the graph's edges.

    Returns `(by_event_id, dropped)`. An element's **last-ending** slice
    is the source of its outgoing edges and its **first-beginning**
    slice is the sink of its incoming ones - the dependency is satisfied
    when the predecessor has finished, and it constrains when the
    dependent may start. On a `bst build` these are the same slice,
    because an element gets one builder task; the rule is written for
    the capture that also has a fetch or a pull in the lane.
    """
    # B paired to E per track, as `_plane1_outcomes` does - keeping the
    # begin *object*, because that is what carries the flow ids.
    spans = {}
    open_by_tid = {}
    for event in plane1_events:
        phase = event.get("ph")
        if phase == "B":
            open_by_tid.setdefault(event.get("tid", 0), []).append(event)
        elif phase == "E":
            pending = open_by_tid.get(event.get("tid", 0))
            if not pending:
                continue
            began = pending.pop()
            element = (began.get("args") or {}).get("element")
            if not element:
                continue
            spans.setdefault(element, []).append((began, event["ts"]))

    flows = {}
    flow_id = first_flow_id
    dropped = 0
    for predecessor, successor in edges:
        source = _last_to_end(spans.get(predecessor))
        sink = _first_to_begin(spans.get(successor))
        if source is None or sink is None:
            # One end of the edge produced no task in this run - a
            # cached element, or one built earlier. Nothing to connect,
            # and an arrow to nowhere is not an improvement.
            continue
        if source["ts"] >= sink["ts"]:
            # The flow ids ride the **begin** events, so the begins are
            # what Perfetto compares. Equal or reversed, it would draw
            # the arrow backwards - the reverse of the dependency - or
            # pick one at random. On `examples/06` this is two edges:
            # `toolchain.bst` is instantaneous and both its dependents
            # begin in the microsecond it does.
            dropped += 1
            continue
        flows.setdefault(id(source), ([], []))[0].append(flow_id)
        flows.setdefault(id(sink), ([], []))[1].append(flow_id)
        flow_id += 1
    return flows, dropped, flow_id


def _plane2_flows(records, first_flow_id):
    """`id(record)` -> flow ids, for the exec chain inside one sandbox.

    A record's `ppid` names its parent, and pids are namespaced per
    sandbox - so the parent is looked up inside the same
    `(invocation, element)` and never across two, because no captured
    relation exists between one element's process and another's.

    A pid is reused inside a sandbox, so the parent is the holder of
    that pid whose own span contains the child's start; two candidates
    that both do would be a pid alive twice at once, which
    `--unshare-pid` does not do.
    """
    by_pid = {}
    for record in records:
        key = (record.get("invocation"), record.get("element"), record["pid"])
        by_pid.setdefault(key, []).append(record)

    flows = {}
    flow_id = first_flow_id
    for record in records:
        parent_key = (record.get("invocation"), record.get("element"),
                      record.get("ppid"))
        if record.get("ppid") is None or parent_key[2] == record["pid"]:
            continue
        parent = None
        for candidate in by_pid.get(parent_key) or ():
            if candidate["start_ts"] > record["start_ts"]:
                continue
            end = candidate.get("end_ts")
            if end is not None and end < record["start_ts"]:
                continue
            parent = candidate
        if parent is None:
            continue
        flows.setdefault(id(parent), ([], []))[0].append(flow_id)
        flows.setdefault(id(record), ([], []))[1].append(flow_id)
        flow_id += 1
    return flows, flow_id


def _plane1_annotations(event: dict, kinds: dict, outcome) -> list:
    args = event.get("args") or {}
    element = args.get("element")
    values = {
        "element": element,
        "element_kind": kinds.get(element, "unknown") if element else None,
        "task_type": args.get("action"),
        "outcome": outcome,
    }
    return [(key, values[key]) for key, _ in PLANE1_ANNOTATIONS
            if values[key] is not None]



def _raw_log(snapshot: str) -> Optional[str]:
    """The snapshot's raw Plane 2 log, compressed or not."""
    for name in (RAW_LOG_NAME, RAW_LOG_NAME[:-3]):
        candidate = os.path.join(snapshot, name)
        if os.path.exists(candidate):
            return candidate
    return None


def _open_raw(path: str):
    return (gzip.open(path, "rt", encoding="utf-8", errors="ignore")
            if path.endswith(".gz")
            else open(path, "r", encoding="utf-8", errors="ignore"))


def pick_anchor(raw_log: str) -> Optional[str]:
    """The element whose Plane 2 span is longest, or None.

    The alignment is a single offset, so any element in both planes
    works; the longest one is chosen because a fixed error in the offset
    is the smallest *share* of its span, and because it is the element a
    reader opening the timeline is most likely looking for.
    """
    from .bst_native_build_tracer import stream_records, stream_trace_events

    spans = {}
    with _open_raw(raw_log) as handle:
        # `UX-297`: a max per element, which is a fold - so the records
        # stream past rather than piling up, and the events behind them
        # never exist as a list at all.
        for record in stream_records(stream_trace_events(handle)):
            element = record.get("element")
            if not element or element == "unknown":
                continue
            start, end = record.get("start_ts"), record.get("end_ts")
            if start is None or end is None:
                continue
            spans[element] = max(spans.get(element, 0), end - start)
    return max(spans, key=spans.get) if spans else None


def element_spans(raw_log: str) -> dict:
    """One streaming pass over the raw log: per element, the longest
    single process and the earliest start.

    `UX-298`. Both numbers the merge needs come out of the same walk -
    the anchor is the element with the longest traced process
    (`pick_anchor`'s rule, unchanged), and the offset needs that
    element's earliest monotonic start. Doing it once means the log is
    read twice rather than three times, and nothing is held but one
    entry per element.
    """
    from .bst_native_build_tracer import stream_records, stream_trace_events

    spans = {}
    with _open_raw(raw_log) as handle:
        for record in stream_records(stream_trace_events(handle)):
            element = record.get("element")
            if not element or element == "unknown":
                continue
            start, end = record.get("start_ts"), record.get("end_ts")
            if start is None or end is None:
                continue
            entry = spans.get(element)
            if entry is None:
                spans[element] = {"longest": end - start, "earliest": start}
            else:
                entry["longest"] = max(entry["longest"], end - start)
                entry["earliest"] = min(entry["earliest"], start)
    return spans


def plane1_elements(plane1_events) -> set:
    """The elements Plane 1 recorded a builder task for.

    `UX-298`: the anchor has to be in **both** planes, and picking it
    from Plane 2 alone can name one Plane 1 never built - a capture
    whose heaviest traced element was, say, a subproject built in an
    earlier run. The merge then refuses with `no Plane 1 'bst-builder' B
    event found`, which is a correct refusal to a question that should
    not have been asked. Found by this item's own streaming fixture, on
    a shape the two-element fixtures could not produce.
    """
    return {
        (event.get("args") or {}).get("element")
        for event in plane1_events
        if event.get("ph") == "B" and event.get("cat") == "bst-builder"
    } - {None}


def choose_anchor(spans, plane1_events) -> Optional[str]:
    """The longest-traced element that **both** planes know.

    Longest, for `pick_anchor`'s reason: a fixed error in the offset is
    the smallest share of the longest span. Shared, because an anchor
    only one plane has is not an anchor. Falls back to the longest
    overall when the two planes name nothing in common, so a capture
    that used to render still renders and fails the same way it did.
    """
    if not spans:
        return None
    shared = spans.keys() & plane1_elements(plane1_events)
    candidates = shared or spans.keys()
    return max(candidates, key=lambda name: spans[name]["longest"])


def _plane1_offset_us(plane1_events, spans, anchor_element) -> float:
    """Plane 2's monotonic clock, placed on Plane 1's wall clock.

    The same single anchor point `native_trace_to_chrome_trace` uses -
    the anchor element's Plane 1 **build** task against its earliest
    Plane 2 process - reached through that module so the two formats
    cannot drift apart on the one number that decides whether the
    planes line up.
    """
    from .native_trace_to_chrome_trace import compute_clock_offset_us

    earliest = spans[anchor_element]["earliest"]
    return compute_clock_offset_us(
        plane1_events,
        [{"element": anchor_element, "start_ts": earliest}],
        anchor_element)


def _write_trackevent(plane1_events, raw_log, spans, anchor_element, output,
                      kinds=None, edges=()):
    """The trace, packet by packet - nothing accumulates but the rows.

    Plane 1 is a handful of tasks and goes in first from the list the
    converter already built. Plane 2 is read as a stream of *events*
    (`UX-297`) and drawn from the record list those events fold to: one
    packet is written per slice and none are buffered, but the records
    are ordered by start before drawing, for the reason the loop below
    states. What grows with the build is one entry per `(element, pid)`
    lane - the same cardinality the Chrome converter's `tid` had, named
    here rather than left to be discovered - and one record per
    process, which is what a per-process timeline is.
    """
    from .bst_native_build_tracer import stream_records, stream_trace_events
    from .native_trace.trackevent import TrackEventWriter

    offset_us = (_plane1_offset_us(plane1_events, spans, anchor_element)
                 if anchor_element else 0.0)
    kinds = kinds or {}
    outcomes = _plane1_outcomes(plane1_events)
    # `UX-309`: flow ids are global within a trace, so one counter runs
    # through both planes. Plane 1's are assigned first because Plane 1
    # is written first; Plane 2's continue from wherever that ended.
    plane1_flows, dropped, next_flow = _plane1_flows(plane1_events, edges, 1)
    flow_count = next_flow - 1

    with TrackEventWriter(output) as trace:
        # Plane 1: one lane, one thread track per task tid, which is
        # the convention `bst_log_to_chrome_trace` already writes.
        plane1_track = trace.process_track("Plane 1: BuildStream", pid=1)
        threads = {}
        names = {}
        for event in plane1_events:
            phase = event.get("ph")
            if phase == "M" and event.get("name") == "thread_name":
                names[event.get("tid")] = (event.get("args") or {}).get("name")
            if phase not in ("B", "E"):
                continue
            tid = event.get("tid", 0)
            track = threads.get(tid)
            if track is None:
                track = threads[tid] = trace.thread_track(
                    names.get(tid) or f"tid {tid}", parent=plane1_track,
                    pid=1, tid=tid)
            timestamp = int(round(event["ts"] * NS_PER_US))
            if phase == "B":
                sources, sinks = plane1_flows.get(id(event), ((), ()))
                trace.slice_begin(
                    timestamp, track, event.get("name") or "task",
                    annotations=_plane1_annotations(
                        event, kinds, outcomes.get(id(event))),
                    flows=sources, terminating_flows=sinks)
            else:
                trace.slice_end(timestamp, track)

        if not raw_log:
            return {"packets": trace.packets, "slices": trace.slices,
                    "tracks": trace.tracks, "flows": flow_count,
                    "flows_dropped": dropped}

        # Plane 2: one process lane per element, one thread lane per
        # traced pid inside it.
        element_pid = {element: index + 2
                       for index, element in enumerate(sorted(spans))}
        lanes = {}
        with _open_raw(raw_log) as handle:
            # `UX-297`: the events stream; the records are still sorted
            # by start before they are drawn, and that is deliberate.
            # Slices are emitted per *track*, and a track here is
            # `(element, pid)` - which a dual-stream process shares with
            # itself. The spine sees the exec first and the kernel exit
            # last; the hook's constructor runs after the exec and its
            # `atexit` before the exit, so the pass yields the hook's
            # record first and the spine's second while their starts run
            # the other way. Measured on the four-line case: streamed
            # `[hook 100.001, spine 100.000]` against sorted
            # `[spine 100.000, hook 100.001]`. Emitting that order into
            # the trace would reorder two slices on one track under a
            # change about memory, so the sort stays and the floor here
            # is O(processes) - the events, which are twice as many, are
            # the ones that no longer pile up.
            records = sorted(stream_records(stream_trace_events(handle)),
                             key=lambda record: record["start_ts"])
            # `UX-309`: the exec chain needs each record's parent, which
            # is a lookup over the list the sort already materialized -
            # no second read of the log, and no second copy of it.
            plane2_flows, next_flow = _plane2_flows(records, next_flow)
            flow_count = next_flow - 1
            for record in records:
                element = record.get("element") or "unknown"
                pid = element_pid.get(element)
                if pid is None:
                    pid = element_pid[element] = len(element_pid) + 2
                lane = lanes.get(element)
                if lane is None:
                    lane = lanes[element] = {
                        "track": trace.process_track(f"native: {element}",
                                                     pid=pid),
                        "threads": {},
                    }
                thread = lane["threads"].get(record["pid"])
                if thread is None:
                    thread = lane["threads"][record["pid"]] = trace.thread_track(
                        f"pid {record['pid']}", parent=lane["track"],
                        pid=pid, tid=record["pid"])
                start_ns = int(round(record["start_ts"] * 1e6 * NS_PER_US
                                     + offset_us * NS_PER_US))
                # `UX-308`: the name stays 120 characters - a lane is
                # read at a glance - and the full argv rides beside it
                # as an annotation, which is where length belongs.
                name = (record.get("cmd") or "")[:120] or "process"
                annotations = _plane2_annotations(record)
                categories = _plane2_categories(record)
                sources, sinks = plane2_flows.get(id(record), ((), ()))
                if record["open"] or record["end_ts"] is None:
                    # No observed exit. An instant, never a zero-width
                    # bar and never a fabricated end (`UX-188`).
                    trace.instant(start_ns, thread,
                                  f"{name} (no observed exit)",
                                  annotations=annotations,
                                  categories=categories,
                                  flows=sources, terminating_flows=sinks)
                    continue
                end_ns = int(round(record["end_ts"] * 1e6 * NS_PER_US
                                   + offset_us * NS_PER_US))
                trace.slice_begin(start_ns, thread, name,
                                  annotations=annotations,
                                  categories=categories,
                                  flows=sources, terminating_flows=sinks)
                trace.slice_end(max(end_ns, start_ns), thread)
        return {"packets": trace.packets, "slices": trace.slices,
                "tracks": trace.tracks, "flows": flow_count,
                "flows_dropped": dropped}


def render(snapshot: str, output: str,
           anchor_element: Optional[str] = None, quiet: bool = False,
           fmt: str = FORMAT_TRACKEVENT) -> dict:
    """Write the timeline. Returns what went into it, for the caller to say.

    `quiet` for a caller rendering into a scratch path it will delete -
    `bga view`, which serves the bytes rather than the file. Without it
    the converters name a path that is gone by the time anyone reads
    the line (`UX-197` item 2, and `UX-194` for this second caller).

    `fmt` is `UX-298`: `trackevent` writes Perfetto's own format as a
    stream of packets, `chrome` writes the legacy JSON the two
    converters have always produced. Both read the same two logs and
    align on the same anchor, so the choice is a matter of what will
    open the file, not of what is in it.
    """
    from .bst_log_to_chrome_trace import main as plane1_main
    from .native_trace_to_chrome_trace import main as merge_main

    if fmt not in FORMATS:
        raise ValueError(f"unknown timeline format {fmt!r}; "
                         f"expected one of {', '.join(FORMATS)}")

    wrapped = os.path.join(snapshot, WRAPPED_LOG_NAME)
    if not os.path.exists(wrapped):
        raise FileNotFoundError(
            f"{snapshot}: no {WRAPPED_LOG_NAME} here. `bga timeline` renders a "
            f"snapshot directory (the one `bga snapshot` created), not a run "
            f"directory - try its parent.")

    scratch = tempfile.mkdtemp(prefix="bga-timeline-")
    try:
        plane1 = os.path.join(scratch, "plane1.json")
        # The existing converters, called rather than reimplemented, so
        # this command cannot drift from the three-command form it
        # replaces.
        code = plane1_main([wrapped, plane1], quiet=True)
        if code:
            raise RuntimeError(f"rendering Plane 1 failed (exit {code})")

        raw = _raw_log(snapshot)
        with open(plane1, "r", encoding="utf-8") as handle:
            plane1_events = json.load(handle)
        spans = element_spans(raw) if raw else {}
        anchor = anchor_element or choose_anchor(spans, plane1_events)

        if fmt == FORMAT_TRACKEVENT:
            written = _write_trackevent(
                plane1_events, raw if anchor else None, spans, anchor, output,
                kinds=element_kinds(snapshot),
                edges=dependency_edges(snapshot))
            result = {"planes": ["1", "2"] if (raw and anchor) else ["1"],
                      "anchor": anchor, "raw_log": raw, "format": fmt}
            result.update(written)
            if raw and not anchor:
                result["omitted"] = (
                    "the Plane 2 capture attributes no span to an element, so "
                    "there is nothing to align the two planes on")
            return result

        if raw is None:
            shutil.copyfile(plane1, output)
            return {"planes": ["1"], "anchor": None, "raw_log": None,
                    "format": fmt}

        if anchor is None:
            # A raw log with no element-attributed span: the merge has
            # nothing to align on, so Plane 1 alone is the honest output.
            shutil.copyfile(plane1, output)
            return {"planes": ["1"], "anchor": None, "raw_log": raw,
                    "format": fmt,
                    "omitted": "the Plane 2 capture attributes no span to an "
                               "element, so there is nothing to align the two "
                               "planes on"}

        # `combined` reads an uncompressed log; decompress into scratch.
        source = raw
        if raw.endswith(".gz"):
            source = os.path.join(scratch, "plane2.log")
            with _open_raw(raw) as handle, open(source, "w", encoding="utf-8") as out:
                shutil.copyfileobj(handle, out, length=1024 * 1024)

        code = merge_main(["combined", plane1, source, output,
                           "--anchor-element", anchor], quiet=quiet)
        if code:
            raise RuntimeError(f"merging Plane 2 failed (exit {code})")
        return {"planes": ["1", "2"], "anchor": anchor, "raw_log": raw,
                "format": fmt}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def describe(result: dict, output: str) -> str:
    lines = []
    if result["planes"] == ["1", "2"]:
        lines.append(f"Wrote both planes to {output}, aligned on "
                     f"{result['anchor']}.")
    else:
        lines.append(f"Wrote Plane 1 to {output}.")
        lines.append(
            "  Plane 2 is not in it: " + (
                result.get("omitted")
                or "this snapshot kept no raw trace log. `bga snapshot` keeps "
                   "one by default; a capture taken with --no-keep-raw, or "
                   "before UX-188, has only the processed report."))
    if result.get("format") == FORMAT_CHROME:
        lines.append("  Open it with Perfetto (https://ui.perfetto.dev) or "
                     "chrome://tracing.")
    else:
        # `chrome://tracing` is deliberately not offered here: it reads
        # the JSON shape, not this one, and naming a viewer that will
        # refuse the file is the kind of dead offer `UX-194` fixed.
        lines.append(f"  {result.get('slices', 0)} slices on "
                     f"{result.get('tracks', 0)} tracks. Open it with "
                     "Perfetto (https://ui.perfetto.dev), which reads this "
                     "format natively; `bga timeline --format chrome` writes "
                     "the legacy JSON for chrome://tracing.")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    from bga.help_format import CompactRawHelp

    parser = argparse.ArgumentParser(
        prog="bga timeline", description=HELP,
        formatter_class=lambda prog: CompactRawHelp(prog),
    )
    parser.add_argument(
        "run", nargs="?", default="@last",
        help="The snapshot to render; `@last` by default, same alias grammar "
             "as every other command.")
    parser.add_argument(
        "-o", "--output", default=None, metavar="PATH",
        help="Where to write the trace. Defaults to `timeline.json` inside "
             "the snapshot.")
    parser.add_argument(
        "--anchor-element", default=None, metavar="ELEMENT",
        help="Align the two planes on this element instead of the "
             "longest-running one Plane 2 traced.")
    parser.add_argument(
        "--format", default=FORMAT_TRACKEVENT, choices=list(FORMATS),
        help="`trackevent` (the default) writes Perfetto's own protobuf "
             "trace, gzipped and written as a stream. `chrome` writes the "
             "legacy Chrome JSON, for `chrome://tracing` and for a pipeline "
             "that already parses it (UX-298).")
    args = parser.parse_args(argv)

    from bga import run_store

    # The same gate every other command uses: an alias is resolved
    # against the project, and anything else is a path meaning exactly
    # what it says. Reaching for `resolve_snapshot` directly made an
    # explicit path an error, which is not the store's grammar.
    try:
        snapshot = (run_store.resolve_snapshot(args.run, run_store.project_root())
                    if run_store.is_alias(args.run) else args.run)
    except Exception as error:  # noqa: BLE001 - reported, not swallowed
        print(f"Error: {error}", file=sys.stderr)
        return 2

    output = args.output or os.path.join(snapshot, DEFAULT_OUTPUT[args.format])
    try:
        result = render(snapshot, output, anchor_element=args.anchor_element,
                        fmt=args.format)
    except (FileNotFoundError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(describe(result, output), file=sys.stderr)
    print(json.dumps({"output": output, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
