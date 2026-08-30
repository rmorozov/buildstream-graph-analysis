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
import re
import pathlib
import shutil
import struct
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bga.run_store import ANALYSIS_NAME  # noqa: E402
from tools.bga_timeline import (  # noqa: E402
    DEFAULT_OUTPUT, FLOW_LOSS_REASONS, FORMAT_TRACKEVENT, dependency_edges,
    describe, element_structure, render)
from tools.native_trace import trackevent  # noqa: E402

from test_the_timeline_speaks_perfetto import _fields  # noqa: E402
from test_one_click_from_investigation import (  # noqa: E402
    _node, needs_node)

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
REAL_CAPTURE = REPO / ("examples/06-macro-micro-optimization/.bga/runs/"
                       "20260821T170127Z")

# `examples/06`'s capture is real and **gitignored** - it exists on this
# machine and not in a clone. The measured figures below are taken from
# it and are worth having exactly, so the clauses that need it are
# skipped rather than deleted; every *property* they check is also
# checked on a committed fixture, so CI is not left believing something
# it never ran.
needs_real_capture = pytest.mark.skipif(
    not REAL_CAPTURE.is_dir(), reason="no real capture in this tree")


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
        assert rendered["result"]["flow_losses"]["out_of_order"] == 1
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
        assert result["flow_losses"] == {"edges": 0, "drawn": 0,
                                         "no_task": 0,
                                         "out_of_order": 0}


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

    @needs_real_capture
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
        assert withf["flow_losses"]["out_of_order"] == 2, (
            "`toolchain.bst` is instantaneous and shares its microsecond "
            "with both dependents - if that changed, so did the capture")
        # 836 flows, two ids each, nine bytes an id plus the growth of
        # the length prefixes they sit inside.
        per_flow = (len(with_body) - len(without_body)) / withf["flows"]
        assert 18.0 <= per_flow <= 22.0, per_flow

    def test_a_flow_costs_no_packet_on_the_committed_fixture_either(
            self, tmp_path, monkeypatch):
        """The same property where a clone can check it.

        The clause above takes the *figures* from `examples/06`, which
        git does not track. This one takes the property from the
        fixture in this file, which it does.
        """
        import tools.bga_timeline as timeline

        snapshot = _snapshot(tmp_path)
        out = tmp_path / "with.gz"
        withf = render(str(snapshot), str(out))
        monkeypatch.setattr(timeline, "dependency_edges", lambda _s: [])
        monkeypatch.setattr(timeline, "_plane2_flows",
                            lambda records, first: ({}, first))
        bare = tmp_path / "bare.gz"
        without = render(str(snapshot), str(bare))
        assert withf["flows"] == 7 and without["flows"] == 0
        assert withf["packets"] == without["packets"]
        assert withf["slices"] == without["slices"]


# `UX-431`: a graph whose every edge names elements this run never built.
# That is what a mostly-cached build looks like from here, and it is the
# ordinary case - the build people profile is the one where most
# elements are already in the cache.
_CACHED_GRAPH = {
    "elements": [{"uid": uid, "cache_key": "k", "requested_target": False,
                  "element_kind": "manual"}
                 for uid in ("cached-a.bst", "cached-b.bst", "cached-c.bst")],
    "dependencies": [
        {"predecessor": "cached-a.bst", "successor": "cached-b.bst",
         "dependency_type": "build"},
        {"predecessor": "cached-b.bst", "successor": "cached-c.bst",
         "dependency_type": "build"},
    ],
    "run_identity_hash": "flows-fixture-cached",
}


