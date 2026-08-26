"""UX-298: Perfetto's own trace format, written by the stdlib.

Direction 15 rule 3: **the event artifact is the interchange format of
the tool the events are for.** Until this, `bga`'s timeline was legacy
Chrome JSON - a shape Perfetto tolerates rather than reads - assembled
whole in memory by two converters and regenerated from the raw log on
every handoff. At field scale both properties fail: a 1.5 GB JSON
document, built entire, per conversion.

A Perfetto trace is a **stream**: `Trace` is `repeated TracePacket
packet = 1`, so a file is just length-delimited packets one after the
other. Nothing has to be held, nothing has to be closed off at the end,
and `gzip` compresses it as it goes. That is the whole reason this
module exists.

**No protobuf dependency, and no generated classes.** Direction 15
declines both: the wire format needed here is varints and
length-delimited fields, which is a page of code, and a dependency
whose only use is one writer is a dependency that will outlive its
reason. Every field number below is a named constant carrying the
`.proto` it came from, because a wrong number is the one mistake this
approach can make and it is silent - a decoder simply skips a field it
does not know.

Field numbers were read from the schema itself, at
`https://github.com/google/perfetto` `protos/perfetto/trace/...`, not
from memory:

```text
trace.proto              Trace.packet = 1
trace_packet.proto       timestamp = 8, trusted_packet_sequence_id = 10,
                         track_event = 11, interned_data = 12,
                         sequence_flags = 13, track_descriptor = 60
track_event.proto        category_iids = 3, debug_annotations = 4,
                         type = 9, name_iid = 10,
                         track_uuid = 11, name = 23, counter_value = 30,
                         flow_ids = 47, terminating_flow_ids = 48
                         TYPE_SLICE_BEGIN = 1, TYPE_SLICE_END = 2,
                         TYPE_INSTANT = 3, TYPE_COUNTER = 4
                         EventCategory.iid = 1, EventCategory.name = 2
                         EventName.iid = 1, EventName.name = 2
debug_annotation.proto   DebugAnnotation.name_iid = 1, int_value = 4,
                         string_value = 6
                         DebugAnnotationName.iid = 1, .name = 2
track_descriptor.proto   uuid = 1, name = 2, process = 3, thread = 4,
                         parent_uuid = 5
process_descriptor.proto pid = 1, process_name = 6
thread_descriptor.proto  pid = 1, tid = 2, thread_name = 5
interned_data.proto      event_categories = 1, event_names = 2,
                         debug_annotation_names = 3
```

`UX-309` added `flow_ids`/`terminating_flow_ids` - both `fixed64`,
which is a **different wire type** from every other number here and the
one thing a copy of the varint path would have got silently wrong.
`UX-308` added the second block and the two interning tables beside
it, read the same way: `debug_annotation.proto` and `interned_data.proto`
fetched from the same tree and checked against the fixture's recorded
sha256, not remembered. `track_event.proto` and `interned_data.proto`
came back byte-identical to what `UX-298` pinned, which is the evidence
that the numbers above are still the numbers upstream means.
"""
import gzip
import struct
from typing import Dict

# --- wire types (protobuf encoding, not Perfetto's) ---------------------
WIRE_VARINT = 0
WIRE_FIXED64 = 1
WIRE_LENGTH = 2

# --- Trace ---------------------------------------------------------------
TRACE_PACKET = 1

# --- TracePacket ---------------------------------------------------------
PACKET_TIMESTAMP = 8
PACKET_SEQUENCE_ID = 10
PACKET_TRACK_EVENT = 11
PACKET_INTERNED_DATA = 12
PACKET_SEQUENCE_FLAGS = 13
PACKET_TRACK_DESCRIPTOR = 60

# TracePacket.SequenceFlags. The first packet of a sequence declares
# that nothing before it is referred to; every packet that *uses*
# interned data has to say that it needs the incremental state, or a
# reader is entitled to drop it after a gap.
SEQ_INCREMENTAL_STATE_CLEARED = 1
SEQ_NEEDS_INCREMENTAL_STATE = 2

