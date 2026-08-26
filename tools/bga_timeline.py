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

# `UX-312`. The plane a slice belongs to, as a category - which is the
# channel `UX-210` designed every canned question around and which the
# trace stopped carrying when `UX-298` changed the format underneath
# them. The Chrome JSON converter wrote a `cat` field; the TrackEvent
# emitter had `EVENT_CATEGORY_IIDS` "reserved rather than used" until
# `UX-308` spent it on `failed`, so between those two rounds every
# query saying `where s.category = 'bst-builder'` matched **nothing**
# and returned zero rows in silence.
#
# The names are `UX-210`'s own, unchanged, because a query someone
# saved against the old trace should start working again rather than
# need rewriting. Interned, so a million slices cost two strings.
CATEGORY_PLANE1 = "bst-builder"
CATEGORY_PLANE2 = "native-process"
# `UX-210` named three scopes and the third is the build itself, which
# is `UX-311`'s identity slice: neither plane, and the thing a reader
# selects when they want to know whose run this is. Every slice in the
# trace carries exactly one of these three, so a question scoped by
# scope can never silently miss a class of them.
CATEGORY_RUN = "bst-invocation"


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
        return (CATEGORY_PLANE2,)
    return (CATEGORY_PLANE2, CATEGORY_FAILED)


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
# `UX-310`: the counter the reserved constant was waiting for.
#
# `UX-298` pinned `TYPE_COUNTER` with the comment "reserved rather than
# used". This is the caller - and it is **one** series, not the three
# the item imagined, for reasons that are worth having written down.
#
# *The memory curve does not exist.* `max_rss_kb` is `ru_maxrss`: a
# per-process peak over that process's whole lifetime, not a sample at a
# moment. A curve drawn from it would be summing peaks that never
# coexisted, which is precisely what `compute_peak_memory` refuses to do
# and says so at length ("two processes that each peaked at 500 MB at
# different moments never held 1 GB between them"). A counter must come
# from what the capture measured; this one was not measured, so it is
# not drawn.
#
# *"Cores busy" and "open process count" are the same series.* Both are
# "how many traced processes were running at time t", and `bga` already
# has one answer to that: `compute_max_concurrency`, over **matched**
# records only. Open records are excluded there deliberately - a
# `sh -c` wrapper that `_exit()`s never runs its destructor, so its end
# is unknown and its contribution at time t is unknowable. Excluding it
# from a peak and including it in a curve would be two answers to one
# question.
#
# So: one series, whose peak **equals** the published `max_concurrency`
# by construction, which is the acceptance test's "one pass, one truth".
CONCURRENCY_COUNTER = "traced processes running"
CONCURRENCY_UNIT = "processes"

# The stride, as a decision with a number behind it. A sample per
# endpoint is two packets per process - 400,000 on a 200,000-process
# trace, which is packet spam by any reading. Bucketing the build into a
# fixed number of windows makes the cost independent of the build's
# size, and emitting each window's **maximum** as well as its closing
# value keeps the peak exact (so the equality above survives the
# stride) while still drawing the shape rather than an envelope.
COUNTER_WINDOWS = 1000


def concurrency_series(records, windows: int = COUNTER_WINDOWS):
    """`(timestamp_s, running processes)` over the build, strided.

    The sweep is `compute_max_concurrency`'s: +1 at a matched record's
    start, -1 at its end, open records excluded. Ties go to the end
    first, so a process that starts exactly as another finishes never
    reads as two running at once - the same rule, because a series that
    disagreed with the scalar about a tie would be a second answer.
    """
    points = []
    for record in records:
        if record.get("open") or record.get("end_ts") is None:
            continue
        points.append((record["start_ts"], 1))
        points.append((record["end_ts"], -1))
    if not points:
        return []
    # `-1` before `+1` at the same timestamp: an end is taken first.
    points.sort(key=lambda point: (point[0], point[1]))

    span = points[-1][0] - points[0][0]
    # `windows=0` is "no stride at all" - every endpoint, which is what
    # a hand-worked case wants to compare against. It is not the
    # shipping setting for the reason in `COUNTER_WINDOWS`.
    if not windows:
        series = []
        running = 0
        for timestamp, delta in points:
            running += delta
            series.append((timestamp, running))
        return _monotonic(series)
    width = (span / windows) if span > 0 else 0.0

    series = []
    running = 0
    window_end = points[0][0] + width if width else None
    best = (points[0][0], 0)
    for timestamp, delta in points:
        if window_end is not None and timestamp > window_end:
            series.append(best)
            series.append((window_end, running))
            while window_end < timestamp:
                window_end += width
            best = (timestamp, 0)
        running += delta
        if running > best[1]:
            best = (timestamp, running)
    series.append(best)
    series.append((points[-1][0], running))
    return _monotonic(series)


