#!/usr/bin/env python3
"""UX-24: Chrome Trace Event JSON export for Plane 2 (`UX-11`'s native-
build-system tracer, `tools/bst_native_build_tracer.py`), standalone or
combined with Plane 1's own real, already-existing export
(`tools/bst_log_to_chrome_trace.py`) for the *same* real captured run.

Mirrors `tools/chrome_trace_to_bga_trace.py`'s own naming convention - a
second, separate converter, not folded into the tracer itself, matching
this repo's established "small single-purpose tools" discipline. Never
changes `tools/bst_log_to_chrome_trace.py`'s own real output shape - the
user's own established `perfetto.dev` workflow for Plane 1 alone must
keep working exactly as before (see docs/ingestion-pipeline.md).

Output shape: a bare JSON array of trace events (Chrome Trace's own
"JSON Array Format"), matching `bst_log_to_chrome_trace.py`'s own real,
already-in-use `get_json()` output exactly (confirmed by reading it
directly - `json.dumps(meta_events + self.trace_events)`, not
`{"traceEvents": [...]}`) - the least surprising choice for a user who
already knows Plane 1's own file shape, and what "combined" mode's own
end-to-end test caught as a real, confirmed bug in an earlier draft that
assumed the object-wrapped shape instead.

Two real, independent modes:

- **standalone**: converts a Plane 2 raw trace log alone into a real
  Chrome Trace JSON. Each distinct real element gets its own synthetic
  Chrome Trace `pid` (a "process" swimlane in perfetto.dev), and each
  real traced OS process gets its own `tid` (a "thread" row) within its
  element's own swimlane - genuinely more granular than Plane 1's own
  per-element/per-task rows, since every real compiler-driver internal
  (`cc1plus`/`as`/`ld`/`collect2`, not just the outer `cmake`/`make`
  wrappers) gets its own row.
- **combined**: merges Plane 1's own real, already-generated Chrome
  Trace events with a Plane 2 element-tagged raw trace for the *same*
  real run into one file - expanding any cmake element's own Plane 1 row
  in perfetto.dev reveals its own real Plane 2 sub-process tree nested
  underneath. The real design risk this mode has to solve: Plane 1's own
  timestamps are wall-clock-anchored (`bst_log_to_chrome_trace.py`'s own
  `_resolve_start_time_us`), Plane 2's are `CLOCK_MONOTONIC`-anchored
  (an arbitrary epoch - see `hook.c`'s own header) - `compute_clock_offset_us`
  computes one real, single global additive offset from exactly one real
  anchor point (a chosen element's own Plane 1 "Running commands" B event
  vs. that same element's own earliest Plane 2 traced process), then
  applies it uniformly to every Plane 2 timestamp. This is sound because
  `CLOCK_MONOTONIC` is the *same* underlying kernel clock for every
  process on the system regardless of which element's sandbox it's in
  (confirmed real, `UX-11`'s own doc) - one anchor point is enough,
  computing a separate offset per element would be both unnecessary and
  a real risk of introducing *inconsistent* offsets that would break the
  "one shared timeline" property this whole mode exists to provide.

  The anchor itself is each element's own single outer `bst-builder` B
  event (`args.element == anchor_element`) - not, as an earlier draft of
  this design assumed, a distinct "Running commands" event. Confirmed by
  running the real end-to-end capture and inspecting Plane 1's own real
  output directly: `bst_log_to_chrome_trace.py`'s `handle_bst_event`
  treats every nested sub-phase (Staging sources, Running commands,
  Caching artifact, ...) sharing the same `hash`+`action` as depth-
  tracking on the *same already-open* span, never a separate trace
  event of its own - so there is exactly one real B event per element
  per action to anchor on, not one per phase.
"""
import argparse
import json
from typing import Dict, List

PLANE2_CAT = "native-process"


def assign_element_pids(elements: List[str], start_pid: int = 2) -> Dict[str, int]:
    """A stable synthetic Chrome Trace `pid` per real element, sorted
    for determinism (I11) - never `pid: 1`, reserved for Plane 1's own
    real "the BuildStream invocation" sentinel (`bst_log_to_chrome_trace.py`),
    so a combined-mode trace never collides the two planes' own process
    rows."""
    return {element: start_pid + i for i, element in enumerate(sorted(set(elements)))}


def _process_name_events(element_pids: Dict[str, int]) -> List[dict]:
    return [
        {"name": "process_name", "ph": "M", "pid": pid, "args": {"name": f"native: {element}"}}
        for element, pid in element_pids.items()
    ]


def _plane2_trace_events(records: List[dict], element_pids: Dict[str, int], ts_offset_us: float) -> List[dict]:
    """Real Chrome Trace events for Plane 2's own traced processes -
    complete (`X`) events for matched (start+end known) records, instant
    (`i`) events for open (no observed exit) ones (an honest choice: a
    zero-width bar could be misread as "instantaneous", this tool never
    fabricates an end time Plane 2 itself doesn't have)."""
    events = []
    for r in records:
        pid = element_pids.get(r["element"], element_pids.get("unknown", 1))
        name = r["cmd"][:120] + ("..." if len(r["cmd"]) > 120 else "")
        start_us = r["start_ts"] * 1e6 + ts_offset_us
        if r["open"]:
            events.append({
                "name": f"{name} (no observed exit)", "cat": PLANE2_CAT, "ph": "i",
                "ts": start_us, "pid": pid, "tid": r["pid"], "s": "t",
                "args": {"element": r["element"], "real_pid": r["pid"]},
            })
        else:
            events.append({
                "name": name, "cat": PLANE2_CAT, "ph": "X",
                "ts": start_us, "dur": r["duration_s"] * 1e6, "pid": pid, "tid": r["pid"],
                "args": {"element": r["element"], "real_pid": r["pid"]},
            })
    return events