class TestTheLostEdgesAreAccountedFor:
    """`UX-431`: every edge is an arrow or a named reason there is none.

    Two real captures of `examples/06` - 11 elements, 34 edges in
    `run/graph.json` - measured in round 69:

    ```text
                            edges   flows   flows_dropped
    mostly-cached build        34       0               0
    full rebuild               34      24              24
    ```

    The cached build drew nothing and reported no losses, because
    `_plane1_flows` had two skip paths and counted one. A zero meaning
    "nothing was lost" and a zero meaning "this counter does not watch
    that door" are indistinguishable, and the second is worse than no
    counter: it converts an absence the reader might have questioned
    into an assurance.

    So the property is an **identity**, not a threshold: drawn plus every
    named reason equals the edge count, on every capture. A reason
    nobody counts breaks it, which is what makes it a guard rather than
    a restatement.
    """

    def test_every_edge_is_an_arrow_or_a_named_reason(self, rendered):
        losses = rendered["result"]["flow_losses"]
        edges = len(dependency_edges(str(rendered["snapshot"])))
        named = sum(losses[reason] for reason in FLOW_LOSS_REASONS)
        assert losses["edges"] == edges, (losses, edges)
        assert losses["drawn"] + named == edges, (
            f"{edges} edges, {losses['drawn']} drawn, {named} accounted "
            f"for by a named reason - the rest vanished without one, "
            f"which is the silence UX-431 was filed for: {losses}")

    def test_the_two_reasons_are_told_apart(self, rendered):
        """The fixture has one of each, so a single counter covering
        both would still balance and still say nothing useful. `top.bst`
        ties with `mid.bst`; `spare.bst` was never built."""
        losses = rendered["result"]["flow_losses"]
        assert losses["out_of_order"] == 1, losses
        assert losses["no_task"] == 1, losses

    def test_a_cached_build_says_why_it_drew_nothing(self, tmp_path):
        """The capture the item was filed on, in miniature: every edge
        names an element this run did not build. Before `UX-431` this
        rendered zero arrows and reported zero losses."""
        snapshot = _snapshot(tmp_path, graph=_CACHED_GRAPH)
        result = render(str(snapshot), str(tmp_path / "trace.gz"))
        losses = result["flow_losses"]
        assert (losses["edges"], losses["drawn"]) == (2, 0), losses
        assert losses["no_task"] == 2, (
            f"a build that drew no arrows at all accounted for none of "
            f"its {losses['edges']} edges: {losses}")

    def test_the_reader_is_told_and_not_only_the_result(self, tmp_path):
        """The count was in the render result and in one test, and
        `describe` never printed it - so even the reason that *was*
        counted reached nobody."""
        snapshot = _snapshot(tmp_path, graph=_CACHED_GRAPH)
        result = render(str(snapshot), str(tmp_path / "trace.gz"))
        said = describe(result, str(tmp_path / "trace.gz"))
        assert "0 of 2 dependency edge(s) drawn" in said, said
        assert FLOW_LOSS_REASONS["no_task"] in said, said
        assert FLOW_LOSS_REASONS["out_of_order"] not in said, (
            "a reason that took no edge is named anyway, so the summary "
            "reads as a list of things that went wrong")

    def test_a_run_that_drew_them_all_still_says_so(self, tmp_path):
        """The other half of the same rule. A line that appears only on
        loss teaches a reader that its absence means nothing was lost,
        which is the reading this item removes."""
        graph = dict(_CACHED_GRAPH, dependencies=[
            {"predecessor": "mid.bst", "successor": "leaf.bst",
             "dependency_type": "build"}])
        snapshot = _snapshot(tmp_path, graph=graph)
        result = render(str(snapshot), str(tmp_path / "trace.gz"))
        said = describe(result, str(tmp_path / "trace.gz"))
        assert result["flow_losses"]["drawn"] == 1, result["flow_losses"]
        assert "1 of 1 dependency edge(s) drawn" in said, said
        assert "not drawn" not in said, said

    def test_the_export_is_given_the_accounting(self, tmp_path):
        """`describe` serves whoever ran `bga timeline`. The reader who
        opens the report goes to the handoff to look for the arrows, so
        the payload carries it too - measured from the export, which is
        where the trace is rendered while the payload is being built.
        The **served** page is `UX-443`: `UX-296` moved the render off
        the startup path deliberately, so `run.json` is written before
        anything has counted an edge."""
        from tools import bga_view

        snapshot = _snapshot(tmp_path)
        path = tmp_path / "report.html"
        bga_view.export(str(snapshot / "run"), str(path))
        payload = json.loads(re.search(
            r'id="bga-run">(.*?)</script>',
            path.read_text(encoding="utf-8"), re.S).group(1))
        held = payload.get("trace_flow_losses")
        assert held, (
            "the run payload carries no edge accounting, so the page "
            "that sends a reader to look for the arrows cannot say why "
            "they are missing")
        assert (held["edges"], held["drawn"]) == (3, 1), held


