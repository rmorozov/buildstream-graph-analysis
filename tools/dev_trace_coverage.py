#!/usr/bin/env python3
"""UX-466 stages 1-2: which captured field reaches the emitted trace.

Three planes write records and one trace is emitted from them. Nothing
in the suite reads both ends and says which captured field arrives as a
slice, a track, a debug annotation, a category or a counter - and which
is held by the capture and dropped on the way. `UX-356` asked that
question of the *element join* and found it worth a row; it has never
been asked of the trace.

**Both ends are emitted artifacts.** The sources are the capture's own
JSON; the destination is the bytes `bga timeline` writes, decoded. No
step reads a Python source file for the name of anything, which is the
failure this instrument exists to avoid making - a text scan cannot
tell a field the code emits from a field it merely mentions (fixing
guide §5).

What it cannot assess, declared rather than guessed
---------------------------------------------------
- **Numeric fields.** The census matches *values*, and a number can
  arrive by coincidence: the trace rebases every timestamp, so a
  duration in microseconds may or may not appear as itself. Numeric
  fields are counted and named under `unassessable`, never under
  `reached` or `dropped`.
- **Single-valued fields.** One distinct value cannot discriminate -
  a field holding only `"BUILD"` matches any trace with a `BUILD`
  anywhere. Also `unassessable`.
- **Plane 3 on its own.** A committed capture carries the spine's
  contribution folded into the Plane 2 report (`spine_policy`,
  `stream_coverage.*_from_spine_only`), not as a separate record
  stream. So this reports Plane 3 as the fields of that report which
  name it, and says so - a real spine stream needs a real build, which
  is `UX-466` stage 3 and `UX-465`.
- **Composite fields.** The census matches whole values, so a field
  the trace *decomposes* reads as dropped. `trace.spans[].task_key` is
  the known instance: its value is `uid|kind|phase|attempt` and the
  trace carries the uid as a slice name and the rest elsewhere, so no
  whole task_key appears and the field is reported dropped. Reported
  that way on purpose - "the composite does not arrive" is true, and
  guessing which parts did from substrings would be the text scan this
  instrument exists to avoid.
- **Field numbers.** The decoder takes its field numbers from
  `tools/native_trace/trackevent.py`, the emitter's own module, so it
  catches a value written into the wrong field but not a field number
  that is wrong in both. That is the same limit the test decoders
  carry, and `UX-321`'s pinned fixture is what covers it.

Usage
-----
    python3 tools/dev_trace_coverage.py tests/fixtures/with_timeline
    python3 tools/dev_trace_coverage.py --carriers tests/fixtures/macro_micro
"""
import argparse
import collections
import gzip
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.native_trace import trackevent          # noqa: E402

#: The carriers Perfetto's TrackEvent proto offers for information, and
#: what each one is for. Stage 2's question is which of these the
#: emitted trace uses at all: a field we hold and a carrier we do not
#: use is a mapping gap, and a field we do not hold is a capture gap.
CARRIERS = {
    "slice": "a named interval on a track (TYPE_SLICE_BEGIN/END)",
    "instant": "a named point in time (TYPE_INSTANT)",
    "counter": "a numeric series over time (TYPE_COUNTER)",
    "flow": "an arrow from one slice to another (EVENT_FLOW_IDS)",
    "track": "a named row (TRACK_DESCRIPTOR with a name)",
    "process-track": "a row grouped under a process (TRACK_PROCESS)",
    "thread-track": "a row grouped under a thread (TRACK_THREAD)",
    "category": "a tag a viewer can filter slices by",
    "debug-annotation": "a key/value pair hanging off one slice",
    "counter-unit": "the unit a counter series is measured in",
}

#: Values that match anything and mean nothing. A field whose whole
#: vocabulary is in here cannot discriminate.
NOISE = {"", "true", "false", "none", "null", "0", "1", "yes", "no",
         "unknown", "n/a"}


# --- the capture side -------------------------------------------------

#: Characters a Python identifier cannot hold. A schema key is written
#: by a programmer and is an identifier; a map key is a name from the
#: build - an element uid, a url, a binary like `c++` - and usually is
#: not. See `_is_map`.
NOT_IDENTIFIER = set("./-:+@ ")


