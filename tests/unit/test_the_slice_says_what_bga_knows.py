"""UX-308: a slice carries what bga knows about it, not just its name.

Before this, a slice said one thing: its name - and for Plane 2 that
name is the command **truncated to 120 characters**, so the argv tail
that tells two compiler invocations apart was not in the trace at all.
Everything the annotations carry was already in the record or the run
directory; none of it is new capture.

**Why the keys are a contract.** They are what a details panel shows,
what `extract_arg(arg_set_id, 'debug.<key>')` selects on, and what
`UX-312`'s canned questions will be written against - so renaming one
silently breaks a query someone saved. `PLANE1_ANNOTATIONS` and
`PLANE2_ANNOTATIONS` are that contract, and the clauses below hold the
emitted set and the documented set equal in **both** directions.

**What it costs.** Measured on `examples/06`'s real capture, 825
slices, the same snapshot rendered by this tree and by the commit
before it:

```text
                    before      after
uncompressed      100,922 B   330,188 B     3.27x   (+278 B/slice)
gzipped            27,013 B    51,102 B     1.89x   (+29 B/slice)
```

The full command line is nearly all of it: on that capture 412 of 813
records run past the 120-character name, and 127,167 of 199,389 command
bytes are past the cut. The duplication is deliberate - `debug.cmd` is
*always* the whole command, so a query never has to know the truncation
rule - and gzip absorbs most of it.

**A recorded deviation.** The acceptance test asks that
`trace_processor` resolve `extract_arg` for each key. There is still no
`trace_processor` in CI - `UX-298`'s own open deviation, which
`UX-312` absorbs as its first clause - so the decoding below is done by
the in-repo protobuf reader, written from the wire rules rather than
from the emitter. That checks the bytes are what the schema says; it
does not check that Perfetto's own SQL reaches them, and this note is
here so that gap is not read as covered.
"""
import gzip
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from tools import bga_timeline  # noqa: E402
from tools.bga_timeline import (
    CATEGORY_PLANE2,  # noqa: E402
    ANNOTATION_CONTRACT, CATEGORY_FAILED, DEFAULT_OUTPUT, EXIT_STATUS_OK,
    FORMAT_TRACKEVENT, PLANE1_ANNOTATIONS, PLANE2_ANNOTATIONS, element_kinds,
    render)
from tools.bst_native_build_tracer import (  # noqa: E402
    parse_trace_lines, stream_records)
from tools.native_trace import trackevent  # noqa: E402

from test_the_timeline_speaks_perfetto import _fields, _WRAPPED  # noqa: E402

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


# A command long enough that the 120-character name loses its tail, with
# the distinguishing part *in* that tail - which is the case the item
# was filed for.
LONG_TAIL = "the-argv-tail-that-tells-two-invocations-apart"
LONG_CMD = ("cc -c " + "-I/usr/include/very/deeply/nested/path " * 4
            + LONG_TAIL + ".c")
assert len(LONG_CMD) > 120


def _raw():
    """One of everything the annotations have to tell apart.

    A spine process that exited 0; one that exited non-zero; one the
    kernel killed (`signal:9`, which is a status and not a number); a
    hook process, which can carry no exit status at all; one with a
    command longer than the name; and one still open when the capture
    ended.
    """
    return "".join([
        "START pid=101 ppid=1 ts=1000.000000 element=work-a.bst inv=inv-a "
        "src=spine cmd=cc -c ok.c\n",
        "END pid=101 ppid=1 ts=1000.500000 element=work-a.bst inv=inv-a "
        "src=spine exit=0 utime=0.012 stime=0.003 maxrss_kb=2048 "
        "cmd=cc -c ok.c\n",
        "START pid=102 ppid=1 ts=1000.100000 element=work-a.bst inv=inv-a "
        "src=spine cmd=cc -c broken.c\n",
        "END pid=102 ppid=1 ts=1000.600000 element=work-a.bst inv=inv-a "
        "src=spine exit=1 utime=0.001 stime=0.001 maxrss_kb=1024 "
        "cmd=cc -c broken.c\n",
        "START pid=103 ppid=1 ts=1000.200000 element=work-b.bst inv=inv-b "
        "src=spine cmd=cc -c killed.c\n",
        "END pid=103 ppid=1 ts=1000.700000 element=work-b.bst inv=inv-b "
        "src=spine exit=signal:9 utime=0.002 stime=0.001 maxrss_kb=512 "
        "cmd=cc -c killed.c\n",
        f"START pid=104 ppid=1 ts=1000.300000 element=work-b.bst inv=inv-b "
        f"cmd={LONG_CMD}\n",
        f"END pid=104 ppid=1 ts=1000.800000 element=work-b.bst inv=inv-b "
        f"utime=0.004 stime=0.001 maxrss_kb=4096 cmd={LONG_CMD}\n",
        "START pid=105 ppid=1 ts=1000.400000 element=work-b.bst inv=inv-b "
        "src=spine cmd=cc -c never-exits.c\n",
    ])


