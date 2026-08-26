"""UX-309: the arrows a timeline exists for.

An element ends, another begins, and whether that adjacency is
*causation* is exactly what `graph.json` knows and the trace never said.
Perfetto's vocabulary for it is **flows**, and the UI draws them as
arrows. Two relations qualify and only two: `graph.json`'s dependency
edges (Plane 1) and `ppid` inside one sandbox (Plane 2). There is no
captured relation between one element's process and another's, so
there is no flow between them - a flow that invented causation would be
a lie the UI draws in bold, and the clause that says so is below.

**A flow is one id on two slices**, and upstream is explicit that "the
earliest event with the same flow ID becomes the source". So the
direction is not something the writer states; it is something the
timestamps decide. That is the one way this can say something false -
an edge whose two slices are in the wrong time order is drawn
**backwards** - so an edge whose source does not begin strictly before
its sink is dropped and counted rather than guessed at. On
`examples/06` two edges are dropped for exactly this reason:
`toolchain.bst` is instantaneous and its two dependents begin in the
same microsecond it does, so nothing in the capture says which came
first.

**The wire type is the trap.** `flow_ids = 47` and
`terminating_flow_ids = 48` are `repeated fixed64` - eight raw bytes,
not a varint - and they replaced deprecated varint fields at 36 and 42.
A varint written into field 47 is a packet a reader drops without
complaining, which is why the decoding below asserts the wire type and
not only the value.

**What it costs**, measured on two captures, the same snapshot rendered
by this tree and by the commit before it:

```text
                       slices    flows    packets       raw        gzipped
examples/06               825      836   2,335 = 2,335  +16,930 B  +6,425 B
synthetic, 20k procs   20,801   20,058  62,804 = 62,804 +401,988 B +172,696 B
```

**Zero extra packets** at both scales - a flow id rides the slice
packet that already exists - and 20.0 B per flow uncompressed, 8.6 B
compressed. That is the argument for the bound being *no bound*: every
edge whose two ends both have slices is emitted, because the thing a
cap would buy is not size. What a cap would buy is a less crowded
picture, and that is Perfetto's own UI to decide.
"""
import gzip
import hashlib
import json
import pathlib
import shutil
import struct
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from tools.bga_timeline import (  # noqa: E402
    DEFAULT_OUTPUT, FORMAT_TRACKEVENT, dependency_edges, render)
from tools.native_trace import trackevent  # noqa: E402

from test_the_timeline_speaks_perfetto import _fields  # noqa: E402

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
REAL_CAPTURE = REPO / ("examples/06-macro-micro-optimization/.bga/runs/"
                       "20260821T170127Z")