def _is_map(node):
    """Whether a dict is a *map* (uid -> record) rather than a record.

    `binary_cost` is keyed by element uid and its keys are data;
    `wall_clock` is a record and its keys are the schema. Collapsing
    the first and keeping the second is what makes a field path mean
    "field" rather than "one element's value".

    Two conditions, and the second is a **heuristic on key spelling**
    rather than a structural fact, so it is stated here rather than
    buried: the values must be homogeneous in type, *and* at least one
    key must hold a character no Python identifier can
    (`NOT_IDENTIFIER`). Homogeneity alone is not enough - it judged
    `{"start_us": 0, "end_us": 9}` a map, because both values are ints,
    and collapsed a record's schema into data. The guard caught that on
    its first run.

    Its known failure mode is the mirror image: a map whose keys are
    all plain identifiers - `{"fetch": ..., "build": ...}` - reads as a
    record, so `queue_summary`'s two phases become two field paths
    instead of one. That mislabels the path; it does not change any
    field's value set, so it cannot change a reached/dropped verdict.
    """
    if not isinstance(node, dict) or len(node) < 2:
        return False
    types = {type(v).__name__ for v in node.values()}
    if len(types) != 1:
        return False
    return any(set(str(key)) & NOT_IDENTIFIER for key in node)


def fields(node, prefix="", out=None):
    """`{field path: set of scalar values}` over one JSON document."""
    out = collections.defaultdict(set) if out is None else out
    if isinstance(node, dict):
        collapse = _is_map(node)
        for key, value in node.items():
            step = "{}" if collapse else key
            fields(value, f"{prefix}.{step}" if prefix else step, out)
            if collapse:
                out[f"{prefix}.{{}}#key" if prefix else "{}#key"].add(key)
    elif isinstance(node, list):
        for item in node:
            fields(item, f"{prefix}[]", out)
    elif node is not None:
        out[prefix].add(node)
    return out


#: Which file belongs to which plane. Plane 3's records are not a file
#: of their own in a committed capture - see the module docstring.
PLANE_FILES = {
    "1": ("run/run-context.json", "run/graph.json", "run/trace.json"),
    "2": ("plane2.json", "run/plane2.json"),
}


def capture_fields(capture):
    """`{plane: {field path: values}}` for one capture directory."""
    found = {}
    for plane, names in PLANE_FILES.items():
        merged = collections.defaultdict(set)
        for name in names:
            path = capture / name
            if not path.is_file():
                continue
            document = json.loads(path.read_text(encoding="utf-8"))
            label = pathlib.Path(name).stem
            fields(document, prefix=label, out=merged)
        if merged:
            found[plane] = dict(merged)
    return found


# --- the trace side ---------------------------------------------------

def _wire_fields(buf):
    """`(field number, wire type, value)` over one encoded message."""
    index = 0
    while index < len(buf):
        key, index = _varint(buf, index)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, index = _varint(buf, index)
        elif wire == 2:
            length, index = _varint(buf, index)
            value, index = buf[index:index + length], index + length
        elif wire == 1:
            value, index = buf[index:index + 8], index + 8
        elif wire == 5:
            value, index = buf[index:index + 4], index + 4
        else:
            raise ValueError(f"unknown wire type {wire} at byte {index}")
        yield field, wire, value


def _varint(buf, index):
    shift = result = 0
    while True:
        byte = buf[index]
        index += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, index
        shift += 7


def decode(path):
    """`(vocabulary, carriers used)` from the emitted trace's bytes.

    The vocabulary is every string the trace carries anywhere a reader
    can see it - slice and track names, category names, annotation keys
    and their string values. That is the set a captured field's values
    have to land in to have arrived.
    """
    raw = (gzip.open(path, "rb").read() if _gzipped(path)
           else path.read_bytes())
    packets = [v for f, _w, v in _wire_fields(raw)
               if f == trackevent.TRACE_PACKET]
    interned = {trackevent.INTERNED_EVENT_NAMES: {},
                trackevent.INTERNED_EVENT_CATEGORIES: {},
                trackevent.INTERNED_DEBUG_ANNOTATION_NAMES: {}}
    vocabulary, used = set(), set()
    annotation_iids, name_iids, category_iids = [], [], []

    for packet in packets:
        for field, _wire, value in _wire_fields(packet):
            if field == trackevent.PACKET_INTERNED_DATA:
                _read_interned(value, interned)
            elif field == trackevent.PACKET_TRACK_DESCRIPTOR:
                _read_track(value, vocabulary, used)
            elif field == trackevent.PACKET_TRACK_EVENT:
                _read_event(value, vocabulary, used,
                            annotation_iids, name_iids, category_iids)

    names = interned[trackevent.INTERNED_EVENT_NAMES]
    categories = interned[trackevent.INTERNED_EVENT_CATEGORIES]
    annotations = interned[trackevent.INTERNED_DEBUG_ANNOTATION_NAMES]
    vocabulary |= {names[i] for i in name_iids if i in names}
    vocabulary |= {categories[i] for i in category_iids if i in categories}
    vocabulary |= {annotations[i] for i in annotation_iids if i in annotations}
    if any(i in categories for i in category_iids):
        used.add("category")
    return {v for v in vocabulary if v}, used