# --- TrackDescriptor -----------------------------------------------------
TRACK_UUID = 1
TRACK_NAME = 2
TRACK_PROCESS = 3
TRACK_THREAD = 4
TRACK_PARENT_UUID = 5

# --- ProcessDescriptor / ThreadDescriptor --------------------------------
PROCESS_PID = 1
PROCESS_NAME = 6
THREAD_PID = 1
THREAD_TID = 2
THREAD_NAME = 5

# --- TrackEvent ----------------------------------------------------------
EVENT_CATEGORY_IIDS = 3
# UX-308: `repeated DebugAnnotation debug_annotations = 4`. This is the
# field the details panel reads and the field `extract_arg` extracts
# from; without it a slice carries its name and nothing else.
EVENT_DEBUG_ANNOTATIONS = 4
EVENT_TYPE = 9
EVENT_NAME_IID = 10
EVENT_TRACK_UUID = 11
EVENT_COUNTER_VALUE = 30
# UX-309: `repeated fixed64 flow_ids = 47` and `terminating_flow_ids
# = 48`. Note **fixed64**, not varint: upstream's own comment says the
# older varint fields (36 and 42) are deprecated in favour of these,
# and writing a flow id as a varint into field 47 produces a packet a
# reader silently drops. Direction is inferred from timestamps - "the
# earliest event with the same flow ID becomes the source" - so an edge
# is one id on two slices, and the terminating list is what says which
# of them is the end rather than a step on the way.
EVENT_FLOW_IDS = 47
EVENT_TERMINATING_FLOW_IDS = 48

TYPE_SLICE_BEGIN = 1
TYPE_SLICE_END = 2
TYPE_INSTANT = 3
# Reserved rather than used: `UX-300` may publish a resource series, and
# an event stream may carry only what a capture measured.
TYPE_COUNTER = 4

# --- DebugAnnotation -----------------------------------------------------
# The name is a `oneof`: interned (`name_iid`) or literal (`name = 10`).
# Interned, here - a million slices carry the same handful of keys, and
# the key is exactly the kind of repeated short string interning exists
# for.
ANNOTATION_NAME_IID = 1
# The value is a `oneof` too. Two of its arms are used: `int_value`
# (`int64`) for every number, `string_value` for everything else -
# including the exit status, which is a *vocabulary* (`3`, `signal:9`)
# rather than a number. `uint_value = 3` is deliberately not used: one
# signed arm is one decoding rule, and nothing here is large enough for
# the extra bit to matter.
ANNOTATION_INT_VALUE = 4
ANNOTATION_STRING_VALUE = 6

# --- InternedData / EventName / EventCategory / DebugAnnotationName ------
# Each interning table has its own iid space: an `EventName` iid and a
# `DebugAnnotationName` iid of 1 are different names. Three counters,
# not one - sharing one would still decode, and would waste the low
# iids that make the varints short.
INTERNED_EVENT_CATEGORIES = 1
INTERNED_EVENT_NAMES = 2
INTERNED_DEBUG_ANNOTATION_NAMES = 3
EVENT_NAME_IID_FIELD = 1
EVENT_NAME_NAME = 2
EVENT_CATEGORY_IID_FIELD = 1
EVENT_CATEGORY_NAME = 2
DEBUG_ANNOTATION_NAME_IID_FIELD = 1
DEBUG_ANNOTATION_NAME_NAME = 2


def varint(value: int) -> bytes:
    """Base-128, low group first, high bit set on every group but the last."""
    if value < 0:
        # Protobuf encodes a negative int64 as a 10-byte varint of its
        # two's complement. Nothing here emits one - every number `bga`
        # annotates is a count, a duration or a size - but a silent
        # wrong answer is worse than a long encoding, and `int_field`
        # exists so that a future one is not read as 2**64 - n.
        value += 1 << 64
    out = bytearray()
    while True:
        group = value & 0x7F
        value >>= 7
        if value:
            out.append(group | 0x80)
        else:
            out.append(group)
            return bytes(out)