# Three elements in a chain and one off it, with a `bst`-shaped log.
# `top.bst` is instantaneous and **begins** in the same millisecond
# `mid.bst` does, which is the tie the drop rule exists for: the flow
# ids ride the begin events, so it is the begins Perfetto compares, and
# two equal ones say nothing about which came first.
_LOG = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:01,100] INFO: [00:00:01][aaaaaaaa][   build:top.bst] START Building
[wrapper][2026-08-21 12:00:01,100] INFO: [00:00:01][aaaaaaaa][   build:top.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:01,100] INFO: [00:00:01][bbbbbbbb][   build:mid.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][bbbbbbbb][   build:mid.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][cccccccc][   build:leaf.bst] START Building
[wrapper][2026-08-21 12:00:06,100] INFO: [00:00:06][cccccccc][   build:leaf.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:06,200] INFO: Return code: 0
"""

# Two sandboxes, each a shell that forks compilers - the *same* pid
# numbers in both, which is what `--unshare-pid` does, and **overlapping
# in time**, which is what a parallel build does.
#
# The overlap is the point. With the sandboxes separated in time, a
# lookup that forgot the invocation still picks the right parent by
# accident, because the other sandbox's shell has already exited; the
# first draft of this fixture ran them 10 seconds apart and the
# cross-sandbox mutation passed. Here `leaf.bst`'s shell starts 50 ms
# after `mid.bst`'s and both are alive when either's children fork, so a
# merged key connects one element's compiler to the other's shell.
def _raw():
    lines = []
    for element, invocation, base in (("mid.bst", "inv-mid", 1000.0),
                                      ("leaf.bst", "inv-leaf", 1000.05)):
        lines.append(f"START pid=2 ppid=1 ts={base:.6f} element={element} "
                     f"inv={invocation} src=spine cmd=sh -c make\n")
        for index in range(3):
            pid = 3 + index
            start = base + 0.1 * (index + 1)
            lines.append(f"START pid={pid} ppid=2 ts={start:.6f} "
                         f"element={element} inv={invocation} src=spine "
                         f"cmd=cc -c f{index}.c\n")
            lines.append(f"END pid={pid} ppid=2 ts={start + 0.05:.6f} "
                         f"element={element} inv={invocation} src=spine "
                         f"exit=0 utime=0.001 stime=0.001 maxrss_kb=1024 "
                         f"cmd=cc -c f{index}.c\n")
        lines.append(f"END pid=2 ppid=1 ts={base + 0.9:.6f} element={element} "
                     f"inv={invocation} src=spine exit=0 utime=0.01 "
                     f"stime=0.01 maxrss_kb=2048 cmd=sh -c make\n")
    return "".join(lines)


_GRAPH = {
    "elements": [{"uid": uid, "cache_key": "k", "requested_target": False,
                  "element_kind": "manual"}
                 for uid in ("top.bst", "mid.bst", "leaf.bst", "spare.bst")],
    "dependencies": [
        {"predecessor": "top.bst", "successor": "mid.bst",
         "dependency_type": "build"},
        {"predecessor": "mid.bst", "successor": "leaf.bst",
         "dependency_type": "build"},
        # An edge onto an element this run never built: nothing to
        # connect, and an arrow to nowhere is not an improvement.
        {"predecessor": "mid.bst", "successor": "spare.bst",
         "dependency_type": "build"},
    ],
    "run_identity_hash": "flows-fixture",
}


def _snapshot(tmp_path, graph=None):
    snapshot = tmp_path / "20260821T120000Z"
    snapshot.mkdir()
    (snapshot / "build.log").write_text(_LOG, encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run")
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    (snapshot / "run" / "graph.json").write_text(
        json.dumps(_GRAPH if graph is None else graph), encoding="utf-8")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write(_raw())
    return snapshot


def decode(path):
    """Every event's name, flow ids and terminating flow ids.

    The wire type is checked here rather than assumed: `fixed64` is
    wire type 1, and a varint in the same field number would arrive as
    wire type 0 and decode to a different number entirely.
    """
    raw = gzip.open(path, "rb").read()
    packets = [v for f, w, v in _fields(raw) if f == trackevent.TRACE_PACKET]
    names, events = {}, []
    for packet in packets:
        body = interned = None
        for field, _wire, value in _fields(packet):
            if field == trackevent.PACKET_TRACK_EVENT:
                body = value
            elif field == trackevent.PACKET_INTERNED_DATA:
                interned = value
        if interned is not None:
            for field, _wire, value in _fields(interned):
                if field != trackevent.INTERNED_EVENT_NAMES:
                    continue
                iid = name = None
                for inner, _w, payload in _fields(value):
                    if inner == 1:
                        iid = payload
                    elif inner == 2:
                        name = payload.decode("utf-8")
                names[iid] = name
        if body is None:
            continue
        kind = name_iid = None
        flows, terminating = [], []
        for field, wire, value in _fields(body):
            if field == trackevent.EVENT_TYPE:
                kind = value
            elif field == trackevent.EVENT_NAME_IID:
                name_iid = value
            elif field in (trackevent.EVENT_FLOW_IDS,
                           trackevent.EVENT_TERMINATING_FLOW_IDS):
                assert wire == trackevent.WIRE_FIXED64, (
                    f"field {field} arrived as wire type {wire}; "
                    "`repeated fixed64` is wire type 1, and a varint here "
                    "is a packet a reader drops without complaining")
                target = (flows if field == trackevent.EVENT_FLOW_IDS
                          else terminating)
                target.append(struct.unpack("<Q", value)[0])
        if kind in (trackevent.TYPE_SLICE_BEGIN, trackevent.TYPE_INSTANT):
            events.append({"name_iid": name_iid, "flows": flows,
                           "terminating": terminating})
    for event in events:
        event["name"] = names.get(event["name_iid"])
    return events


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("flows")
    snapshot = _snapshot(tmp)
    out = tmp / DEFAULT_OUTPUT[FORMAT_TRACKEVENT]
    result = render(str(snapshot), str(out))
    events = decode(out)
    return {"snapshot": snapshot, "path": out, "result": result,
            "events": events,
            "by_name": {event["name"]: event for event in events}}


def _pairs(events):
    """`flow id -> (source name, sink name)`, from the two lists."""
    sources, sinks = {}, {}
    for event in events:
        for flow in event["flows"]:
            assert flow not in sources, f"flow {flow} has two sources"
            sources[flow] = event["name"]
        for flow in event["terminating"]:
            assert flow not in sinks, f"flow {flow} ends twice"
            sinks[flow] = event["name"]
    assert set(sources) == set(sinks), (
        "a flow with only one end draws no arrow and says nothing")
    return {flow: (sources[flow], sinks[flow]) for flow in sources}


class TestThePlane1ArrowsAreTheGraphsEdges:

    def test_the_chain_is_connected_end_to_end(self, rendered):
        pairs = _pairs(rendered["events"])
        plane1 = {(source, sink) for source, sink in pairs.values()
                  if source and sink and "[" in source}
        assert ("mid.bst [Building]", "leaf.bst [Building]") in plane1

    def test_an_edge_whose_ends_tie_is_dropped_and_counted(self, rendered):
        """`top.bst` finishes in the microsecond `mid.bst` starts, so
        nothing in the capture says which came first. Perfetto would
        pick one; this drops it and says how many it dropped."""
        assert rendered["result"]["flows_dropped"] == 1
        pairs = _pairs(rendered["events"])
        assert not any(source and source.startswith("top.bst")
                       for source, _ in pairs.values())

    def test_an_edge_onto_an_unbuilt_element_draws_nothing(self, rendered):
        """`spare.bst` is in the graph and produced no task. An arrow
        to nowhere is not an improvement."""
        pairs = _pairs(rendered["events"])
        assert not any("spare" in (name or "")
                       for pair in pairs.values() for name in pair)

    def test_the_edges_come_from_the_graph_and_not_from_adjacency(
            self, rendered):
        edges = dependency_edges(str(rendered["snapshot"]))
        assert ("mid.bst", "leaf.bst") in edges
        assert ("top.bst", "leaf.bst") not in edges, (
            "the fixture has a transitive pair; if the emitter drew it the "
            "next clause could not tell a graph edge from an adjacency")
        pairs = _pairs(rendered["events"])
        drawn = {(source, sink) for source, sink in pairs.values()
                 if source and "[" in source}
        assert ("top.bst [Building]", "leaf.bst [Building]") not in drawn

    def test_a_snapshot_with_no_graph_draws_no_dependency_arrows(
            self, tmp_path):
        snapshot = _snapshot(tmp_path)
        (snapshot / "run" / "graph.json").unlink()
        assert dependency_edges(str(snapshot)) == []
        out = tmp_path / "trace.gz"
        result = render(str(snapshot), str(out))
        pairs = _pairs(decode(out))
        assert not any(source and "[" in source
                       for source, _ in pairs.values())
        assert result["flows_dropped"] == 0


class TestThePlane2ArrowsAreTheExecChain:

    def test_a_parent_is_connected_to_each_of_its_children(self, rendered):
        pairs = _pairs(rendered["events"])
        children = [sink for source, sink in pairs.values()
                    if source == "sh -c make"]
        assert sorted(children) == ["cc -c f0.c", "cc -c f0.c",
                                    "cc -c f1.c", "cc -c f1.c",
                                    "cc -c f2.c", "cc -c f2.c"], children

    def test_no_flow_crosses_two_elements(self, rendered):
        """The clause the item was filed with. Both sandboxes use pids
        2..5, so a lookup that forgot the invocation would connect one
        element's shell to another's compiler - causation invented out
        of a pid collision.
        """
        from tools.bga_timeline import _plane2_flows
        from tools.bst_native_build_tracer import (
            parse_trace_lines, stream_records)
        records = sorted(stream_records(iter(parse_trace_lines(
            _raw().splitlines()))), key=lambda r: r["start_ts"])
        by_id = {id(record): record for record in records}
        flows, _next = _plane2_flows(records, 1)
        owners = {}
        for record_id, (sources, sinks) in flows.items():
            for flow in sources + sinks:
                owners.setdefault(flow, set()).add(
                    (by_id[record_id]["invocation"],
                     by_id[record_id]["element"]))
        crossing = {flow: sandboxes for flow, sandboxes in owners.items()
                    if len(sandboxes) > 1}
        assert crossing == {}, crossing
        assert len(owners) == 6, owners

    def test_a_record_whose_parent_is_not_traced_starts_no_flow(self):
        """`ppid=1` is the sandbox's own init, which the capture never
        recorded. Nothing to point at."""
        from tools.bga_timeline import _plane2_flows
        from tools.bst_native_build_tracer import (
            parse_trace_lines, stream_records)
        records = list(stream_records(iter(parse_trace_lines([
            "START pid=2 ppid=1 ts=1.0 element=e.bst inv=a cmd=orphan",
            "END pid=2 ppid=1 ts=2.0 element=e.bst inv=a utime=0.1 stime=0.1",
        ]))))
        assert _plane2_flows(records, 1) == ({}, 1)


class TestAFlowIsOneIdOnTwoSlices:

    def test_no_event_both_starts_and_ends_the_same_flow(self, rendered):
        for event in rendered["events"]:
            shared = set(event["flows"]) & set(event["terminating"])
            assert shared == set(), (event["name"], shared)

    def test_every_id_is_used_exactly_twice_and_is_unique(self, rendered):
        pairs = _pairs(rendered["events"])
        assert len(pairs) == rendered["result"]["flows"], (
            len(pairs), rendered["result"]["flows"])
        assert len(pairs) == 7, pairs

    def test_the_ids_are_fixed64_on_the_wire(self, rendered):
        """`decode` asserts the wire type on every flow field it meets;
        this is the clause that says it met some."""
        assert any(event["flows"] or event["terminating"]
                   for event in rendered["events"])


class TestTheArrowsRideThePacketsThatExist:

    def test_the_trace_is_the_same_trace_twice(self, tmp_path):
        snapshot = _snapshot(tmp_path)
        digests = []
        for index in (1, 2):
            out = tmp_path / f"trace-{index}.gz"
            render(str(snapshot), str(out))
            with gzip.open(out, "rb") as handle:
                digests.append(hashlib.sha256(handle.read()).hexdigest())
        assert digests[0] == digests[1], digests

    def test_a_flow_costs_no_packet_at_all(self, tmp_path, monkeypatch):
        """The property, not a remembered number.

        The same capture is rendered twice - once as it ships, once
        with both flow sources silenced - and the packet counts must be
        **equal**. A flow id rides the slice packet that already exists,
        which is the whole argument for emitting every edge rather than
        capping them. Asserting a constant instead would have gone
        stale the moment `UX-311` added three packets of its own, and
        would have said nothing about flows either way.
        """
        import tools.bga_timeline as timeline

        snapshot = tmp_path / "20260821T170127Z"
        snapshot.mkdir()
        shutil.copy(REAL_CAPTURE / "build.log", snapshot / "build.log")
        shutil.copy(REAL_CAPTURE / "plane2.log.gz", snapshot / "plane2.log.gz")
        shutil.copytree(REAL_CAPTURE / "run", snapshot / "run")

        out = tmp_path / "trace.gz"
        withf = render(str(snapshot), str(out))
        with gzip.open(out, "rb") as handle:
            with_body = handle.read()

        monkeypatch.setattr(timeline, "dependency_edges", lambda _s: [])
        monkeypatch.setattr(timeline, "_plane2_flows",
                            lambda records, first: ({}, first))
        bare = tmp_path / "bare.gz"
        without = render(str(snapshot), str(bare))
        with gzip.open(bare, "rb") as handle:
            without_body = handle.read()

        assert withf["packets"] == without["packets"], (
            withf["packets"], without["packets"])
        assert withf["slices"] == without["slices"]
        assert without["flows"] == 0 and withf["flows"] == 836, withf["flows"]
        assert withf["flows_dropped"] == 2, (
            "`toolchain.bst` is instantaneous and shares its microsecond "
            "with both dependents - if that changed, so did the capture")
        # 836 flows, two ids each, nine bytes an id plus the growth of
        # the length prefixes they sit inside.
        per_flow = (len(with_body) - len(without_body)) / withf["flows"]
        assert 18.0 <= per_flow <= 22.0, per_flow
