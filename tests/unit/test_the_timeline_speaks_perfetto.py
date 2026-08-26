"""UX-298: the timeline is Perfetto's own format, written by the stdlib.

Direction 15 rule 3. Until this, `bga`'s timeline was legacy Chrome
JSON - a shape Perfetto tolerates rather than reads - assembled whole in
memory and regenerated from the raw log on every handoff. At field
scale both properties fail: a 1.5 GB JSON document, built entire, per
conversion. A Perfetto trace is `repeated TracePacket packet = 1`, so
it is a stream: packets are appended, gzip compresses as it goes, and
nothing is ever held.

**Why this file carries its own protobuf reader.** No library checks
the writer - there is deliberately no protobuf dependency (Direction 15
declines it: the wire format needed is a page of code) - so the writer
would otherwise be guarded by nothing but its own confidence. The
decoder below is written from the wire rules rather than from the
emitter, so a field the emitter writes into the wrong number is a field
the decoder does not find.

**And why the field numbers have their own fixture.** A wrong field
number is the one mistake this approach can make, and it is *silent*: a
reader skips a field it does not know rather than complaining.
`tests/fixtures/perfetto_field_numbers.json` was extracted from
upstream's own `.proto` files - it records each file's sha256 - and the
guard holds `trackevent.py`'s constants against it. Two copies of one
fact, one of them derived from the schema rather than from memory.
"""
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bga_timeline import (  # noqa: E402
    DEFAULT_OUTPUT, FORMAT_CHROME, FORMAT_TRACKEVENT, render)
from tools.native_trace import trackevent  # noqa: E402

FIELD_NUMBERS = REPO / "tests/fixtures/perfetto_field_numbers.json"
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

_WRAPPED = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""


def _raw(processes=6, elements=2):
    """A Plane 2 log with matched processes and one that never exits."""
    lines = []
    for index in range(processes):
        element = f"work-{chr(ord('a') + index % elements)}.bst"
        pid = 101 + index
        # A handful of command lines, repeated - which is what a build
        # looks like, and what makes interning worth having. A fixture
        # of all-distinct names cannot tell an interned table from one
        # that redefines every name it meets.
        cmd = f"cc -c part{index % 3}.c"
        start = 1000.0 + index * 0.1
        lines.append(f"START pid={pid} ppid=1 ts={start:.6f} "
                     f"element={element} cmd={cmd}\n")
        if index == processes - 1:
            continue          # no observed exit - an instant, not a bar
        lines.append(f"END pid={pid} ppid=1 ts={start + 0.5:.6f} "
                     f"element={element} cmd={cmd}\n")
    return "".join(lines)