def build_standalone_chrome_trace(records: List[dict]) -> List[dict]:
    """Real Plane 2 records (as returned by `bst_native_build_tracer.pair_events`)
    alone, converted into a real, self-contained Chrome Trace event list.
    Timestamps are normalized so the trace starts near `ts=0` (Plane 2's
    own `CLOCK_MONOTONIC` epoch is arbitrary and meaningless on its own -
    only relative offsets are real)."""
    if not records:
        return []
    element_pids = assign_element_pids([r["element"] for r in records])
    min_start = min(r["start_ts"] for r in records)
    offset_us = -min_start * 1e6
    return _process_name_events(element_pids) + _plane2_trace_events(records, element_pids, offset_us)


def compute_clock_offset_us(plane1_trace_events: List[dict], plane2_records: List[dict], anchor_element: str) -> float:
    """The one real, global additive offset (microseconds) to convert
    every Plane 2 `CLOCK_MONOTONIC`-seconds timestamp into Plane 1's own
    real wall-clock-microseconds coordinate system - computed from
    exactly one real anchor point: `anchor_element`'s own single, real
    outer Plane 1 `bst-builder` B event (real wall-clock start of that
    element's own build/fetch/... task as a whole - confirmed to be the
    only real per-element B event Plane 1 ever emits, see this module's
    own docstring) vs. that same element's own earliest Plane 2 traced
    process (real monotonic start). Raises ValueError if either side has
    no real data for `anchor_element` - never silently guesses an offset
    of 0."""
    plane1_ts_us = None
    for ev in plane1_trace_events:
        if ev.get("ph") != "B" or ev.get("cat") != "bst-builder":
            continue
        if ev.get("args", {}).get("element") != anchor_element:
            continue
        plane1_ts_us = ev["ts"]
        break
    if plane1_ts_us is None:
        raise ValueError(f"no Plane 1 'bst-builder' B event found for element {anchor_element!r}")

    plane2_starts = [r["start_ts"] for r in plane2_records if r["element"] == anchor_element]
    if not plane2_starts:
        raise ValueError(f"no Plane 2 traced process found for element {anchor_element!r}")
    plane2_earliest_s = min(plane2_starts)

    return plane1_ts_us - (plane2_earliest_s * 1e6)


def build_combined_chrome_trace(
    plane1_trace_events: List[dict], plane2_records: List[dict], anchor_element: str,
) -> List[dict]:
    """Merges Plane 1's own real trace events (unmodified - its own
    `pid: 1`/per-task `tid` convention is untouched) with Plane 2's own
    real per-process events, correlated onto one shared timeline via
    `compute_clock_offset_us`. `plane1_trace_events` is the real, bare
    event list `bst_log_to_chrome_trace.py`'s own `get_json()` produces
    (already parsed from its own real output file). Plane 2 elements get
    synthetic `pid`s starting at 2 (`assign_element_pids`' own default),
    never colliding with Plane 1's `pid: 1`."""
    offset_us = compute_clock_offset_us(plane1_trace_events, plane2_records, anchor_element)
    element_pids = assign_element_pids([r["element"] for r in plane2_records])
    return (
        list(plane1_trace_events) + _process_name_events(element_pids)
        + _plane2_trace_events(plane2_records, element_pids, offset_us)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    standalone_parser = subparsers.add_parser("standalone", help="Plane 2 raw trace alone -> Chrome Trace JSON")
    standalone_parser.add_argument("raw_log", help="Path to a Plane 2 raw trace log (bst_native_build_tracer.py)")
    standalone_parser.add_argument("output", help="Path to write the Chrome Trace JSON to")

    combined_parser = subparsers.add_parser(
        "combined", help="Plane 1 Chrome Trace JSON + Plane 2 raw trace (same real run) -> one combined JSON",
    )
    combined_parser.add_argument("plane1_json", help="Path to Plane 1's own Chrome Trace JSON (bst_log_to_chrome_trace.py)")
    combined_parser.add_argument("raw_log", help="Path to a Plane 2 raw trace log (element-tagged, UX-23)")
    combined_parser.add_argument("output", help="Path to write the combined Chrome Trace JSON to")
    combined_parser.add_argument(
        "--anchor-element", required=True,
        help="A real element present in both traces, used to correlate Plane 2's CLOCK_MONOTONIC "
             "clock onto Plane 1's own wall-clock timeline.",
    )

    args = parser.parse_args()

    # Local imports (not at module top) - this tool is standalone, single-
    # purpose per this module's own docstring; avoids importing
    # bst_native_build_tracer's argparse/subprocess-heavy CLI machinery
    # just to reuse its two pure parsing functions.
    from tools.bst_native_build_tracer import pair_events, parse_trace_log

    with open(args.raw_log, "r", encoding="utf-8", errors="ignore") as f:
        records = pair_events(parse_trace_log(f.read()))

    if args.command == "standalone":
        output = build_standalone_chrome_trace(records)
    else:
        with open(args.plane1_json, "r", encoding="utf-8") as f:
            plane1_trace_events = json.load(f)
        output = build_combined_chrome_trace(plane1_trace_events, records, args.anchor_element)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote {len(output)} trace events to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
