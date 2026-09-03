"""UX-406: with the spine on, the trace counted every process twice.

`UX-107` established the rule and `merge_record_streams` implements it:
a dynamically-linked process is recorded twice - once by the hook, once
by the spine - and the two records are one process. The *report* has
joined them since round 12. The **timeline never called the join**, so
a spine-on capture of 813 processes emitted 1,626 slices:

```text
select debug.src, count(*) from ... (trace_processor v57.2)
  hook    813
  spine   813
```

Four of the fourteen canned questions then answered confidently and
wrongly on `examples/06`:

```text
concurrency-curve   peak 44        plane2.json max_concurrency: 24
process-storm       core.bst 224   report says 112
cpu-versus-wall     core.bst 13.77 CPU-s   report says 7.14
sandbox-tax         core.bst -112.1 unaccounted seconds
```

This is not `UX-395` (a format that drops a table): these queries
resolve and return **wrong numbers**, which is strictly worse. Round 63
checked that twelve of fourteen queries *resolve*; nobody had checked
that their answers are right with both sources on.

`docs/spec/trace-dictionary.md` promises the counter's peak equals the
report's `max_concurrency` "by construction", and `UX-310` was closed on
that equality - on a capture whose spine was off.

Re-measured in round 65 on a fresh spine-on capture of a cold
`lib-c.bst`, decoded from the wire:

```text
                          before              after       plane2.json
Plane 2 slices               158                 87       process_count 87
  src=spine                   87                 87
  src=hook                    71                  0
concurrency counter peak      24                 13       max_concurrency 13
```

71 hook records against 87 spine ones, not 87: sixteen of those
processes are static, and the spine is the only mechanism that sees one
(`UX-105`). Which is why the number to check is the **joined** count and
not "half the slices".

**The fixture below is built, not captured.** Ten raw lines, five
records, three processes: two seen by both mechanisms and one static
seen only by the spine, with the two dynamic ones overlapping so the
counter's peak is a number worth checking. A capture with a real spine
is gitignored (`UX-189`) and needs `bst`; this needs neither and fails
for the same reason.
"""
import gzip
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from tools.bga_timeline import (                          # noqa: E402
    DEFAULT_OUTPUT, FORMAT_TRACKEVENT, render)
from tools.bst_native_build_tracer import (               # noqa: E402
    merge_record_streams, stream_records, stream_trace_events)
from tools.native_trace import trackevent                 # noqa: E402

from test_the_timeline_speaks_perfetto import _fields     # noqa: E402

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

_WRAPPED_LOG = """\
[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:10,100] INFO: [00:00:10][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:10,200] INFO: Return code: 0
"""

#: Three processes, five records. `101` and `103` are dynamically
#: linked and therefore seen twice; `102` is static and seen only by the
#: spine, which is the coverage class the spine exists for (`UX-105`).
#: The overlap of 101 and 103 is what makes the concurrency counter's
#: peak a number worth checking: two at once, never four.
_RAW = """\
START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
START pid=101 ppid=1 ts=1000.000000 element=work-a.bst src=spine cmd=cc -c main.c
START pid=103 ppid=1 ts=1000.500000 element=work-a.bst cmd=cc -c other.c
START pid=103 ppid=1 ts=1000.500000 element=work-a.bst src=spine cmd=cc -c other.c
START pid=102 ppid=1 ts=1003.000000 element=work-a.bst src=spine cmd=/usr/bin/gen
END pid=101 ppid=1 ts=1002.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.000000 element=work-a.bst src=spine exit=0 cmd=cc -c main.c
END pid=103 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c other.c
END pid=103 ppid=1 ts=1002.500000 element=work-a.bst src=spine exit=0 cmd=cc -c other.c
END pid=102 ppid=1 ts=1004.000000 element=work-a.bst src=spine exit=0 cmd=/usr/bin/gen
"""

#: What the raw log describes, so the numbers below are stated rather
#: than read off whatever the code produced.
PROCESSES = 3
RAW_RECORDS = 5
PEAK_CONCURRENCY = 2


def _snapshot(into):
    snapshot = pathlib.Path(into) / "20260821T120000Z"
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot / "build.log").write_text(_WRAPPED_LOG, encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    dirs_exist_ok=True)
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write(_RAW)
    return snapshot