def _gzipped(path):
    with open(path, "rb") as handle:
        return handle.read(2) == b"\x1f\x8b"


def _read_interned(buf, tables):
    for field, _wire, value in _wire_fields(buf):
        table = tables.get(field)
        if table is None:
            continue
        iid = name = None
        for inner, _w, payload in _wire_fields(value):
            if inner == 1:
                iid = payload
            elif inner == 2:
                name = payload.decode("utf-8", "replace")
        if iid is not None:
            table[iid] = name


def _read_track(buf, vocabulary, used):
    used.add("track")
    for field, _wire, value in _wire_fields(buf):
        if field == trackevent.TRACK_NAME:
            vocabulary.add(value.decode("utf-8", "replace"))
        elif field == trackevent.TRACK_PROCESS:
            used.add("process-track")
            for inner, _w, payload in _wire_fields(value):
                if inner == trackevent.PROCESS_NAME:
                    vocabulary.add(payload.decode("utf-8", "replace"))
        elif field == trackevent.TRACK_THREAD:
            used.add("thread-track")
            for inner, _w, payload in _wire_fields(value):
                if inner == trackevent.THREAD_NAME:
                    vocabulary.add(payload.decode("utf-8", "replace"))
        elif field == trackevent.TRACK_COUNTER:
            used.add("counter")
            for inner, _w, payload in _wire_fields(value):
                if inner == trackevent.COUNTER_UNIT_NAME:
                    used.add("counter-unit")
                    vocabulary.add(payload.decode("utf-8", "replace"))


def _read_event(buf, vocabulary, used, annotation_iids, name_iids,
                category_iids):
    for field, _wire, value in _wire_fields(buf):
        if field == trackevent.EVENT_TYPE:
            if value == trackevent.TYPE_SLICE_BEGIN:
                used.add("slice")
            elif value == trackevent.TYPE_INSTANT:
                used.add("instant")
            elif value == trackevent.TYPE_COUNTER:
                used.add("counter")
        elif field == trackevent.EVENT_NAME_IID:
            name_iids.append(value)
        elif field == trackevent.EVENT_CATEGORY_IIDS:
            category_iids.append(value)
        elif field in (trackevent.EVENT_FLOW_IDS,
                       trackevent.EVENT_TERMINATING_FLOW_IDS):
            used.add("flow")
        elif field == trackevent.EVENT_DEBUG_ANNOTATIONS:
            used.add("debug-annotation")
            for inner, _w, payload in _wire_fields(value):
                if inner == trackevent.ANNOTATION_NAME_IID:
                    annotation_iids.append(payload)
                elif inner == trackevent.ANNOTATION_STRING_VALUE:
                    vocabulary.add(payload.decode("utf-8", "replace"))


def emit_trace(capture, out_dir):
    """Run the shipped `bga timeline` over one capture."""
    target = pathlib.Path(out_dir) / "timeline.pftrace"
    done = subprocess.run(
        [sys.executable, "-m", "tools.bga_timeline", str(capture),
         "-o", str(target)],
        cwd=str(REPO), capture_output=True, text=True)
    if done.returncode != 0 or not target.is_file():
        return None, (done.stderr or done.stdout).strip().splitlines()[-1:]
    return target, None


# --- the census -------------------------------------------------------

def assess(values):
    """`(verdict, reason)` for one field's value set."""
    strings = {str(v) for v in values
               if isinstance(v, str) and str(v).lower() not in NOISE}
    if not strings:
        return "unassessable", "no string values a trace could carry"
    if len(strings) < 2:
        return "unassessable", "one distinct value cannot discriminate"
    return "assessable", strings