def _snapshot(tmp_path, kinds=True):
    snapshot = tmp_path / "20260821T120000Z"
    snapshot.mkdir()
    (snapshot / "build.log").write_text(_WRAPPED, encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run")
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    if kinds:
        # The golden graph carries no `element_kind`; a real capture
        # does, and the annotation is only worth asserting against a
        # graph that states one.
        import json
        path = snapshot / "run" / "graph.json"
        graph = json.loads(path.read_text(encoding="utf-8"))
        for element in graph["elements"]:
            element["element_kind"] = "cmake"
        graph["elements"].append({"uid": "work-a.bst", "cache_key": "k",
                                  "requested_target": False,
                                  "element_kind": "autotools"})
        path.write_text(json.dumps(graph), encoding="utf-8")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write(_raw())
    return snapshot


def decode(path):
    """Slices and instants with their annotations and categories.

    The reader from `test_the_timeline_speaks_perfetto.py`, extended to
    the two fields this item added - and written from the wire rules
    rather than from the emitter, so a value written into the wrong
    field number is a value this does not find.
    """
    raw = gzip.open(path, "rb").read()
    packets = [v for f, w, v in _fields(raw) if f == trackevent.TRACE_PACKET]
    tables = {trackevent.INTERNED_EVENT_NAMES: {},
              trackevent.INTERNED_EVENT_CATEGORIES: {},
              trackevent.INTERNED_DEBUG_ANNOTATION_NAMES: {}}
    events = []
    for packet in packets:
        body = interned = None
        for field, _wire, value in _fields(packet):
            if field == trackevent.PACKET_TRACK_EVENT:
                body = value
            elif field == trackevent.PACKET_INTERNED_DATA:
                interned = value
        if interned is not None:
            for field, _wire, value in _fields(interned):
                table = tables.get(field)
                if table is None:
                    continue
                iid = name = None
                for inner, _w, payload in _fields(value):
                    if inner == 1:
                        iid = payload
                    elif inner == 2:
                        name = payload.decode("utf-8")
                table[iid] = name
        if body is None:
            continue
        kind = name_iid = None
        annotations, categories = [], []
        for field, _wire, value in _fields(body):
            if field == trackevent.EVENT_TYPE:
                kind = value
            elif field == trackevent.EVENT_NAME_IID:
                name_iid = value
            elif field == trackevent.EVENT_CATEGORY_IIDS:
                categories.append(value)
            elif field == trackevent.EVENT_DEBUG_ANNOTATIONS:
                key = val = None
                for inner, _w, payload in _fields(value):
                    if inner == trackevent.ANNOTATION_NAME_IID:
                        key = payload
                    elif inner == trackevent.ANNOTATION_INT_VALUE:
                        val = (payload - (1 << 64) if payload >= (1 << 63)
                               else payload)
                    elif inner == trackevent.ANNOTATION_STRING_VALUE:
                        val = payload.decode("utf-8")
                annotations.append((key, val))
        if kind in (trackevent.TYPE_SLICE_BEGIN, trackevent.TYPE_INSTANT):
            events.append({"type": kind, "name_iid": name_iid,
                           "annotation_iids": annotations,
                           "category_iids": categories})
    names = tables[trackevent.INTERNED_EVENT_NAMES]
    annotation_names = tables[trackevent.INTERNED_DEBUG_ANNOTATION_NAMES]
    category_names = tables[trackevent.INTERNED_EVENT_CATEGORIES]
    for event in events:
        event["name"] = names.get(event["name_iid"])
        event["args"] = {annotation_names[iid]: value
                         for iid, value in event["annotation_iids"]}
        event["categories"] = sorted(category_names[iid]
                                     for iid in event["category_iids"])
    return {"events": events, "annotation_names": annotation_names,
            "category_names": category_names}


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    if not REAL_CAPTURE.is_dir():
        pytest.skip("no real capture in this tree")
    """`examples/06`'s own capture, rendered.

    The small fixture above is built to carry one of everything; this is
    the one that says what the annotations cost and whether the
    interning is worth having, because it has 813 real records with
    real command lines in them.
    """
    tmp = tmp_path_factory.mktemp("real")
    snapshot = tmp / "20260821T170127Z"
    snapshot.mkdir()
    shutil.copy(REAL_CAPTURE / "build.log", snapshot / "build.log")
    shutil.copy(REAL_CAPTURE / "plane2.log.gz", snapshot / "plane2.log.gz")
    shutil.copytree(REAL_CAPTURE / "run", snapshot / "run")
    out = tmp / DEFAULT_OUTPUT[FORMAT_TRACKEVENT]
    result = render(str(snapshot), str(out))
    return {"path": out, "result": result, "trace": decode(out)}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("annotated")
    snapshot = _snapshot(tmp)
    out = tmp / DEFAULT_OUTPUT[FORMAT_TRACKEVENT]
    result = render(str(snapshot), str(out))
    trace = decode(out)
    plane2 = [e for e in trace["events"] if "cmd" in e["args"]]
    plane1 = [e for e in trace["events"] if "element_kind" in e["args"]]
    return {"path": out, "result": result, "trace": trace,
            "plane2": {e["args"]["cmd"]: e for e in plane2},
            "plane1": plane1, "records": {
                r["pid"]: r for r in stream_records(
                    iter(parse_trace_lines(_raw().splitlines())))}}


class TestTheKeysAreAContract:

    def test_every_documented_key_is_emitted(self, rendered):
        """This item's own two sets. `UX-311` added a third - the run
        identity - which no Plane 1 or Plane 2 slice carries and which
        `test_the_arrows...`'s neighbour guards on the fixture that can
        (an interrupted run is the only thing that emits
        `incomplete_reason`). The *reverse* direction below still reads
        the whole contract, because an undocumented key is undocumented
        wherever it came from.
        """
        emitted = set(rendered["trace"]["annotation_names"].values())
        documented = {key for key, _ in PLANE1_ANNOTATIONS + PLANE2_ANNOTATIONS}
        assert documented - emitted == set(), (
            "documented and never written - a query against it returns "
            "nothing, and nothing here says so")

    def test_every_emitted_key_is_documented(self, rendered):
        emitted = set(rendered["trace"]["annotation_names"].values())
        documented = {key for key, _ in ANNOTATION_CONTRACT}
        assert emitted - documented == set(), (
            "written and undocumented - the trace dictionary is the only "
            "place a reader can learn a key exists")

    def test_every_key_says_what_it_means(self):
        """A key with no sentence is a key nobody can use. `UX-312`
        renders this table; an empty cell would render as one."""
        for key, meaning in ANNOTATION_CONTRACT:
            assert key and key == key.lower().replace(" ", "_"), key
            assert len(meaning.split()) >= 5, (key, meaning)

    def test_the_two_planes_do_not_disagree_about_a_key(self):
        plane1 = dict(PLANE1_ANNOTATIONS)
        plane2 = dict(PLANE2_ANNOTATIONS)
        shared = set(plane1) & set(plane2)
        assert shared == set(), (
            f"{shared} is documented twice - one key, one meaning, or a "
            "query has to know which plane it is reading")

    def test_a_key_is_interned_once_on_the_committed_fixture(
            self, rendered):
        """The property where a clone can check it: the names table has
        no duplicate, and more annotation *values* are written than
        there are names to write them under. The clause below takes the
        same claim at a scale only the gitignored capture has."""
        names = rendered["trace"]["annotation_names"]
        written = sum(len(event["args"])
                      for event in rendered["trace"]["events"])
        assert len(names) == len(set(names.values())), names
        assert written > len(names), (written, len(names))

    def test_a_key_is_interned_once_however_many_slices_use_it(self, real):
        """Ten keys over 825 slices cost ten strings.

        The whole reason the names are interned rather than written per
        slice - and a claim the small fixture cannot make, because it
        has fewer slices than the contract has keys. Measured on the
        real capture instead.
        """
        names = real["trace"]["annotation_names"]
        written = sum(len(event["args"]) for event in real["trace"]["events"])
        assert len(names) == len(set(names.values())), (
            "a name is interned twice - the table is not a table")
        assert written > 20 * len(names), (written, len(names))


class TestThePlane2ValuesAreTheRecordsOwn:

    def test_each_annotation_equals_the_field_it_came_from(self, rendered):
        """Equality, sampled across every record the fixture has."""
        for pid, record in rendered["records"].items():
            cmd = record["cmd"]
            event = rendered["plane2"].get(cmd)
            assert event is not None, f"pid {pid} ({cmd}) has no slice"
            args = event["args"]
            assert args["cmd"] == record["cmd"]
            assert args["src"] == record["src"]
            assert args["exec_chain"] == record["exec_chain"]
            for key, field in (("cpu_us", "cpu_us"),
                               ("max_rss_kb", "max_rss_kb"),
                               ("exit_status", "exit_status")):
                if field in record:
                    assert args[key] == record[field], (pid, key)
                else:
                    assert key not in args, (
                        f"pid {pid} annotates {key} the record does not have")

    def test_a_hook_record_carries_no_exit_status_rather_than_a_zero(
            self, rendered):
        """The hook's destructor runs before the process has a status,
        and not at all when it is killed. An absent key and a `0` say
        different things, and only the first is true."""
        event = rendered["plane2"][LONG_CMD]
        assert event["args"]["src"] == "hook"
        assert "exit_status" not in event["args"]
        assert CATEGORY_FAILED not in event["categories"], (
            "a process whose exit was never observed is not a failure")
        # It still says which plane it is on (`UX-312`): the scope is
        # what a query filters by, and a slice missing from that filter
        # is a wrong answer rather than an absent one.
        assert event["categories"] == [CATEGORY_PLANE2]

    def test_the_numbers_are_numbers(self, rendered):
        args = rendered["plane2"]["cc -c ok.c"]["args"]
        assert isinstance(args["cpu_us"], int) and args["cpu_us"] == 15000
        assert isinstance(args["max_rss_kb"], int)
        assert isinstance(args["exec_chain"], int)
        # And the status is not: `signal:9` is a status, and a schema
        # that made it a number could not hold it.
        assert args["exit_status"] == "0"


class TestTheNameStaysShortAndTheArgvSurvives:

    def test_a_long_command_is_cut_in_the_name_and_whole_in_the_annotation(
            self, rendered):
        event = rendered["plane2"][LONG_CMD]
        assert len(event["name"]) == 120, event["name"]
        assert LONG_TAIL not in event["name"], (
            "the fixture no longer loses its tail to the cut - this clause "
            "tests nothing until it does")
        assert event["args"]["cmd"] == LONG_CMD
        assert LONG_TAIL in event["args"]["cmd"]

    @needs_real_capture
    def test_the_real_capture_has_commands_that_need_this(self):
        """Not a hypothetical. On `examples/06`, 412 of 813 records run
        past the 120-character name."""
        path = REAL_CAPTURE / "plane2.log.gz"
        with gzip.open(path, "rt", errors="ignore") as handle:
            records = list(stream_records(iter(parse_trace_lines(handle))))
        over = [r for r in records if len(r.get("cmd") or "") > 120]
        assert len(records) == 813 and len(over) == 412, (
            f"{len(over)} of {len(records)} - the figure in this file's "
            "header and in the task file is stale")

    def test_an_instant_is_annotated_too(self, rendered):
        """A process whose exit was never seen is exactly the one a
        reader wants the full command line of."""
        instants = [e for e in rendered["trace"]["events"]
                    if e["type"] == trackevent.TYPE_INSTANT
                    and "cmd" in e["args"]]
        assert len(instants) == 1, (
            "the other instant is `UX-311`'s run-identity marker, which is "
            "not a process and carries no command")
        assert instants[0]["args"]["cmd"] == "cc -c never-exits.c"
        assert "(no observed exit)" in instants[0]["name"]


class TestTheFailedCategoryIsExactlyTheFailures:

    def test_it_is_on_every_process_that_did_not_exit_zero(self, rendered):
        failed = {cmd for cmd, event in rendered["plane2"].items()
                  if CATEGORY_FAILED in event["categories"]}
        assert failed == {"cc -c broken.c", "cc -c killed.c"}

    def test_a_signal_counts_and_a_zero_does_not(self, rendered):
        """`UX-312` gave every slice its plane as a category too, so a
        process that succeeded carries its plane and nothing else -
        `failed` is still exactly the failures, which is what this has
        always been about."""
        assert rendered["plane2"]["cc -c killed.c"]["args"]["exit_status"] == \
            "signal:9"
        assert rendered["plane2"]["cc -c ok.c"]["categories"] == \
            [CATEGORY_PLANE2]
        assert CATEGORY_FAILED not in rendered["plane2"]["cc -c ok.c"][
            "categories"]

    def test_the_success_value_is_a_string_not_a_number(self):
        """`spine.c` writes `exit=%d`, so the status is text. Comparing
        it to the integer `0` would have called every process a failure;
        comparing truthiness would have called `"0"` one."""
        assert EXIT_STATUS_OK == "0"
        for record in ({"exit_status": "0"}, {"exit_status": 0}, {}):
            assert bga_timeline._plane2_categories(record) == (
                CATEGORY_PLANE2,), record
        assert bga_timeline._plane2_categories(
            {"exit_status": "signal:9"}) == (CATEGORY_PLANE2, CATEGORY_FAILED)


class TestThePlane1TaskSaysWhatItWas:

    def test_the_task_carries_element_kind_and_outcome(self, rendered):
        assert rendered["plane1"], "no Plane 1 slice was annotated"
        for event in rendered["plane1"]:
            args = event["args"]
            assert args["element"].endswith(".bst")
            assert args["task_type"] == "build"
            assert args["outcome"] == "SUCCESS"
            assert args["element_kind"] == "autotools", args

    def test_the_kind_comes_from_the_runs_own_graph(self, tmp_path):
        snapshot = _snapshot(tmp_path)
        kinds = element_kinds(str(snapshot))
        assert kinds["work-a.bst"] == "autotools"
        assert kinds["app.bst"] == "cmake"

    def test_a_graph_without_kinds_says_unknown_rather_than_nothing(
            self, tmp_path):
        snapshot = _snapshot(tmp_path, kinds=False)
        assert element_kinds(str(snapshot)) == {
            "base.bst": "unknown", "lib.bst": "unknown",
            "app.bst": "unknown", "extra.bst": "unknown"}

    def test_a_snapshot_with_no_graph_at_all_is_not_an_error(self, tmp_path):
        snapshot = _snapshot(tmp_path)
        (snapshot / "run" / "graph.json").unlink()
        assert element_kinds(str(snapshot)) == {}


class TestTheAnnotationsRideTheSamePass:

    def test_the_trace_is_the_same_trace_twice(self, tmp_path):
        """The digest clause. Gzip stamps a timestamp in its header, so
        the comparison is of the packets, not of the file."""
        snapshot = _snapshot(tmp_path)
        digests = []
        for index in (1, 2):
            out = tmp_path / f"trace-{index}.gz"
            render(str(snapshot), str(out))
            with gzip.open(out, "rb") as handle:
                digests.append(hashlib.sha256(handle.read()).hexdigest())
        assert digests[0] == digests[1], digests

    def test_the_writer_still_never_builds_an_event_list(self, tmp_path):
        """`UX-297`'s property, re-asserted here because this item is
        the one that gave the writer a reason to want the record again.
        """
        source = (
            "import sys\n"
            "import tools.bst_native_build_tracer as tracer\n"
            "import tools.bga_timeline as timeline\n"
            "def refuse(*a, **k):\n"
            "    raise AssertionError('the timeline built an event list')\n"
            "tracer.parse_trace_lines = refuse\n"
            "tracer.parse_trace_log = refuse\n"
            "tracer.pair_events = refuse\n"
            "print(timeline.render(sys.argv[1], sys.argv[2])['slices'])\n")
        snapshot = _snapshot(tmp_path)
        out = tmp_path / "trace.gz"
        done = subprocess.run(
            [sys.executable, "-c", source, str(snapshot), str(out)],
            cwd=REPO, capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
        assert int(done.stdout.strip()) > 0

    def test_what_the_annotations_cost_on_a_real_capture(self, real):
        """Stated rather than left to be discovered.

        Measured against the commit before this item, same snapshot:
        100,922 -> 330,188 B uncompressed (3.27x, +278 B/slice) and
        27,013 -> 51,102 B gzipped (1.89x, +29 B/slice). The ceilings
        below are those figures with room, so a change that doubles the
        cost again has to come and say so here.
        """
        with gzip.open(real["path"], "rb") as handle:
            body = handle.read()
        packed = os.path.getsize(real["path"])
        slices = real["result"]["slices"]
        assert slices == 826, slices   # 825 processes + the identity marker
        assert len(body) < 420_000, (
            f"{len(body)} B uncompressed over {slices} slices - measured at "
            f"330,188 when this was written, 348,014 once `UX-309`'s flows "
            f"and `UX-311`'s identity joined it")
        assert packed < 70_000, (
            f"{packed} B gzipped - measured at 51,102 when this was written, "
            f"58,150 with the flows and the identity")