def tag(field: int, wire: int) -> bytes:
    return varint((field << 3) | wire)


def uint_field(field: int, value: int) -> bytes:
    return tag(field, WIRE_VARINT) + varint(value)


def int_field(field: int, value: int) -> bytes:
    """A signed `int64` field. Same wire shape as `uint_field` - the
    difference is the reader's, and naming it at the call site is how a
    negative value stays readable rather than becoming 2**64 - n."""
    return tag(field, WIRE_VARINT) + varint(value)


def bytes_field(field: int, payload: bytes) -> bytes:
    return tag(field, WIRE_LENGTH) + varint(len(payload)) + payload


def string_field(field: int, text: str) -> bytes:
    return bytes_field(field, text.encode("utf-8"))


def fixed64_field(field: int, value: int) -> bytes:
    return tag(field, WIRE_FIXED64) + struct.pack("<Q", value)


class TrackEventWriter:
    """A Perfetto trace, written one packet at a time.

    Holds a name table and a handle. Not the packets: `write` hands each
    one to the file as it is built, which is what makes an arbitrarily
    long capture cost what one packet costs.

    ```python
    with TrackEventWriter(path) as trace:
        lane = trace.process_track("bst", pid=1)
        thread = trace.thread_track("BUILD", parent=lane, pid=1, tid=2)
        trace.slice_begin(ts_ns, thread, "app.bst")
        trace.slice_end(ts_ns + 1000, thread)
    ```
    """

    def __init__(self, path: str, sequence_id: int = 1, compress: bool = True):
        self._handle = (gzip.open(path, "wb", compresslevel=6) if compress
                        else open(path, "wb"))
        self._sequence_id = sequence_id
        # UX-308: three interning tables, each with its own iid space
        # (`InternedData` field number -> {name: iid}) and its own
        # pending queue, because a table's definitions ride on the next
        # packet that refers to them.
        self._tables: Dict[int, Dict[str, int]] = {
            INTERNED_EVENT_NAMES: {},
            INTERNED_EVENT_CATEGORIES: {},
            INTERNED_DEBUG_ANNOTATION_NAMES: {},
        }
        self._pending: Dict[int, list] = {field: [] for field in self._tables}
        self._next_uuid = 1
        self._first = True
        self.packets = 0
        self.slices = 0
        self.tracks = 0

    # -- lifecycle --------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    # -- packets ----------------------------------------------------------
    def _write_packet(self, body: bytes) -> None:
        self._handle.write(bytes_field(TRACE_PACKET, body))
        self.packets += 1

    def _sequence_prefix(self) -> bytes:
        """The two fields every packet on this sequence carries.

        The first packet clears the incremental state - it is the start
        of the sequence and refers to nothing before it - and every
        packet after it declares that it *needs* that state, because the
        names are interned and a reader that dropped the earlier packets
        must know it can no longer resolve them.
        """
        flags = (SEQ_INCREMENTAL_STATE_CLEARED if self._first
                 else SEQ_NEEDS_INCREMENTAL_STATE)
        self._first = False
        return (uint_field(PACKET_SEQUENCE_ID, self._sequence_id)
                + uint_field(PACKET_SEQUENCE_FLAGS, flags))

    # `InternedData` field -> the (iid, name) field numbers of its entry
    # message. All three entry messages happen to be `iid = 1, name = 2`,
    # and they are written out rather than assumed, because "they are the
    # same today" is not a wire guarantee.
    _ENTRY_FIELDS = {
        INTERNED_EVENT_NAMES: (EVENT_NAME_IID_FIELD, EVENT_NAME_NAME),
        INTERNED_EVENT_CATEGORIES: (EVENT_CATEGORY_IID_FIELD,
                                    EVENT_CATEGORY_NAME),
        INTERNED_DEBUG_ANNOTATION_NAMES: (DEBUG_ANNOTATION_NAME_IID_FIELD,
                                          DEBUG_ANNOTATION_NAME_NAME),
    }

    def _intern(self, name: str, table: int = INTERNED_EVENT_NAMES) -> int:
        """The iid for a name in one table, queueing it if it is new.

        Interning is why a million slices of forty distinct commands
        cost forty strings - and why a million slices carrying six
        annotation keys cost six. The definition rides on the next
        packet written, which is the packet that first refers to it, so
        a reader meets the name before it needs it.
        """
        entries = self._tables[table]
        iid = entries.get(name)
        if iid is None:
            iid = entries[name] = len(entries) + 1
            self._pending[table].append((iid, name))
        return iid

    def _take_interned(self) -> bytes:
        if not any(self._pending.values()):
            return b""
        entries = b""
        for table, queued in self._pending.items():
            if not queued:
                continue
            iid_field, name_field = self._ENTRY_FIELDS[table]
            entries += b"".join(
                bytes_field(table,
                            uint_field(iid_field, iid)
                            + string_field(name_field, name))
                for iid, name in queued)
            queued.clear()
        return bytes_field(PACKET_INTERNED_DATA, entries)

    def _annotations(self, annotations) -> bytes:
        """`repeated DebugAnnotation`, one per key, name interned.

        `annotations` is an iterable of `(key, value)` - a sequence
        rather than a mapping, because the order a details panel shows
        them in is the order they are written and that order is a
        decision (`cmd` first: it is the one a reader opened the slice
        for). A `None` value is dropped rather than written as an empty
        string: an annotation that is absent and an annotation that is
        empty say different things, and only the first is true of a
        record that never carried the field.
        """
        out = b""
        for key, value in annotations:
            if value is None:
                continue
            payload = uint_field(ANNOTATION_NAME_IID,
                                 self._intern(key,
                                              INTERNED_DEBUG_ANNOTATION_NAMES))
            if isinstance(value, bool):
                # Before `int`, which `bool` is a subclass of. Written as
                # its word rather than as 0/1, because these are read by
                # a person in a details panel.
                payload += string_field(ANNOTATION_STRING_VALUE,
                                        "true" if value else "false")
            elif isinstance(value, int):
                payload += int_field(ANNOTATION_INT_VALUE, value)
            else:
                payload += string_field(ANNOTATION_STRING_VALUE, str(value))
            out += bytes_field(EVENT_DEBUG_ANNOTATIONS, payload)
        return out

    def _flows(self, flows, terminating_flows) -> bytes:
        """`UX-309`: the ids that make Perfetto draw an arrow.

        A flow is one id on two events, and the UI infers the direction
        from their timestamps - so the caller does not say "from A to
        B", it says "A is in this flow" and "B ends it". The ids are
        **fixed64**, eight bytes each, which is why they use
        `fixed64_field` and not the varint path everything else here
        takes: field 47 with a varint in it is a packet a reader drops
        without complaining.
        """
        return (b"".join(fixed64_field(EVENT_FLOW_IDS, flow)
                         for flow in flows)
                + b"".join(fixed64_field(EVENT_TERMINATING_FLOW_IDS, flow)
                           for flow in terminating_flows))

    def _categories(self, categories) -> bytes:
        """`repeated uint64 category_iids`, which is what makes a class
        of slice filterable in the UI and selectable in SQL."""
        return b"".join(
            uint_field(EVENT_CATEGORY_IIDS,
                       self._intern(category, INTERNED_EVENT_CATEGORIES))
            for category in categories)

    # -- tracks -----------------------------------------------------------
    def _uuid(self) -> int:
        value = self._next_uuid
        self._next_uuid += 1
        return value

    def process_track(self, name: str, pid: int) -> int:
        """A process lane. Returns its uuid, which slices are hung from."""
        uuid = self._uuid()
        descriptor = (
            uint_field(TRACK_UUID, uuid)
            + string_field(TRACK_NAME, name)
            + bytes_field(TRACK_PROCESS,
                          uint_field(PROCESS_PID, pid)
                          + string_field(PROCESS_NAME, name)))
        self._write_packet(self._sequence_prefix()
                           + bytes_field(PACKET_TRACK_DESCRIPTOR, descriptor))
        self.tracks += 1
        return uuid

    def thread_track(self, name: str, parent: int, pid: int, tid: int) -> int:
        """A thread lane inside a process lane."""
        uuid = self._uuid()
        descriptor = (
            uint_field(TRACK_UUID, uuid)
            + string_field(TRACK_NAME, name)
            + bytes_field(TRACK_THREAD,
                          uint_field(THREAD_PID, pid)
                          + uint_field(THREAD_TID, tid)
                          + string_field(THREAD_NAME, name))
            + uint_field(TRACK_PARENT_UUID, parent))
        self._write_packet(self._sequence_prefix()
                           + bytes_field(PACKET_TRACK_DESCRIPTOR, descriptor))
        self.tracks += 1
        return uuid

    # -- events -----------------------------------------------------------
    def slice_begin(self, timestamp_ns: int, track: int, name: str,
                    annotations=(), categories=(),
                    flows=(), terminating_flows=()) -> None:
        """A slice opens, carrying what is known about it.

        `annotations` are `(key, value)` pairs (`UX-308`) - the details
        panel's contents, and what `extract_arg` extracts. They go on
        the **begin**, never on the end: the end of a slice carries no
        name for the same reason, and a reader assembling one slice from
        two packets should have to read one of them.

        `categories` are names, interned; a slice that has one is
        filterable in the UI and selectable in SQL by it.

        `flows` and `terminating_flows` are ids (`UX-309`); a slice in
        both lists for one id would be a flow that is its own end, which
        upstream says not to write, so the caller keeps them disjoint.
        """
        event = (uint_field(EVENT_TYPE, TYPE_SLICE_BEGIN)
                 + uint_field(EVENT_TRACK_UUID, track)
                 + uint_field(EVENT_NAME_IID, self._intern(name))
                 + self._categories(categories)
                 + self._flows(flows, terminating_flows)
                 + self._annotations(annotations))
        self._write_packet(self._sequence_prefix()
                           + uint_field(PACKET_TIMESTAMP, timestamp_ns)
                           + self._take_interned()
                           + bytes_field(PACKET_TRACK_EVENT, event))
        self.slices += 1

    def slice_end(self, timestamp_ns: int, track: int) -> None:
        """The close of the innermost open slice on `track`.

        A `TYPE_SLICE_END` carries no name - the track's own stack
        supplies it - which is the property that makes the format
        appendable: the end of a slice need not know how it began.
        """
        event = (uint_field(EVENT_TYPE, TYPE_SLICE_END)
                 + uint_field(EVENT_TRACK_UUID, track))
        self._write_packet(self._sequence_prefix()
                           + uint_field(PACKET_TIMESTAMP, timestamp_ns)
                           + bytes_field(PACKET_TRACK_EVENT, event))

    def instant(self, timestamp_ns: int, track: int, name: str,
                annotations=(), categories=(),
                flows=(), terminating_flows=()) -> None:
        """A moment rather than a span - what a process with no observed
        exit gets, because a zero-width bar reads as "instantaneous" and
        `bga` does not fabricate an end it never saw.

        It carries the same annotations a slice does: a process whose
        exit was never seen is exactly the one a reader wants the full
        command line of."""
        event = (uint_field(EVENT_TYPE, TYPE_INSTANT)
                 + uint_field(EVENT_TRACK_UUID, track)
                 + uint_field(EVENT_NAME_IID, self._intern(name))
                 + self._categories(categories)
                 + self._flows(flows, terminating_flows)
                 + self._annotations(annotations))
        self._write_packet(self._sequence_prefix()
                           + uint_field(PACKET_TIMESTAMP, timestamp_ns)
                           + self._take_interned()
                           + bytes_field(PACKET_TRACK_EVENT, event))
        self.slices += 1
