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
track_event.proto        category_iids = 3, type = 9, name_iid = 10,
                         track_uuid = 11, name = 23, counter_value = 30
                         TYPE_SLICE_BEGIN = 1, TYPE_SLICE_END = 2,
                         TYPE_INSTANT = 3, TYPE_COUNTER = 4
                         EventName.iid = 1, EventName.name = 2
track_descriptor.proto   uuid = 1, name = 2, process = 3, thread = 4,
                         parent_uuid = 5
process_descriptor.proto pid = 1, process_name = 6
thread_descriptor.proto  pid = 1, tid = 2, thread_name = 5
interned_data.proto      event_names = 2
```
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
EVENT_TYPE = 9
EVENT_NAME_IID = 10
EVENT_TRACK_UUID = 11
EVENT_COUNTER_VALUE = 30

TYPE_SLICE_BEGIN = 1
TYPE_SLICE_END = 2
TYPE_INSTANT = 3
# Reserved rather than used: `UX-300` may publish a resource series, and
# an event stream may carry only what a capture measured.
TYPE_COUNTER = 4

# --- InternedData / EventName --------------------------------------------
INTERNED_EVENT_NAMES = 2
EVENT_NAME_IID_FIELD = 1
EVENT_NAME_NAME = 2


def varint(value: int) -> bytes:
    """Base-128, low group first, high bit set on every group but the last."""
    if value < 0:
        # Protobuf encodes a negative int64 as a 10-byte varint of its
        # two's complement. Nothing here emits one, but a silent wrong
        # answer is worse than a long encoding.
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
        self._names: Dict[str, int] = {}
        self._pending_names: list = []
        self._next_iid = 1
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

    def _intern(self, name: str) -> int:
        """The iid for a name, queueing its definition if it is new.

        Interning is why a million slices of forty distinct commands
        cost forty strings. The definition rides on the next packet
        written, which is the packet that first refers to it - a reader
        meets the name before it needs it.
        """
        iid = self._names.get(name)
        if iid is None:
            iid = self._names[name] = self._next_iid
            self._next_iid += 1
            self._pending_names.append((iid, name))
        return iid

    def _take_interned(self) -> bytes:
        if not self._pending_names:
            return b""
        entries = b"".join(
            bytes_field(INTERNED_EVENT_NAMES,
                        uint_field(EVENT_NAME_IID_FIELD, iid)
                        + string_field(EVENT_NAME_NAME, name))
            for iid, name in self._pending_names)
        self._pending_names.clear()
        return bytes_field(PACKET_INTERNED_DATA, entries)

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
    def slice_begin(self, timestamp_ns: int, track: int, name: str) -> None:
        event = (uint_field(EVENT_TYPE, TYPE_SLICE_BEGIN)
                 + uint_field(EVENT_TRACK_UUID, track)
                 + uint_field(EVENT_NAME_IID, self._intern(name)))
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

    def instant(self, timestamp_ns: int, track: int, name: str) -> None:
        """A moment rather than a span - what a process with no observed
        exit gets, because a zero-width bar reads as "instantaneous" and
        `bga` does not fabricate an end it never saw."""
        event = (uint_field(EVENT_TYPE, TYPE_INSTANT)
                 + uint_field(EVENT_TRACK_UUID, track)
                 + uint_field(EVENT_NAME_IID, self._intern(name)))
        self._write_packet(self._sequence_prefix()
                           + uint_field(PACKET_TIMESTAMP, timestamp_ns)
                           + self._take_interned()
                           + bytes_field(PACKET_TRACK_EVENT, event))
        self.slices += 1
