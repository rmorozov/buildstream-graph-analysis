"""UX-297: the Plane 2 report is what is read, and nothing else.

Round 40 measured the shape of the field's 1.5 GB `plane2.json`:
`summarize` embedded the whole per-process record list under
`"processes"`, and **no production reader consumed it**. `correlate`,
`analyze` and the store aggregate all read the per-element reductions
sitting beside it in the same file. Measured here, on a generated
200,000-process trace:

```text
                              before (round 39)        after
plane2.json on disk               69,641,647 B       43,879 B
share of it that is records             99.94%             0%
extract and write it                    12.4 s          8.1 s
```

The repository's own two-plane fixture is the same evidence from the
other side: `tests/fixtures/macro_micro/plane2.json` has carried no
`processes` key for many rounds, and every number the suite asserts is
computed from it.

**What this guard holds.** That the report carries the reductions and
not the records; that a capture taken *before* this item still
analyzes, because a store is full of those; that the analysis says
which of the two shapes served it; and - the clause that makes the
rest safe - that the fold and the list produce the same document. The
migration's guard is equality, and `summarize` is implemented as a
fold over the list, so the two paths are one code path with two
callers rather than two implementations that have to be kept level.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import contracts, plane2  # noqa: E402
from tools import bst_native_build_tracer as tracer  # noqa: E402

MACRO_MICRO = REPO / "tests/fixtures/macro_micro"

# One process per line pair, with a parent, a sandbox and a measurable
# exit: the shape `bga capture` writes. Small - this file is about what
# the report contains, and `test_analysis_memory_shape.py` is where the
# big traces are measured.
def _trace(path, processes=400, elements=8):
    with open(path, "w", encoding="utf-8") as handle:
        for index in range(processes):
            element = f"core-{index % elements:02d}.bst"
            inv = f"inv-{index % elements}"
            pid = 1000 + index
            cmd = f"/usr/bin/cc1plus -c file{index}.c -o file{index}.o"
            handle.write(f"START pid={pid} ppid=1000 ts={1000.0 + index} "
                         f"element={element} inv={inv} cmd={cmd}\n")
            handle.write(f"END pid={pid} ppid=1000 ts={1000.5 + index} "
                         f"element={element} inv={inv} utime_us={9000 + index} "
                         f"stime_us=1000 max_rss_kb={4096 + index} cmd={cmd}\n")


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    log = tmp_path_factory.mktemp("plane2") / "trace.log"
    _trace(str(log))
    return tracer.load_and_summarize(str(log))


class TestTheReportIsTheReductions:

    def test_it_does_not_carry_the_records(self, report):
        """The item's headline, and the one clause a reader of a
        gigabyte capture cares about."""
        assert plane2.RECORDS_KEY not in report, sorted(report)
        assert report["process_count"] == 400, report["process_count"]

    def test_the_reductions_are_all_still_there(self, report):
        """Non-vacuity: a report that dropped the aggregates too would
        pass the clause above and be useless. These are the keys every
        published number is computed from."""
        for key in ("cpu_time", "peak_memory", "per_element_parallelism",
                    "binary_cost", "configure_phase", "stream_coverage",
                    "by_element", "max_concurrency"):
            assert report.get(key), key
        assert report["cpu_time"]["per_element"], "no per-element CPU"

    def test_the_document_is_smaller_than_what_it_dropped(
            self, report, tmp_path):
        """The item's measurement, reproduced at this file's scale
        rather than quoted: the record list was the document.

        Priced both ways over one trace - the reductions the report
        carries against the records it used to carry beside them. On
        the 200,000-process trace the item measured, that ratio is
        1,587x; here it only has to be decisive, because a bound that
        held at four hundred processes and failed at a million would be
        measuring the fixture."""
        log = tmp_path / "priced.log"
        _trace(str(log))
        records = len(json.dumps(tracer.load_records(str(log)), default=str))
        reductions = len(json.dumps(report))
        assert records > reductions * 5, (
            f"records {records} B against reductions {reductions} B - the "
            "list was not the bulk of the document, so this fixture is not "
            "measuring what the item measured")

    def test_it_stamps_the_shape_it_is(self, report):
        assert report["schema"] == plane2.SCHEMA == "plane2/v3"
        assert plane2.shape_of(report) == "plane2/v3"


class TestAnOlderStoreStillReads:
    """A store is full of captures taken before this item. Reading has
    to stay one interface, or the fix breaks every run anyone has."""

    def test_the_legacy_shape_is_recognised_without_a_stamp(self):
        legacy = {"process_count": 3, "processes": [{"pid": 1}, {"pid": 2}]}
        assert plane2.shape_of(legacy) == "plane2/v1"

    def test_it_is_inventoried_as_read_and_never_written(self):
        assert contracts.superseded() == [
            "analyze/v2", "analyze/v3", "analyze/v4", "blast/v1",
            "compare/v1", "correlate/v1", "host/v1", "plane2/v1",
            "plane2/v2"]
        assert "plane2/v1" in contracts.ids()
        assert plane2.SCHEMA in contracts.ids()

    def test_the_provenance_says_which_one_served_the_numbers(self):
        new = plane2.provenance({"schema": "plane2/v3"})
        old = plane2.provenance({"process_count": 2, "processes": [1, 2]})
        assert new["records_embedded"] is False and new["records"] == 0
        assert old["records_embedded"] is True and old["records"] == 2
        # The sentence is what a reader meets, so it has to say
        # something: which command, or what it means for this run.
        assert "raw trace log" in new["note"], new["note"]
        assert "UX-297" in old["note"], old["note"]

    def test_a_saved_report_is_still_recognised_as_one(self, tmp_path, report):
        """`UX-38`: handing `report` a saved JSON report must not parse
        as zero trace lines and print a confident "0 processes". The
        marker key set lost `processes` with the list; these four are
        emitted by every report this tool has ever written."""
        path = tmp_path / "plane2.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        assert tracer.load_saved_report(str(path)) is not None
        legacy = tmp_path / "legacy.json"
        legacy.write_text(json.dumps(
            {"process_count": 1, "matched_count": 1, "by_binary": {"cc": 1},
             "by_element": {"a.bst": 1}, "processes": [{"pid": 1}]}),
            encoding="utf-8")
        assert tracer.load_saved_report(str(legacy)) is not None


class TestTheAnalysisSaysWhichShapeItRead:

    def test_the_two_plane_run_publishes_its_plane2_source(self):
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze",
             str(MACRO_MICRO / "run"), "--plane2",
             str(MACRO_MICRO / "plane2.json"), "--format", "json"],
            capture_output=True, text=True, cwd=REPO, timeout=300)
        assert done.returncode == 0, done.stderr[-2000:]
        document = json.loads(done.stdout)
        source = (document.get("plane2_coverage") or {}).get("source")
        assert source, "the payload does not say which Plane 2 shape it read"
        assert source["schema"] in ("plane2/v1", "plane2/v2",
                                   "plane2/v3"), source
        assert source["records_embedded"] is False, (
            "the committed fixture carries no record list - it has not for "
            "many rounds, which is the item's own evidence that nothing "
            "reads one")

    def test_the_contract_declares_it(self):
        from bga import schemas

        node = schemas.schema(schemas.ANALYZE)["properties"]["plane2_coverage"]
        source = node["properties"]["source"]
        assert "plane2/v3" in source["description"], source["description"]
        for key in ("schema", "records_embedded", "records", "note"):
            assert key in source["properties"], key


class TestTheAnswersAreKnown:
    """Known answers, because equality is not a check here.

    `summarize` is implemented as a fold, so "the fold agrees with the
    list" is true by construction and cannot catch a change to the
    shared arithmetic - it was measured passing against a deliberately
    broken concurrency sweep. What discriminates is a trace small
    enough to work out by hand.

    Three matched processes: `a` [0, 2], `c` [1, 3], `b` [2, 4].
    Two are alive together from 1 to 2 and again from 2 to 3, and the
    tie at t=2 is the case worth writing down - `b` starts exactly as
    `a` ends, and they are never both running. Peak is **2**, and a
    sweep that took the start before the end at equal timestamps would
    say 3.
    """

    @staticmethod
    def _records():
        def record(pid, cmd, start, end, cpu, rss):
            return {"pid": pid, "ppid": 1, "element": "one.bst",
                    "invocation": "inv-1", "cmd": cmd, "start_ts": start,
                    "end_ts": end, "duration_s": end - start, "open": False,
                    "cpu_us": cpu, "max_rss_kb": rss}
        return [
            record(2, "/usr/bin/cc1 -c a.c", 0.0, 2.0, 1_000_000, 4096),
            record(3, "/usr/bin/cc1 -c c.c", 1.0, 3.0, 2_000_000, 8192),
            record(4, "/usr/bin/as b.s", 2.0, 4.0, 500_000, 2048),
        ]

    @pytest.fixture
    def known(self):
        return tracer.summarize(self._records())

    def test_the_peak_is_two_and_the_tie_does_not_make_it_three(self, known):
        assert known["max_concurrency"] == 2

    def test_the_cpu_is_the_sum_of_the_three(self, known):
        cpu = known["cpu_time"]
        assert cpu["total_cpu_us"] == 3_500_000
        assert cpu["measured_processes"] == 3
        # The element's span is its first start to its last end.
        assert cpu["per_element"]["one.bst"]["wall_span_s"] == 4.0

    def test_the_peak_memory_is_the_largest_process_not_the_sum(self, known):
        assert known["peak_memory"]["per_element"]["one.bst"]["peak_rss_kb"] == 8192

    def test_the_wall_span_and_the_counts(self, known):
        assert known["wall_span_s"] == 4.0
        assert known["process_count"] == 3
        assert known["matched_count"] == 3 and known["open_count"] == 0
        assert known["by_binary"] == {"cc1": 2, "as": 1}


class TestTheFoldAndTheListAgree:
    """The migration's guard, run rather than argued.

    Every aggregate was split into `add` and `finish`. If the split
    changed any arithmetic, the fold and a straight list walk would
    disagree - so this builds the report both ways over one trace and
    compares the whole document.
    """

    def test_one_document_by_two_routes(self, tmp_path):
        log = tmp_path / "both.log"
        _trace(str(log), processes=600, elements=12)
        records = tracer.load_records(str(log))
        by_list = tracer.summarize(list(records))

        fold = tracer.Plane2Fold()
        for record in records:
            fold.add(record)
        by_fold = fold.report()

        assert json.dumps(by_list, sort_keys=True, default=str) == json.dumps(
            by_fold, sort_keys=True, default=str)
        # Non-vacuity: an empty report would satisfy the equality above.
        assert by_list["process_count"] == 600
        assert len(by_list["cpu_time"]["per_element"]) == 12

    def test_the_relabelling_happens_before_the_fold(self, tmp_path):
        """`UX-56`'s correction used to be a second pass that rewrote
        every record in place. There is no list to rewrite in a stream,
        so the fold applies it on arrival - and every aggregate is keyed
        on the element name, so applying it later would leave them all
        disagreeing."""
        log = tmp_path / "relabel.log"
        _trace(str(log), processes=40, elements=4)
        records = tracer.load_records(str(log))
        fold = tracer.Plane2Fold(resolved={"inv-0": "real-name.bst"})
        for record in records:
            fold.add(record)
        report = fold.report()
        assert fold.relabelled == 10, fold.relabelled
        assert "real-name.bst" in report["by_element"], report["by_element"]
        assert "core-00.bst" not in report["by_element"]
        assert "real-name.bst" in report["cpu_time"]["per_element"]