def _decode(path):
    """Plane 2 slices by their `src` annotation, and counter samples."""
    raw = gzip.open(path, "rb").read()
    packets = [v for f, _w, v in _fields(raw) if f == trackevent.TRACE_PACKET]
    names = {}
    slices, counters = [], []
    for packet in packets:
        body = interned = None
        for field, _wire, value in _fields(packet):
            if field == trackevent.PACKET_TRACK_EVENT:
                body = value
            elif field == trackevent.PACKET_INTERNED_DATA:
                interned = value
        if interned is not None:
            for field, _wire, value in _fields(interned):
                if field != trackevent.INTERNED_DEBUG_ANNOTATION_NAMES:
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
        kind = counter_value = None
        annotations = []
        for field, _wire, value in _fields(body):
            if field == trackevent.EVENT_TYPE:
                kind = value
            elif field == trackevent.EVENT_COUNTER_VALUE:
                counter_value = value
            elif field == trackevent.EVENT_DEBUG_ANNOTATIONS:
                key = val = None
                for inner, _w, payload in _fields(value):
                    if inner == trackevent.ANNOTATION_NAME_IID:
                        key = payload
                    elif inner == trackevent.ANNOTATION_STRING_VALUE:
                        val = payload.decode("utf-8")
                annotations.append((key, val))
        if kind == trackevent.TYPE_SLICE_BEGIN:
            slices.append(annotations)
        elif kind == trackevent.TYPE_COUNTER:
            counters.append(counter_value)
    sources = []
    for annotations in slices:
        args = {names.get(iid): value for iid, value in annotations}
        if "src" in args:
            sources.append(args["src"])
    return {"plane2_slices": len(sources), "sources": sources,
            "counter_peak": max(counters) if counters else None}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("one-process-one-slice")
    snapshot = _snapshot(tmp)
    out = tmp / DEFAULT_OUTPUT[FORMAT_TRACKEVENT]
    result = render(str(snapshot), str(out))
    return {"trace": _decode(out), "result": result}


class TestTheFixtureIsTheCase:
    """The raw log really does carry the double-record shape."""

    def test_the_records_are_five_and_the_processes_are_three(self):
        records = list(stream_records(stream_trace_events(_RAW.splitlines())))
        assert len(records) == RAW_RECORDS, (
            "the fixture stopped describing a capture where a process is "
            "seen twice, so nothing below is testing this item")
        assert len(merge_record_streams(records)) == PROCESSES, (
            "`merge_record_streams` is UX-107's join and the definition of "
            "'one process'; if it disagrees with the fixture the fixture is "
            "wrong")


class TestOneProcessIsOneSlice:
    def test_the_trace_carries_one_slice_per_process(self, rendered):
        seen = rendered["trace"]
        assert seen["plane2_slices"] == PROCESSES, (
            f"{seen['plane2_slices']} Plane 2 slices for {PROCESSES} "
            f"processes. With both mechanisms recording, the timeline used "
            f"to emit both records - 813 hook slices beside 813 spine ones "
            f"on examples/06 - and four canned queries then answered ~2x")

    def test_no_process_is_emitted_once_per_mechanism(self, rendered):
        """The shape of the defect, not only its count.

        A trace with the right *number* of slices and one of them
        duplicated would pass a count alone.
        """
        sources = rendered["trace"]["sources"]
        assert sources.count("hook") == 0, (
            f"a hook-sourced slice survived the join: {sources}. The spine "
            f"is the base and the hook is enrichment (UX-107), so a joined "
            f"record carries src=spine")
        assert len(sources) == len(set(range(len(sources)))), sources

    def test_the_counter_peak_is_the_reports_max_concurrency(self, rendered):
        """`docs/spec/trace-dictionary.md`'s equality, in the field.

        It read "by construction" there until `UX-572`; both sentences
        name this clause and the join now.

        `UX-310` was closed on this equality against a capture whose
        spine was off, so the sentence had never been checked in the
        state that breaks it: unjoined, both records of one process are
        alive at once and every process counts twice.
        """
        assert rendered["trace"]["counter_peak"] == PEAK_CONCURRENCY, (
            f"the concurrency counter peaks at "
            f"{rendered['trace']['counter_peak']}; the run has "
            f"{PEAK_CONCURRENCY} processes alive at once. On examples/06 "
            f"this read 44 against a published max_concurrency of 24")


class TestTheStreamingPassesAreUnaffected:
    """Why only one of the three readers needed the join.

    `pick_anchor` and `element_spans` fold a **max per element** out of
    the stream, and a duplicate record has the same span as its partner,
    so a max over both is the max over one. Stated as a clause rather
    than in a comment, because "this reader is safe" is exactly the kind
    of claim that stops being true quietly.
    """

    def test_a_max_over_both_records_is_the_max_over_one(self):
        records = list(stream_records(stream_trace_events(_RAW.splitlines())))
        merged = merge_record_streams(records)

        def longest(rows):
            return max(row["end_ts"] - row["start_ts"] for row in rows
                       if row.get("end_ts") is not None)

        assert longest(records) == longest(merged), (
            "the streaming passes take a max per element and would need "
            "the join too if a duplicate could change one")
