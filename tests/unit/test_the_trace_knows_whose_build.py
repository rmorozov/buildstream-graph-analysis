"""UX-311: a trace that knows whose build it was.

A trace file leaves the machine that made it - attached to a ticket,
shared, opened weeks later beside five others - and until this it
carried no identity at all: not which run, not which host, not whether
the capture was even complete. The report refuses to present an
interrupted run's numbers as measurements (`UX-156`); the trace, opened
directly in Perfetto, looked like any other build.

**The surface is one track and one instant on it**, because that is
portable vocabulary: `trace_processor` selects it like any other slice
and the UI shows it without knowing anything about `bga`. The
incompleteness is in the **track name**, not only in an annotation - an
annotation is something a reader has to open a slice to see, and the
honesty belongs where the first scroll lands.

**The ordering rule that had to be read rather than remembered.**
`sibling_order_rank` is **ignored on a process track** unless the
*root* descriptor - `uuid = 0`, a track nobody writes events to - sets
`process_ordering` to `PROCESS_ORDERING_EXPLICIT`. A rank written
without that one packet is a hint no UI reads, and nothing about the
trace would look wrong.

**A recorded deviation.** The item asks for the *critical path* lanes
first. The timeline has no critical path: it reads two logs and a
graph, not an analysis, and computing one here would be a second copy
of the analyzer's own rule - the kind of duplication `UX-273` and
`UX-301` are about. Element lanes are ordered heaviest-traced-first,
which is what this command can compute from what it reads, and the
trace says which rule it used in `lane_order` rather than leaving a
reader to assume the other one.
"""
import gzip
import json
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from tools.bga_timeline import (  # noqa: E402
    DEFAULT_OUTPUT, FORMAT_TRACKEVENT, IDENTITY_ANNOTATIONS, IDENTITY_TRACK,
    LANE_ORDER_RULE, identity_annotations, identity_track_name, render,
    run_identity)
from tools.native_trace import trackevent  # noqa: E402
from bga import hostinfo  # noqa: E402

from test_the_timeline_speaks_perfetto import _fields  # noqa: E402

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