@needs_node
class TestTheHandoffSectionNamesTheMissingArrows:
    """The rendered half. The payload above is only worth carrying if
    the page draws it, and `questions.js` is where the reader is told
    what to open the trace for."""

    SCRIPT = (
        'const q = await import("./bga/viewer/questions.js");'
        'const make = (t, a = {}, ...c) => ({ tagName: t, attrs: {...a},'
        '  children: [], textContent: c.join(""),'
        '  setAttribute(k, v) { this.attrs[k] = v; },'
        '  getAttribute(k) { return this.attrs[k] ?? null; },'
        '  addEventListener() {}, append(...x) {'
        '    for (const y of x) if (y) this.children.push(y); } });'
        'const found = [];'
        '(function walk(n) { if (!n) return;'
        '  if (n.attrs && n.attrs["data-flow-accounting"] !== undefined)'
        '    found.push(n.textContent);'
        '  (n.children ?? []).forEach(walk); })('
        '  q.renderQuestions(make, %s));'
        'console.log(JSON.stringify({ found }));')

    def _render(self, options):
        return _node(self.SCRIPT % json.dumps(options))["found"]

    def test_the_paragraph_names_the_count_and_the_reason(self):
        found = self._render({
            "hasTimeline": True, "tracePlanes": ["1"],
            "flowLosses": {"edges": 34, "drawn": 0, "no_task": 34,
                           "out_of_order": 0}})
        assert len(found) == 1, found
        assert "0 of 34 dependency edges" in found[0], found
        assert "cached or built earlier" in found[0], found
        assert "point the wrong way" not in found[0], (
            "a reason that took no edge is named anyway")

    def test_a_run_with_no_timeline_draws_no_accounting(self):
        """The section already tells that reader there is nothing to
        open; a count of edges in a trace that does not exist is a
        second answer to a question nobody asked."""
        assert self._render({
            "hasTimeline": False,
            "flowLosses": {"edges": 34, "drawn": 0, "no_task": 34,
                           "out_of_order": 0}}) == []

    def test_a_graph_with_no_edges_draws_no_accounting(self):
        assert self._render({
            "hasTimeline": True,
            "flowLosses": {"edges": 0, "drawn": 0, "no_task": 0,
                           "out_of_order": 0}}) == []


class TestTheCommittedFixtureCarriesTheGraphAnnotations:
    """`UX-431`'s third clause: no fixture in this repository had an
    `analyze.json`, so `depth`, `on_critical_path` and
    `downstream_count` were absent from every fixture-rendered trace and
    the questions that group by them were exercised by nobody. A real
    `bga snapshot` writes one; this is that file, produced by running
    `bga analyze` on the fixture's own run.

    It also closed a defect the fixture found. `element_structure` read
    `on_critical_path` from `element_join`, which is **Plane 2's**
    table - so a Plane 1 capture lost the annotation entirely while
    `critical_path_detail`, in the same document, named the path.
    """

    FIXTURE = REPO / "tests/fixtures/with_timeline"

    def test_the_analysis_is_beside_the_run(self):
        assert (self.FIXTURE / ANALYSIS_NAME).is_file(), (
            f"{ANALYSIS_NAME} is gone, and with it the only committed "
            f"capture that exercises the graph annotations")

    def test_all_three_annotations_reach_every_element(self):
        structure = element_structure(str(self.FIXTURE))
        assert len(structure) == 11, sorted(structure)
        missing = {uid: sorted(facts) for uid, facts in structure.items()
                   if set(facts) != {"depth", "downstream_count",
                                     "on_critical_path"}}
        assert missing == {}, (
            f"an annotation present on some elements and absent from "
            f"others is a `group by` that silently drops rows: {missing}")

    def test_the_chain_is_nine_levels_deep(self):
        """The shape `UX-434`'s query has to be able to see. One row per
        depth is the answer; a fixture with one depth could not tell a
        working query from the collapsed one."""
        depths = {facts["depth"]
                  for facts in element_structure(str(self.FIXTURE)).values()}
        assert len(depths) == 10, sorted(depths)

    def test_the_critical_path_comes_from_the_analysis(self):
        """Not every element, which a `True` default would give, and not
        none, which reading only `element_join` gave."""
        structure = element_structure(str(self.FIXTURE))
        on_path = {uid for uid, facts in structure.items()
                   if facts["on_critical_path"]}
        assert "codegen.bst" not in on_path, (
            "every element is on the path, so the annotation says "
            "nothing - `codegen.bst` is the one this fixture has off it")
        assert {"core.bst", "lib-a.bst", "app.bst"} <= on_path, sorted(on_path)