def coverage(capture, vocabulary):
    """`{plane: {verdict: [(field, detail)]}}` for one capture."""
    report = {}
    for plane, found in sorted(capture_fields(capture).items()):
        buckets = collections.defaultdict(list)
        for field, values in sorted(found.items()):
            verdict, detail = assess(values)
            if verdict == "unassessable":
                buckets["unassessable"].append((field, detail))
                continue
            landed = detail & vocabulary
            if landed:
                buckets["reached"].append(
                    (field, f"{len(landed)}/{len(detail)} value(s) in the trace"))
            else:
                buckets["dropped"].append(
                    (field, f"0/{len(detail)} value(s) in the trace"))
        report[plane] = dict(buckets)
    return report


def render(capture, report, used, show_fields=True):
    lines = [f"capture: {capture}"]
    for plane, buckets in sorted(report.items()):
        reached = buckets.get("reached", [])
        dropped = buckets.get("dropped", [])
        unassessable = buckets.get("unassessable", [])
        lines.append(
            f"\nPlane {plane}: {len(reached)} reached, {len(dropped)} dropped, "
            f"{len(unassessable)} unassessable")
        if show_fields:
            for field, detail in dropped:
                lines.append(f"    DROPPED   {field}  ({detail})")
            for field, detail in reached:
                lines.append(f"    reached   {field}  ({detail})")
    lines.append("\nPerfetto carriers this trace uses:")
    for name, what in sorted(CARRIERS.items()):
        mark = "used  " if name in used else "UNUSED"
        lines.append(f"    {mark}  {name:18} {what}")
    return "\n".join(lines)


def drawable(root=REPO, tracked_only=True):
    """The captures a timeline can be drawn from, and why the rest cannot.

    `bga timeline` needs the wrapped BuildStream log, which a snapshot
    keeps and an imported or generated run directory does not. So the
    population this census can speak about is smaller than the
    population of captures, and naming the difference is the point -
    `UX-376`'s rule, that a census says what it could not assess.
    """
    from tools.dev_finding_coverage import captures, label

    can, cannot = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for run in captures(root, tracked_only=tracked_only):
            capture = run.parent                     # the snapshot, not `run/`
            trace, complaint = emit_trace(capture, tmp)
            if trace is None:
                cannot.append((label(run, root), _why(complaint)))
            else:
                can.append((label(run, root), capture, decode(trace)))
    return can, cannot


def _why(complaint):
    text = " ".join(complaint or ()) or "bga timeline wrote nothing"
    if "no build.log" in text:
        return "no build.log: an imported run directory, not a snapshot"
    return text[:110]


def survey(root=REPO, tracked_only=True):
    """Stage 1 and 2 over every capture a clone has."""
    can, cannot = drawable(root, tracked_only=tracked_only)
    planes_seen = collections.Counter()
    carriers_seen = set()
    blocks = []
    for name, capture, (vocabulary, used) in can:
        report = coverage(capture, vocabulary)
        planes_seen.update(report.keys())
        carriers_seen |= used
        blocks.append((name, capture, report, used))
    return blocks, cannot, planes_seen, carriers_seen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("capture", nargs="?",
                        help="one capture; default is every capture a clone has")
    parser.add_argument("--carriers", action="store_true",
                        help="stage 2 only: the carrier table, no field list")
    parser.add_argument("--local", action="store_true",
                        help="include captures this machine has and a clone does not")
    args = parser.parse_args(argv)

    if args.capture:
        capture = pathlib.Path(args.capture)
        if not capture.is_absolute():
            capture = REPO / capture
        with tempfile.TemporaryDirectory() as tmp:
            trace, complaint = emit_trace(capture, tmp)
            if trace is None:
                print(f"{capture}: {_why(complaint)}")
                return 1
            vocabulary, used = decode(trace)
        print(render(capture, coverage(capture, vocabulary), used,
                     show_fields=not args.carriers))
        return 0

    blocks, cannot, planes_seen, carriers_seen = survey(
        tracked_only=not args.local)
    for name, _capture, report, used in blocks:
        print(render(name, report, used, show_fields=not args.carriers))
        print()
    scope = "this machine" if args.local else "a clone"
    print(f"({scope}) {len(blocks)} capture(s) can draw a timeline, "
          f"{len(cannot)} cannot")
    for name, why in cannot:
        print(f"  cannot: {name:32} {why}")
    for plane in sorted(PLANE_FILES):
        if plane not in planes_seen:
            print(f"  Plane {plane}: no capture that can draw a timeline "
                  f"carries its records, so nothing measures what it maps to")
    unused = sorted(set(CARRIERS) - carriers_seen)
    if unused:
        print(f"  carriers no capture exercised: {', '.join(unused)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
