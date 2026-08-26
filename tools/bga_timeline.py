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
from typing import List, Optional

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


def _write_trackevent(plane1_events, raw_log, spans, anchor_element, output):
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
                trace.slice_begin(timestamp, track, event.get("name") or "task")
            else:
                trace.slice_end(timestamp, track)

        if not raw_log:
            return trace.packets, trace.slices, trace.tracks

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
            for record in sorted(stream_records(stream_trace_events(handle)),
                                 key=lambda record: record["start_ts"]):
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
                name = (record.get("cmd") or "")[:120] or "process"
                if record["open"] or record["end_ts"] is None:
                    # No observed exit. An instant, never a zero-width
                    # bar and never a fabricated end (`UX-188`).
                    trace.instant(start_ns, thread, f"{name} (no observed exit)")
                    continue
                end_ns = int(round(record["end_ts"] * 1e6 * NS_PER_US
                                   + offset_us * NS_PER_US))
                trace.slice_begin(start_ns, thread, name)
                trace.slice_end(max(end_ns, start_ns), thread)
        return trace.packets, trace.slices, trace.tracks


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
            packets, slices, tracks = _write_trackevent(
                plane1_events, raw if anchor else None, spans, anchor, output)
            result = {"planes": ["1", "2"] if (raw and anchor) else ["1"],
                      "anchor": anchor, "raw_log": raw, "format": fmt,
                      "packets": packets, "slices": slices, "tracks": tracks}
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