def _monotonic(series):
    """The same series without repeated points.

    Perfetto draws a step function and a duplicate is a step of zero
    height, so consecutive identical samples are dropped.

    **Not** a re-ordering. The construction above is ordered by
    construction - every point folded into a window's maximum is at or
    before that window's end, and each window's end precedes the next
    window's points - and a filter that silently dropped a backwards
    sample would *hide* a construction bug rather than fix one. A
    mutation confirmed the branch was dead: removing it changed nothing,
    because nothing ever reached it. The ordering is asserted in
    `test_the_counter_the_constant_was_waiting_for.py` instead, where a
    break in it fails loudly.
    """
    out = []
    for timestamp, value in series:
        if out and out[-1] == (timestamp, value):
            continue
        out.append((timestamp, value))
    return out


# --------------------------------------------------------------------------
# `UX-311`: whose build this was.
#
# A trace file leaves the machine that made it - attached, shared,
# opened weeks later beside five others - and until this it carried no
# identity at all. The report refuses to present an interrupted run's
# numbers as measurements; the trace, opened directly in Perfetto,
# looked like any other build.
#
# The surface is one track and one instant on it, because that is
# portable vocabulary: `trace_processor` selects it like any other
# slice, and the UI shows it without knowing anything about `bga`.
IDENTITY_TRACK = "bga: run"
IDENTITY_TRACK_PID = 0

IDENTITY_ANNOTATIONS = (
    ("run", "the snapshot directory's own stamp - which run this is"),
    ("project", "the project identity the run was captured under"),
    ("targets", "the elements `bst build` was asked for"),
    ("manifest_hash", "the run identity hash two runs are compared by"),
    ("project_git_commit", "the commit the project was at, where it is a "
                           "git checkout"),
    ("bga_version", "the version of `bga` that wrote this trace"),
    ("bst_version", "the BuildStream the capture ran against"),
    ("host_cpu_model", "the CPU the build ran on, from the host manifest"),
    ("host_cpu_count", "how many cores that host had"),
    ("host_memory_mb", "how much memory it had"),
    ("kernel_release", "the kernel the sandboxes ran under"),
    ("distro_id", "the distribution the capture was taken on"),
    ("builders", "BuildStream's element-dispatch concurrency for this run"),
    ("incomplete_reason", "why this run is not a measurement - `failed`, "
                          "`interrupted` or `suspended`. Absent on a run "
                          "that finished, which is the only thing its "
                          "absence means"),
    ("anchor_element", "the element the two planes were aligned on"),
    ("plane_offset_us", "the single offset that alignment applied, in "
                        "microseconds"),
    ("lane_order", "the rule the element lanes are ordered by"),
)

# The whole trace dictionary's slice half, in one name. Three sets, one
# contract: a query does not care which plane a key came from, and the
# guard that holds emitted-equals-documented has to see all of them or
# it is only checking the ones it remembers.
ANNOTATION_CONTRACT = (PLANE1_ANNOTATIONS + PLANE2_ANNOTATIONS
                       + IDENTITY_ANNOTATIONS)

# `UX-311`'s deviation, named where the value is produced rather than
# only in the task file. The item asks for the *critical path* first,
# and the timeline has no critical path: it reads two logs and a graph,
# not an analysis, and computing one here would be a second copy of the
# analyzer's own rule. The heaviest traced element first is what this
# command can compute from what it reads, and the trace says which rule
# it used rather than leaving a reader to assume the other one.
LANE_ORDER_RULE = "longest-traced-first"