# Three elements whose Plane 2 spans are deliberately in the *reverse*
# of their name order, so lane rank cannot accidentally agree with the
# alphabetical pid assignment.
_LOG = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:aaa.bst] START Building
[wrapper][2026-08-21 12:00:01,100] INFO: [00:00:01][aaaaaaaa][   build:aaa.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:01,200] INFO: [00:00:01][bbbbbbbb][   build:bbb.bst] START Building
[wrapper][2026-08-21 12:00:03,200] INFO: [00:00:03][bbbbbbbb][   build:bbb.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,300] INFO: [00:00:03][cccccccc][   build:ccc.bst] START Building
[wrapper][2026-08-21 12:00:07,300] INFO: [00:00:07][cccccccc][   build:ccc.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:07,400] INFO: Return code: 0
"""

# aaa is the *shortest*, ccc the longest - the reverse of alphabetical.
_SPANS = {"aaa.bst": 0.2, "bbb.bst": 1.0, "ccc.bst": 3.0}


def _raw():
    lines = []
    base = 1000.0
    for index, (element, length) in enumerate(sorted(_SPANS.items())):
        start = base + index
        lines.append(f"START pid={10 + index} ppid=1 ts={start:.6f} "
                     f"element={element} inv=inv-{index} src=spine "
                     f"cmd=cc -c {element}.c\n")
        lines.append(f"END pid={10 + index} ppid=1 ts={start + length:.6f} "
                     f"element={element} inv=inv-{index} src=spine exit=0 "
                     f"utime=0.1 stime=0.1 maxrss_kb=1024 "
                     f"cmd=cc -c {element}.c\n")
    return "".join(lines)


_CONTEXT = {
    "run_identity": {
        "manifest_hash": "abc123",
        "project_identity": "examples/11-identity",
        "targets": ["all.bst"],
        "project_git_commit": "deadbeef",
        "scheduler": {"builders": 7},
    },
    "host_manifest": {
        "schema": "host/v1",
        "cpu_model": "Fictional CPU @ 1.0GHz",
        "cpu_count": 3,
        "memory_mb": 4096,
        "kernel_release": "1.2.3-test",
        "distro_id": "testdistro 1.0",
        "toolchain": {"bst": "2.7.0"},
    },
    "build_outcome": {"failed_elements": [], "failed_count": 0,
                      "interrupted": False},
}


def _snapshot(tmp_path, name="20260821T120000Z", outcome=None):
    snapshot = tmp_path / name
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.mkdir()
    (snapshot / "build.log").write_text(_LOG, encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run")
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    context = json.loads(json.dumps(_CONTEXT))
    if outcome is not None:
        context["build_outcome"] = outcome
    (snapshot / "run" / "run-context.json").write_text(
        json.dumps(context), encoding="utf-8")
    (snapshot / "run" / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid, "cache_key": "k",
                      "requested_target": False, "element_kind": kind}
                     for uid, kind in (("aaa.bst", "manual"),
                                       ("bbb.bst", "cmake"),
                                       ("ccc.bst", "autotools"))],
        "dependencies": [], "run_identity_hash": "identity-fixture"}),
        encoding="utf-8")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write(_raw())
    return snapshot


def decode(path):
    """Process tracks with their ranks, and the annotated instants.

    The root descriptor is read too: without `process_ordering` on
    `uuid = 0` every rank below it is inert, so "the ranks are right"
    is only half the claim.
    """
    raw = gzip.open(path, "rb").read()
    packets = [v for f, w, v in _fields(raw) if f == trackevent.TRACE_PACKET]
    annotation_names, event_names = {}, {}
    processes, instants = [], []
    root_ordering = None
    for packet in packets:
        body = descriptor = interned = None
        for field, _wire, value in _fields(packet):
            if field == trackevent.PACKET_TRACK_EVENT:
                body = value
            elif field == trackevent.PACKET_TRACK_DESCRIPTOR:
                descriptor = value
            elif field == trackevent.PACKET_INTERNED_DATA:
                interned = value
        if interned is not None:
            for field, _wire, value in _fields(interned):
                table = {trackevent.INTERNED_EVENT_NAMES: event_names,
                         trackevent.INTERNED_DEBUG_ANNOTATION_NAMES:
                             annotation_names}.get(field)
                if table is None:
                    continue
                iid = name = None
                for inner, _w, payload in _fields(value):
                    if inner == 1:
                        iid = payload
                    elif inner == 2:
                        name = payload.decode("utf-8")
                table[iid] = name
        if descriptor is not None:
            uuid = name = rank = None
            is_process = False
            for field, _wire, value in _fields(descriptor):
                if field == trackevent.TRACK_UUID:
                    uuid = value
                elif field == trackevent.TRACK_NAME:
                    name = value.decode("utf-8")
                elif field == trackevent.TRACK_SIBLING_ORDER_RANK:
                    rank = value
                elif field == trackevent.TRACK_PROCESS:
                    is_process = True
                elif field == trackevent.TRACK_PROCESS_ORDERING:
                    root_ordering = value
            if is_process:
                processes.append({"uuid": uuid, "name": name, "rank": rank})
        if body is None:
            continue
        kind = name_iid = None
        args = {}
        for field, _wire, value in _fields(body):
            if field == trackevent.EVENT_TYPE:
                kind = value
            elif field == trackevent.EVENT_NAME_IID:
                name_iid = value
            elif field == trackevent.EVENT_DEBUG_ANNOTATIONS:
                key = val = None
                for inner, _w, payload in _fields(value):
                    if inner == trackevent.ANNOTATION_NAME_IID:
                        key = payload
                    elif inner == trackevent.ANNOTATION_INT_VALUE:
                        val = payload
                    elif inner == trackevent.ANNOTATION_STRING_VALUE:
                        val = payload.decode("utf-8")
                args[key] = val
        if kind == trackevent.TYPE_INSTANT:
            instants.append({"name": event_names.get(name_iid),
                             "args": {annotation_names[k]: v
                                      for k, v in args.items()}})
    return {"processes": processes, "instants": instants,
            "root_ordering": root_ordering}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("identity")
    snapshot = _snapshot(tmp)
    out = tmp / DEFAULT_OUTPUT[FORMAT_TRACKEVENT]
    result = render(str(snapshot), str(out))
    trace = decode(out)
    identity = next(entry for entry in trace["instants"]
                    if entry["name"].startswith(IDENTITY_TRACK))
    return {"snapshot": snapshot, "path": out, "result": result,
            "trace": trace, "identity": identity}


class TestTheTraceSaysWhoseBuildItWas:

    def test_the_identity_values_are_the_run_contexts_own(self, rendered):
        """Equality, field by field, against the file they came from."""
        context = json.loads(
            (rendered["snapshot"] / "run" / "run-context.json")
            .read_text(encoding="utf-8"))
        args = rendered["identity"]["args"]
        assert args["run"] == "20260821T120000Z"
        assert args["project"] == context["run_identity"]["project_identity"]
        assert args["manifest_hash"] == context["run_identity"]["manifest_hash"]
        assert args["project_git_commit"] == \
            context["run_identity"]["project_git_commit"]
        assert args["targets"] == "all.bst"
        assert args["builders"] == context["run_identity"]["scheduler"]["builders"]
        manifest = context["host_manifest"]
        assert args["host_cpu_model"] == manifest["cpu_model"]
        assert args["host_cpu_count"] == manifest["cpu_count"]
        # UX-341: the fixture's manifest is a `host/v1` one, in MB;
        # the annotation is in bytes, converted where it is read.
        assert args["host_memory_bytes"] == hostinfo.normalised(
            manifest)["memory_bytes"]
        assert args["kernel_release"] == manifest["kernel_release"]
        assert args["distro_id"] == manifest["distro_id"]
        assert args["bst_version"] == manifest["toolchain"]["bst"]

    def test_it_says_which_bga_wrote_it(self, rendered):
        from bga import __version__
        assert rendered["identity"]["args"]["bga_version"] == __version__

    def test_it_states_the_alignment_rather_than_leaving_it_implied(
            self, rendered):
        args = rendered["identity"]["args"]
        assert args["anchor_element"] == rendered["result"]["anchor"]
        assert isinstance(args["plane_offset_us"], int)
        assert args["lane_order"] == LANE_ORDER_RULE

    def test_two_runs_are_distinguishable_by_their_identity_alone(
            self, tmp_path):
        """The sharing scenario: two traces open together, and the only
        thing that tells them apart is the track a reader meets first.
        """
        seen = []
        for name in ("20260821T120000Z", "20260822T090000Z"):
            snapshot = _snapshot(tmp_path / name, name=name)
            out = tmp_path / f"{name}.gz"
            render(str(snapshot), str(out))
            identity = next(e for e in decode(out)["instants"]
                            if e["name"].startswith(IDENTITY_TRACK))
            seen.append(identity["args"]["run"])
        assert seen == ["20260821T120000Z", "20260822T090000Z"]
        assert len(set(seen)) == 2

    def test_a_snapshot_with_no_context_still_says_which_run(self, tmp_path):
        snapshot = _snapshot(tmp_path)
        (snapshot / "run" / "run-context.json").unlink()
        assert run_identity(str(snapshot)) == {}
        out = tmp_path / "trace.gz"
        render(str(snapshot), str(out))
        identity = next(e for e in decode(out)["instants"]
                        if e["name"].startswith(IDENTITY_TRACK))
        assert identity["args"]["run"] == "20260821T120000Z"
        assert "project" not in identity["args"]


class TestAnIncompleteRunSaysSoInTheName:

    @pytest.mark.parametrize("outcome,reason", [
        ({"failed_elements": ["app.bst"], "failed_count": 1,
          "interrupted": False}, "failed"),
        ({"failed_elements": [], "failed_count": 0,
          "interrupted": True}, "interrupted"),
        ({"failed_elements": [], "failed_count": 0, "interrupted": False,
          "suspended": {"suspended_seconds": 42.0}}, "suspended"),
    ])
    def test_each_way_of_being_incomplete_reaches_the_track_name(
            self, tmp_path, outcome, reason):
        """All three, because `UX-156`/`UX-157`/`UX-185` are answered by
        one accessor precisely so a consumer cannot handle one and
        forget the others - and this is a new consumer."""
        snapshot = _snapshot(tmp_path / reason, outcome=outcome)
        out = tmp_path / f"{reason}.gz"
        result = render(str(snapshot), str(out))
        assert result["incomplete_reason"] == reason
        trace = decode(out)
        named = [entry["name"] for entry in trace["processes"]
                 if entry["name"].startswith(IDENTITY_TRACK)]
        assert named == [f"{IDENTITY_TRACK} ({reason})"], named
        identity = next(e for e in trace["instants"]
                        if e["name"].startswith(IDENTITY_TRACK))
        assert identity["args"]["incomplete_reason"] == reason

    def test_a_finished_run_says_nothing_rather_than_saying_fine(
            self, rendered):
        assert rendered["result"]["incomplete_reason"] is None
        assert identity_track_name(None) == IDENTITY_TRACK
        assert "incomplete_reason" not in rendered["identity"]["args"]
        names = [entry["name"] for entry in rendered["trace"]["processes"]]
        assert IDENTITY_TRACK in names

    def test_the_reason_is_bgas_own_rule_and_not_a_second_copy(self):
        """`incomplete_reason` has one definition (`UX-156`/`157`/`185`
        joined it into one accessor). This reads that one, so a fourth
        way to be incomplete arrives here for free."""
        from tools.bga_timeline import _incomplete_reason
        from bga.ingest.models import RunContext

        for outcome in ({"failed_elements": ["a"], "interrupted": False},
                        {"failed_elements": [], "interrupted": True},
                        {"suspended": {"suspended_seconds": 1.0}},
                        {"failed_elements": [], "interrupted": False}):
            assert _incomplete_reason(outcome) == \
                RunContext(build_outcome=outcome).incomplete_reason


class TestTheLanesOpenWhereTheReaderShouldLook:

    def test_the_root_descriptor_asks_for_explicit_order(self, rendered):
        """Without this one packet every rank below is a hint no UI
        reads - and the trace would look correct while ordering
        nothing."""
        assert rendered["trace"]["root_ordering"] == \
            trackevent.PROCESS_ORDERING_EXPLICIT

    def test_identity_first_then_plane_one_then_the_elements(self, rendered):
        ranked = sorted(rendered["trace"]["processes"],
                        key=lambda entry: entry["rank"])
        assert ranked[0]["name"].startswith(IDENTITY_TRACK)
        assert ranked[0]["rank"] == 0
        assert ranked[1]["name"] == "Plane 1: BuildStream"
        assert ranked[1]["rank"] == 1
        assert all(entry["rank"] >= 2 for entry in ranked[2:])

    def test_the_heaviest_element_lane_comes_first(self, rendered):
        """And the fixture's spans run the *reverse* of its names, so a
        rank that agreed with the alphabetical pid assignment would be
        ordering nothing."""
        lanes = [entry for entry in rendered["trace"]["processes"]
                 if entry["name"].startswith("native: ")]
        by_rank = [entry["name"] for entry in
                   sorted(lanes, key=lambda entry: entry["rank"])]
        assert by_rank == ["native: ccc.bst (autotools)",
                           "native: bbb.bst (cmake)",
                           "native: aaa.bst (manual)"], by_rank
        assert by_rank != sorted(by_rank), (
            "the ranks agree with alphabetical order - this fixture cannot "
            "tell an ordering rule from the pid assignment")

    def test_each_lane_says_what_kind_of_element_it_is(self, rendered):
        labels = {entry["name"] for entry in rendered["trace"]["processes"]
                  if entry["name"].startswith("native: ")}
        assert labels == {"native: aaa.bst (manual)",
                          "native: bbb.bst (cmake)",
                          "native: ccc.bst (autotools)"}

    def test_a_lane_whose_kind_is_unknown_says_only_its_name(self, tmp_path):
        """An empty pair of brackets would be worse than none."""
        snapshot = _snapshot(tmp_path)
        graph = json.loads((snapshot / "run" / "graph.json")
                           .read_text(encoding="utf-8"))
        for element in graph["elements"]:
            element.pop("element_kind")
        (snapshot / "run" / "graph.json").write_text(json.dumps(graph),
                                                     encoding="utf-8")
        out = tmp_path / "trace.gz"
        render(str(snapshot), str(out))
        labels = {entry["name"] for entry in decode(out)["processes"]
                  if entry["name"].startswith("native: ")}
        assert labels == {"native: aaa.bst (unknown)",
                          "native: bbb.bst (unknown)",
                          "native: ccc.bst (unknown)"}


class TestTheIdentityKeysAreInTheContract:

    def test_every_identity_key_is_emitted_on_a_run_that_has_them(self):
        """Including `incomplete_reason`, which only an unfinished run
        emits - so the coverage is taken over the union of the fixtures
        rather than over one of them."""
        emitted = set()
        for outcome in (None, {"failed_elements": [], "failed_count": 0,
                               "interrupted": True}):
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                snapshot = _snapshot(pathlib.Path(tmp), outcome=outcome)
                emitted.update(
                    key for key, _ in
                    identity_annotations(str(snapshot), "aaa.bst", 1.0))
        documented = {key for key, _ in IDENTITY_ANNOTATIONS}
        assert documented - emitted == set()
        assert emitted - documented == set()

    @needs_real_capture
    def test_the_real_capture_fills_it_too(self, tmp_path):
        """Not only the shaped fixture: `examples/06` is a real
        `run-context.json` written by a real capture."""
        snapshot = tmp_path / "20260821T170127Z"
        snapshot.mkdir()
        shutil.copy(REAL_CAPTURE / "build.log", snapshot / "build.log")
        shutil.copy(REAL_CAPTURE / "plane2.log.gz", snapshot / "plane2.log.gz")
        shutil.copytree(REAL_CAPTURE / "run", snapshot / "run")
        filled = dict(identity_annotations(str(snapshot), "core.bst", 0.0))
        assert filled["project"] == "examples/06-macro-micro-optimization"
        assert filled["host_cpu_count"] == 4
        assert filled["bst_version"] == "2.7.0"
        assert "incomplete_reason" not in filled