def _snapshot(tmp_path, raw=None, name="20260821T120000Z"):
    snapshot = tmp_path / name
    snapshot.mkdir()
    (snapshot / "build.log").write_text(_WRAPPED, encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run")
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as handle:
        handle.write(_raw() if raw is None else raw)
    return snapshot


# --------------------------------------------------------------------------
# A protobuf reader, from the wire rules.
# --------------------------------------------------------------------------
def _varint(buf, index):
    value = shift = 0
    while True:
        byte = buf[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, index
        shift += 7


def _fields(buf):
    """`(field number, wire type, value)` over one encoded message."""
    index = 0
    while index < len(buf):
        key, index = _varint(buf, index)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, index = _varint(buf, index)
        elif wire == 2:
            length, index = _varint(buf, index)
            value = buf[index:index + length]
            index += length
        elif wire == 1:
            value, index = buf[index:index + 8], index + 8
        elif wire == 5:
            value, index = buf[index:index + 4], index + 4
        else:
            raise AssertionError(f"unknown wire type {wire} at byte {index}")
        yield field, wire, value


def decode(path):
    """Tracks, slices and instants, read back out of the bytes."""
    raw = (gzip.open(path, "rb").read() if str(path).endswith(".gz")
           else open(path, "rb").read())
    packets = [value for field, wire, value in _fields(raw)
               if field == trackevent.TRACE_PACKET and wire == 2]
    tracks, slices, instants, names, open_stacks = {}, [], [], {}, {}
    flags = []
    for packet in packets:
        timestamp = event = descriptor = interned = None
        for field, _wire, value in _fields(packet):
            if field == trackevent.PACKET_TIMESTAMP:
                timestamp = value
            elif field == trackevent.PACKET_TRACK_EVENT:
                event = value
            elif field == trackevent.PACKET_TRACK_DESCRIPTOR:
                descriptor = value
            elif field == trackevent.PACKET_INTERNED_DATA:
                interned = value
            elif field == trackevent.PACKET_SEQUENCE_FLAGS:
                flags.append(value)
        if interned is not None:
            for field, _wire, value in _fields(interned):
                if field != trackevent.INTERNED_EVENT_NAMES:
                    continue
                iid = name = None
                for inner, _w, payload in _fields(value):
                    if inner == trackevent.EVENT_NAME_IID_FIELD:
                        iid = payload
                    elif inner == trackevent.EVENT_NAME_NAME:
                        name = payload.decode("utf-8")
                names[iid] = name
        if descriptor is not None:
            uuid = name = parent = None
            kind = "track"
            for field, _wire, value in _fields(descriptor):
                if field == trackevent.TRACK_UUID:
                    uuid = value
                elif field == trackevent.TRACK_NAME:
                    name = value.decode("utf-8")
                elif field == trackevent.TRACK_PROCESS:
                    kind = "process"
                elif field == trackevent.TRACK_THREAD:
                    kind = "thread"
                elif field == trackevent.TRACK_PARENT_UUID:
                    parent = value
            tracks[uuid] = {"name": name, "parent": parent, "kind": kind}
        if event is not None:
            kind = track = iid = None
            for field, _wire, value in _fields(event):
                if field == trackevent.EVENT_TYPE:
                    kind = value
                elif field == trackevent.EVENT_TRACK_UUID:
                    track = value
                elif field == trackevent.EVENT_NAME_IID:
                    iid = value
            if kind == trackevent.TYPE_SLICE_BEGIN:
                open_stacks.setdefault(track, []).append((timestamp, iid))
            elif kind == trackevent.TYPE_SLICE_END:
                start, started_as = open_stacks[track].pop()
                slices.append({"track": track, "name": names.get(started_as),
                               "start_ns": start, "end_ns": timestamp,
                               "dur_ns": timestamp - start})
            elif kind == trackevent.TYPE_INSTANT:
                instants.append({"track": track, "name": names.get(iid),
                                 "ts": timestamp})
    return {"packets": len(packets), "tracks": tracks, "slices": slices,
            "instants": instants, "names": names, "flags": flags,
            "unclosed": {k: v for k, v in open_stacks.items() if v}}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("perfetto")
    snapshot = _snapshot(tmp)
    out = tmp / DEFAULT_OUTPUT[FORMAT_TRACKEVENT]
    result = render(str(snapshot), str(out))
    return {"snapshot": snapshot, "path": out, "result": result,
            "trace": decode(out)}


class TestTheWireFormatIsTheOneUpstreamDeclares:
    """The clause that makes every other clause mean something. A field
    number is not checkable by running the code - a reader skips what it
    does not recognise - so it is checked against the schema."""

    @pytest.fixture
    def upstream(self):
        return json.loads(FIELD_NUMBERS.read_text(encoding="utf-8"))

    def test_every_constant_matches_the_schema(self, upstream):
        expected = {
            ("trace.proto", "Trace", "packet"): trackevent.TRACE_PACKET,
            ("trace_packet.proto", "TracePacket", "timestamp"):
                trackevent.PACKET_TIMESTAMP,
            ("trace_packet.proto", "TracePacket", "trusted_packet_sequence_id"):
                trackevent.PACKET_SEQUENCE_ID,
            ("trace_packet.proto", "TracePacket", "track_event"):
                trackevent.PACKET_TRACK_EVENT,
            ("trace_packet.proto", "TracePacket", "interned_data"):
                trackevent.PACKET_INTERNED_DATA,
            ("trace_packet.proto", "TracePacket", "sequence_flags"):
                trackevent.PACKET_SEQUENCE_FLAGS,
            ("trace_packet.proto", "TracePacket", "track_descriptor"):
                trackevent.PACKET_TRACK_DESCRIPTOR,
            ("trace_packet.proto", "SequenceFlags",
             "SEQ_INCREMENTAL_STATE_CLEARED"):
                trackevent.SEQ_INCREMENTAL_STATE_CLEARED,
            ("trace_packet.proto", "SequenceFlags",
             "SEQ_NEEDS_INCREMENTAL_STATE"):
                trackevent.SEQ_NEEDS_INCREMENTAL_STATE,
            ("track_event.proto", "TrackEvent", "category_iids"):
                trackevent.EVENT_CATEGORY_IIDS,
            ("track_event.proto", "TrackEvent", "type"): trackevent.EVENT_TYPE,
            ("track_event.proto", "TrackEvent", "name_iid"):
                trackevent.EVENT_NAME_IID,
            ("track_event.proto", "TrackEvent", "track_uuid"):
                trackevent.EVENT_TRACK_UUID,
            ("track_event.proto", "TrackEvent", "counter_value"):
                trackevent.EVENT_COUNTER_VALUE,
            ("track_event.proto", "Type", "TYPE_SLICE_BEGIN"):
                trackevent.TYPE_SLICE_BEGIN,
            ("track_event.proto", "Type", "TYPE_SLICE_END"):
                trackevent.TYPE_SLICE_END,
            ("track_event.proto", "Type", "TYPE_INSTANT"):
                trackevent.TYPE_INSTANT,
            ("track_event.proto", "Type", "TYPE_COUNTER"):
                trackevent.TYPE_COUNTER,
            ("track_event.proto", "EventName", "iid"):
                trackevent.EVENT_NAME_IID_FIELD,
            ("track_event.proto", "EventName", "name"):
                trackevent.EVENT_NAME_NAME,
            ("track_descriptor.proto", "TrackDescriptor", "uuid"):
                trackevent.TRACK_UUID,
            ("track_descriptor.proto", "TrackDescriptor", "name"):
                trackevent.TRACK_NAME,
            ("track_descriptor.proto", "TrackDescriptor", "process"):
                trackevent.TRACK_PROCESS,
            ("track_descriptor.proto", "TrackDescriptor", "thread"):
                trackevent.TRACK_THREAD,
            ("track_descriptor.proto", "TrackDescriptor", "parent_uuid"):
                trackevent.TRACK_PARENT_UUID,
            ("process_descriptor.proto", "ProcessDescriptor", "pid"):
                trackevent.PROCESS_PID,
            ("process_descriptor.proto", "ProcessDescriptor", "process_name"):
                trackevent.PROCESS_NAME,
            ("thread_descriptor.proto", "ThreadDescriptor", "pid"):
                trackevent.THREAD_PID,
            ("thread_descriptor.proto", "ThreadDescriptor", "tid"):
                trackevent.THREAD_TID,
            ("thread_descriptor.proto", "ThreadDescriptor", "thread_name"):
                trackevent.THREAD_NAME,
            ("interned_data.proto", "InternedData", "event_names"):
                trackevent.INTERNED_EVENT_NAMES,
            # UX-308: annotations, categories, and the two interning
            # tables they need.
            ("track_event.proto", "TrackEvent", "debug_annotations"):
                trackevent.EVENT_DEBUG_ANNOTATIONS,
            ("track_event.proto", "EventCategory", "iid"):
                trackevent.EVENT_CATEGORY_IID_FIELD,
            ("track_event.proto", "EventCategory", "name"):
                trackevent.EVENT_CATEGORY_NAME,
            ("debug_annotation.proto", "DebugAnnotation", "name_iid"):
                trackevent.ANNOTATION_NAME_IID,
            ("debug_annotation.proto", "DebugAnnotation", "int_value"):
                trackevent.ANNOTATION_INT_VALUE,
            ("debug_annotation.proto", "DebugAnnotation", "string_value"):
                trackevent.ANNOTATION_STRING_VALUE,
            ("debug_annotation.proto", "DebugAnnotationName", "iid"):
                trackevent.DEBUG_ANNOTATION_NAME_IID_FIELD,
            ("debug_annotation.proto", "DebugAnnotationName", "name"):
                trackevent.DEBUG_ANNOTATION_NAME_NAME,
            ("interned_data.proto", "InternedData", "event_categories"):
                trackevent.INTERNED_EVENT_CATEGORIES,
            ("interned_data.proto", "InternedData", "debug_annotation_names"):
                trackevent.INTERNED_DEBUG_ANNOTATION_NAMES,
            # UX-309: flows. Both `fixed64`, which is a different wire
            # type from every other number pinned here.
            ("track_event.proto", "TrackEvent", "flow_ids"):
                trackevent.EVENT_FLOW_IDS,
            ("track_event.proto", "TrackEvent", "terminating_flow_ids"):
                trackevent.EVENT_TERMINATING_FLOW_IDS,
        }
        wrong = []
        for (proto, block, field), ours in expected.items():
            theirs = upstream["files"][proto]["numbers"][block][field]
            if theirs != ours:
                wrong.append((proto, block, field, ours, theirs))
        assert wrong == [], wrong
        # Non-vacuity: the table above must cover what the module pins,
        # or a constant could drift with nothing noticing.
        pinned = {name for name in dir(trackevent)
                  if name.isupper() and not name.startswith("WIRE_")}
        assert len(expected) >= len(pinned) - 1, (
            f"{len(pinned)} constants pinned, {len(expected)} checked")

    def test_the_fixture_says_where_it_came_from(self, upstream):
        assert "perfetto" in upstream["source"]
        for proto, entry in upstream["files"].items():
            assert len(entry["sha256"]) == 64, proto

    def test_a_varint_is_a_varint(self):
        """The one encoding rule everything else rests on, against
        vectors worked by hand: base 128, low group first, high bit set
        on every group but the last."""
        for value, encoded in ((0, b"\x00"), (1, b"\x01"), (127, b"\x7f"),
                               (128, b"\x80\x01"), (300, b"\xac\x02"),
                               (16384, b"\x80\x80\x01")):
            assert trackevent.varint(value) == encoded, value
        # A length-delimited field is tag, length, bytes - and the tag
        # is (field << 3 | 2).
        assert trackevent.bytes_field(1, b"ab") == b"\x0a\x02ab"


class TestTheTraceSaysWhatTheCaptureSaw:

    def test_both_planes_are_in_it(self, rendered):
        result = rendered["result"]
        assert result["planes"] == ["1", "2"]
        assert result["format"] == FORMAT_TRACKEVENT
        assert result["anchor"]

    def test_the_lanes_are_the_two_planes(self, rendered):
        tracks = rendered["trace"]["tracks"]
        processes = {t["name"] for t in tracks.values() if t["kind"] == "process"}
        assert "Plane 1: BuildStream" in processes
        assert any(name.startswith("native: ") for name in processes), processes
        # Every thread track hangs off a process track, which is what
        # gives Perfetto the hierarchy to draw.
        for track in tracks.values():
            if track["kind"] == "thread":
                assert track["parent"] in tracks, track

    def test_every_slice_closes(self, rendered):
        """A `TYPE_SLICE_END` with no begin, or a begin never ended, is
        a trace that draws wrong rather than one that fails to open."""
        assert rendered["trace"]["unclosed"] == {}
        assert rendered["trace"]["slices"], "no slices at all"

    def test_the_plane_2_slices_are_the_processes_the_report_counted(
            self, rendered, tmp_path):
        """The acceptance test's equality: what the trace draws is what
        the published report counted, element by element - asserted, not
        eyeballed."""
        from tools.bst_native_build_tracer import load_and_summarize

        log = tmp_path / "plane2.log"
        with gzip.open(rendered["snapshot"] / "plane2.log.gz", "rt") as handle:
            log.write_text(handle.read(), encoding="utf-8")
        report = load_and_summarize(str(log))

        tracks = rendered["trace"]["tracks"]

        def element_of(track_uuid):
            track = tracks[track_uuid]
            parent = tracks.get(track["parent"]) if track["parent"] else None
            name = (parent or track)["name"] or ""
            return name[len("native: "):] if name.startswith("native: ") else None

        drawn = {}
        for event in rendered["trace"]["slices"] + rendered["trace"]["instants"]:
            element = element_of(event["track"])
            if element:
                drawn[element] = drawn.get(element, 0) + 1
        assert drawn == report["by_element"], (drawn, report["by_element"])
        assert sum(drawn.values()) == report["process_count"]

    def test_a_process_with_no_observed_exit_is_an_instant(self, rendered):
        """`UX-188`'s rule, carried over: never a zero-width bar and
        never a fabricated end."""
        instants = rendered["trace"]["instants"]
        assert len(instants) == 1, instants
        assert "no observed exit" in instants[0]["name"]

    def test_the_names_are_interned_once_each(self, rendered):
        """What makes a million slices of forty commands cost forty
        strings. Every slice resolves to a name, and no name is defined
        twice - which the fixture can only show because its command
        lines repeat."""
        names = rendered["trace"]["names"]
        assert names, "nothing was interned"
        assert len(set(names.values())) == len(names), names
        slices = rendered["trace"]["slices"]
        assert len(slices) > len(names), (
            f"{len(slices)} slices over {len(names)} names - this fixture "
            "does not repeat a name, so it cannot show interning at all")
        for entry in slices:
            assert entry["name"], entry

    def test_one_name_is_one_definition(self, tmp_path):
        """Directly, on the writer: the same name twice is one entry in
        the table and one iid on the wire."""
        path = tmp_path / "interned.perfetto-trace.gz"
        with trackevent.TrackEventWriter(str(path)) as writer:
            lane = writer.process_track("lane", pid=1)
            track = writer.thread_track("thread", parent=lane, pid=1, tid=2)
            for index in range(6):
                writer.slice_begin(index * 10, track, "cc -c a.c")
                writer.slice_end(index * 10 + 5, track)
        trace = decode(path)
        assert list(trace["names"].values()) == ["cc -c a.c"], trace["names"]
        assert len(trace["slices"]) == 6
        assert {entry["name"] for entry in trace["slices"]} == {"cc -c a.c"}

    def test_the_sequence_declares_its_incremental_state(self, rendered):
        """Interned data is per packet sequence: the first packet says
        it refers to nothing earlier, and every packet after it says it
        needs that state. A reader that met a gap has to know."""
        flags = rendered["trace"]["flags"]
        assert flags[0] == trackevent.SEQ_INCREMENTAL_STATE_CLEARED
        assert set(flags[1:]) == {trackevent.SEQ_NEEDS_INCREMENTAL_STATE}

    def test_the_two_planes_are_aligned_on_the_anchor(self, rendered):
        """Plane 2's monotonic clock placed on Plane 1's wall clock -
        the traced process must land *inside* the element's build task,
        which is the only thing the alignment is for."""
        tracks = rendered["trace"]["tracks"]
        build = [s for s in rendered["trace"]["slices"]
                 if (s["name"] or "").startswith("work-a.bst")]
        assert build, "no Plane 1 build slice for the anchor element"
        native = [s for s in rendered["trace"]["slices"]
                  if (tracks[tracks[s["track"]]["parent"]]["name"] or "")
                  == "native: work-a.bst"]
        assert native, "no Plane 2 slice for the anchor element"
        task = build[0]
        for entry in native:
            assert task["start_ns"] <= entry["start_ns"] <= task["end_ns"], (
                task, entry)


class TestTheBytesAreStable:

    def test_the_same_input_twice_is_the_same_trace(self, tmp_path):
        """The acceptance test's digest clause. Gzip stamps a
        modification time into its header, so the comparison is of the
        decompressed stream - the trace, not its wrapper."""
        snapshot = _snapshot(tmp_path)
        digests = []
        for run in range(2):
            out = tmp_path / f"run{run}.perfetto-trace.gz"
            render(str(snapshot), str(out))
            with gzip.open(out, "rb") as handle:
                digests.append(hashlib.sha256(handle.read()).hexdigest())
        assert digests[0] == digests[1], digests


class TestTheLegacyPathIsStillThere:

    def test_chrome_json_is_still_written_on_request(self, tmp_path):
        """`chrome://tracing` users, and any pipeline that already parses
        the JSON. The item keeps it as the compatibility path, which
        means it has to still work rather than still exist."""
        snapshot = _snapshot(tmp_path)
        out = tmp_path / "timeline.json"
        result = render(str(snapshot), str(out), fmt=FORMAT_CHROME)
        assert result["format"] == FORMAT_CHROME
        events = json.loads(out.read_text(encoding="utf-8"))
        assert any(event.get("ph") == "X" for event in events)

    def test_the_two_formats_place_a_process_at_the_same_instant(
            self, tmp_path):
        """One number decides whether the planes line up, and both
        formats reach it through the same function. Measured here rather
        than trusted: the same process, the same microsecond."""
        snapshot = _snapshot(tmp_path)
        chrome_path = tmp_path / "t.json"
        trace_path = tmp_path / "t.perfetto-trace.gz"
        render(str(snapshot), str(chrome_path), fmt=FORMAT_CHROME)
        render(str(snapshot), str(trace_path), fmt=FORMAT_TRACKEVENT)

        chrome = {event["name"]: (event["ts"], event["dur"])
                  for event in json.loads(chrome_path.read_text())
                  if event.get("ph") == "X"}
        trace = decode(trace_path)
        tracks = trace["tracks"]
        native = {s["name"]: (s["start_ns"] / 1000, s["dur_ns"] / 1000)
                  for s in trace["slices"]
                  if (tracks[tracks[s["track"]]["parent"]]["name"] or "")
                  .startswith("native: ")}
        assert native, "no Plane 2 slices in the TrackEvent trace"
        assert native == {k: v for k, v in chrome.items() if k in native}

    def test_an_unknown_format_is_refused_by_name(self, tmp_path):
        snapshot = _snapshot(tmp_path)
        with pytest.raises(ValueError) as raised:
            render(str(snapshot), str(tmp_path / "x"), fmt="protobuf")
        assert "trackevent" in str(raised.value)


_MEASURE = textwrap.dedent("""
    import json, sys, time
    sys.path.insert(0, %(repo)r)
    from tools.bga_timeline import render
    def peak_mb():
        for line in open("/proc/self/status"):
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) / 1024
        return 0.0
    start = time.time()
    result = render(%(snapshot)r, %(output)r)
    print(json.dumps({"seconds": time.time() - start, "peak_mb": peak_mb(),
                      "slices": result["slices"]}))
""")

# A coarse regression alarm, not the streaming proof. Measured on the
# fixture below (40,000 processes): 82.4 MB, of which the interpreter
# with this repository imported is ~39 MB and most of the rest is the
# event list `pair_events` has to sort (`UX-297`'s floor, which this
# item does not move). The emitter's own state is a name table and one
# entry per lane.
#
# It is a *ceiling*, and a ceiling cannot prove streaming: measured, a
# writer that buffered every packet would add ~10 MB at this size and
# pass it comfortably. What discriminates is the clause below it -
# bytes on disk while the writer is still open, which nothing that
# buffers can satisfy.
STREAM_RSS_CEILING_MB = 120.0


class TestTheEmitterStreams:

    def test_the_bytes_are_on_disk_before_the_writer_is_closed(self, tmp_path):
        """The discriminating clause. `Trace` is `repeated TracePacket`,
        so a packet is complete the moment it is written and the file is
        valid at every point - which is the whole reason for the format.
        An emitter that assembled the trace and wrote it at the end
        would leave this file at zero bytes until `close`."""
        path = tmp_path / "streaming.perfetto-trace.gz"
        writer = trackevent.TrackEventWriter(str(path))
        lane = writer.process_track("lane", pid=1)
        track = writer.thread_track("thread", parent=lane, pid=1, tid=2)
        midway = 0
        for index in range(20_000):
            writer.slice_begin(index * 1000, track, f"cmd {index % 40}")
            writer.slice_end(index * 1000 + 500, track)
            if index == 10_000:
                midway = path.stat().st_size
        assert midway > 0, (
            "nothing had reached the file after 10,000 slices - the writer "
            "is holding the trace rather than streaming it")
        writer.close()
        assert path.stat().st_size > midway
        assert len(decode(path)["slices"]) == 20_000

    def test_a_big_capture_stays_inside_the_ceiling(self, tmp_path):
        snapshot = _snapshot(tmp_path, raw=_raw(processes=40_000, elements=20))
        out = tmp_path / "big.perfetto-trace.gz"
        done = subprocess.run(
            [sys.executable, "-c", _MEASURE % {
                "repo": str(REPO), "snapshot": str(snapshot),
                "output": str(out)}],
            capture_output=True, text=True, cwd=REPO, timeout=900)
        assert done.returncode == 0, done.stderr[-3000:]
        measured = json.loads(done.stdout.strip().splitlines()[-1])
        assert measured["slices"] >= 40_000, measured
        assert measured["peak_mb"] < STREAM_RSS_CEILING_MB, measured
        # And the file is real: it decodes, and every slice closes.
        assert os.path.getsize(out) > 0
        trace = decode(out)
        assert trace["unclosed"] == {}
        assert len(trace["slices"]) + len(trace["instants"]) >= 40_000