def run_identity(snapshot: str) -> dict:
    """What `run-context.json` says about the run, flattened.

    Everything here is already on disk; none of it is new capture. A
    snapshot without a readable context yields `{}` and the trace gets
    a bare identity track, which still says *which* run it is - the
    directory stamp is the one fact that needs no file.
    """
    path = os.path.join(snapshot, RUN_SUBDIR, "run-context.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            context = json.load(handle)
    except (OSError, ValueError):
        return {}
    identity = context.get("run_identity") or {}
    manifest = context.get("host_manifest") or {}
    toolchain = manifest.get("toolchain") or {}
    scheduler = identity.get("scheduler") or {}
    targets = identity.get("targets") or []
    return {
        "project": identity.get("project_identity"),
        "targets": ", ".join(targets) or None,
        "manifest_hash": identity.get("manifest_hash"),
        "project_git_commit": identity.get("project_git_commit"),
        "bst_version": toolchain.get("bst"),
        "host_cpu_model": manifest.get("cpu_model"),
        "host_cpu_count": manifest.get("cpu_count"),
        "host_memory_mb": manifest.get("memory_mb"),
        "kernel_release": manifest.get("kernel_release"),
        "distro_id": manifest.get("distro_id"),
        "builders": scheduler.get("builders"),
        "incomplete_reason": _incomplete_reason(context.get("build_outcome")),
    }


def _incomplete_reason(build_outcome):
    """Why this run is not a measurement, by `bga`'s own one rule.

    `UX-156`/`UX-157`/`UX-185` are answered by a single accessor
    precisely so a consumer cannot handle one and forget the others -
    which is what happened between the first two. Re-deriving it here
    would be the fourth place to forget the third; the model is
    constructed instead, which costs one import and is the same answer
    by construction.
    """
    if not build_outcome:
        return None
    from bga.ingest.models import RunContext

    return RunContext(build_outcome=build_outcome).incomplete_reason


def identity_annotations(snapshot: str, anchor, offset_us):
    """`IDENTITY_ANNOTATIONS`, filled - absent keys for absent facts."""
    from bga import __version__

    values = dict(run_identity(snapshot))
    values.update({
        "run": os.path.basename(os.path.normpath(snapshot)) or None,
        "bga_version": __version__,
        "anchor_element": anchor,
        "plane_offset_us": None if offset_us is None else int(round(offset_us)),
        "lane_order": LANE_ORDER_RULE,
    })
    return [(key, values.get(key)) for key, _ in IDENTITY_ANNOTATIONS
            if values.get(key) is not None]


def identity_track_name(reason) -> str:
    """The track's own name, which says `interrupted` where it applies.

    An annotation is something a reader has to open a slice to see. The
    honesty `UX-156` enforces in the report belongs where the first
    scroll lands, so the incompleteness is in the **name** and the
    reason is in the annotation beside it.
    """
    return IDENTITY_TRACK if not reason else f"{IDENTITY_TRACK} ({reason})"


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


def _plane1_start_us(plane1_events) -> float:
    """The earliest Plane 1 stamp, or 0.

    Where the identity instant goes (`UX-311`): at the beginning of the
    trace rather than at zero, so it sits with the run it describes on
    whatever window the UI opens on rather than off the left edge.
    """
    stamps = [event["ts"] for event in plane1_events
              if event.get("ph") in ("B", "E") and event.get("ts") is not None]
    return min(stamps) if stamps else 0.0


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
                      kinds=None, edges=(), snapshot=None):
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
        # `UX-311`: say once that the lane order is the ranks below, or
        # every rank is a hint no UI reads.
        trace.order_processes_explicitly()

        # `UX-311`: whose build this was, first lane and first thing a
        # reader meets. One instant on one track - portable vocabulary,
        # so `trace_processor` selects it like any other slice.
        reason = None
        if snapshot is not None:
            identity = identity_annotations(snapshot, anchor_element,
                                            offset_us)
            reason = dict(identity).get("incomplete_reason")
            identity_track = trace.process_track(
                identity_track_name(reason), pid=IDENTITY_TRACK_PID, rank=0)
            start_us = _plane1_start_us(plane1_events)
            trace.instant(int(round(start_us * NS_PER_US)), identity_track,
                          identity_track_name(reason), annotations=identity,
                          categories=(CATEGORY_RUN,))

        # Plane 1: one lane, one thread track per task tid, which is
        # the convention `bst_log_to_chrome_trace` already writes.
        plane1_track = trace.process_track("Plane 1: BuildStream", pid=1,
                                           rank=1)
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
                    categories=(CATEGORY_PLANE1,),
                    flows=sources, terminating_flows=sinks)
            else:
                trace.slice_end(timestamp, track)

        if not raw_log:
            return {"packets": trace.packets, "slices": trace.slices,
                    "tracks": trace.tracks, "flows": flow_count,
                    "flows_dropped": dropped, "incomplete_reason": reason,
                    "lane_order": LANE_ORDER_RULE, "counters": 0,
                    "counter_peak": None}

        # Plane 2: one process lane per element, one thread lane per
        # traced pid inside it.
        # `UX-311`: the lane order. Ranks 0 and 1 are the identity and
        # Plane 1; element lanes take 2 upward, heaviest first, which is
        # `LANE_ORDER_RULE` and is *not* the critical path - see there
        # for why this command cannot know that one. The pid stays the
        # sorted-name index so a lane's identity does not move when a
        # run's timings do.
        ranked = sorted(spans, key=lambda name: (-spans[name]["longest"], name))
        element_rank = {element: index + 2
                        for index, element in enumerate(ranked)}
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
            # `UX-310`: the series, folded from the records already in
            # hand and hung off the Plane 1 lane so it graphs above the
            # build rather than inside one element's group.
            series = concurrency_series(records)
            counter_track = None
            if series:
                counter_track = trace.counter_track(
                    CONCURRENCY_COUNTER, parent=plane1_track,
                    unit_name=CONCURRENCY_UNIT)
                for timestamp, value in series:
                    trace.counter(
                        int(round(timestamp * 1e6 * NS_PER_US
                                  + offset_us * NS_PER_US)),
                        counter_track, value)
            for record in records:
                element = record.get("element") or "unknown"
                pid = element_pid.get(element)
                if pid is None:
                    pid = element_pid[element] = len(element_pid) + 2
                lane = lanes.get(element)
                if lane is None:
                    # `UX-311`: the kind in the label, so a lane says
                    # what sort of element it is without a lookup.
                    kind = kinds.get(element)
                    label = (f"native: {element} ({kind})" if kind
                             else f"native: {element}")
                    lane = lanes[element] = {
                        "track": trace.process_track(
                            label, pid=pid,
                            rank=element_rank.get(element, len(element_rank) + 2)),
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
                "flows_dropped": dropped, "incomplete_reason": reason,
                "lane_order": LANE_ORDER_RULE,
                "counters": trace.counters,
                "counter_peak": max((v for _t, v in series), default=None)}


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
                edges=dependency_edges(snapshot), snapshot=snapshot)
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
