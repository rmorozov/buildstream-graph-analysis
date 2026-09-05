"""UX-676: the envelope, and the intervals that violate it.

`traced processes running` counts slots. A process blocked on I/O or a
lock holds a slot and no core, so the CI owner's question - "were the
cores the binding resource?" - had no series to be answered from until
`UX-675` sampled `/proc/stat`.

Read against `tests/fixtures/host_cpu`, which is a real two-plane
capture of `examples/06-macro-micro-optimization` and the only committed
run with a CPU series at all. Its own README carries the readings; this
file asserts the arithmetic over them, and the clauses that do not need
a capture construct their windows instead.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.utilisation import envelope

FIXTURE = REPO / "tests" / "fixtures" / "host_cpu"

#: The capture's own numbers, from its README's measured block. Written
#: out rather than recomputed here, because a clause that derives its
#: expectation from the thing under test asserts only that two copies of
#: one bug agree (`test_every_captured_file_has_a_consumer`'s rule).
CORES = 4
CAPACITY = 4
BUSY_P50 = 1.884
BUSY_P95 = 3.255


@pytest.fixture(scope="module")
def analysed():
    return BuildEfficiencyAnalyzer().analyze(FIXTURE / "run")


class TestTheEnvelopeIsReadInCores:

    def test_capacity_is_the_smaller_of_the_two_caps(self, analysed):
        """`builders x max-jobs` is 16 on this capture and the host has
        four cores. Sixteen is what the scheduler was *allowed*; four is
        what it could be *given*, and a share against a number nothing
        can reach is not a verdict. Both are published - the reader can
        see the configured number is the one that does not bind."""
        section = analysed.utilization_envelope
        assert section["available"] is True, section
        assert section["configured_capacity_cores"] == 16
        assert section["cores"] == CORES
        assert section["capacity_cores"] == CAPACITY

    def test_the_percentiles_are_the_captures_own(self, analysed):
        section = analysed.utilization_envelope
        assert section["busy_cores_p50"] == BUSY_P50
        assert section["busy_cores_p95"] == BUSY_P95
        assert section["busy_share_p50"] == round(BUSY_P50 / CAPACITY, 3)

    def test_the_headline_says_the_verdict_and_carries_the_numbers(
            self, analysed):
        """`UX-220`'s rule: the sentence a reader acts on has the
        figures in it, so it can be quoted without the table."""
        section = analysed.utilization_envelope
        assert section["verdict"] == "not_binding"
        headline = section["headline"]
        assert "not the binding resource" in headline
        assert str(BUSY_P95) in headline and f"of {CAPACITY}" in headline

    def test_a_run_with_no_host_series_says_so_rather_than_zero(self):
        """The mutation this item's own Acceptance Test names, as a
        clause on a real run: `macro_micro` predates `UX-675`, so it has
        no `cpu_busy_cores` anywhere. "Nobody measured" and "the cores
        were fine" are different claims and the section keeps them
        apart - it publishes `available: false` and the sentence, not an
        absent key and not a busy share of zero."""
        result = BuildEfficiencyAnalyzer().analyze(
            REPO / "tests" / "fixtures" / "macro_micro" / "run")
        section = result.utilization_envelope
        assert section["available"] is False
        assert "host" in section["absence"] and section["absence"].strip()
        assert "busy_cores_p50" not in section
        assert result.underutilized_intervals == []


class TestTheIntervalsNameWhatWasRunning:

    def test_the_top_row_is_the_pinned_element_under_capacity(
            self, analysed):
        """`UX-676`'s Acceptance Test, verbatim: `core.bst` is
        `notparallel` in the example's own element file, so it builds at
        one job while three cores sit idle. The row names it, its
        `max_jobs`, and the cores busy under capacity."""
        rows = analysed.underutilized_intervals
        assert rows, "the capture's own README measures 11 rows"
        top = rows[0]
        assert [entry["element"] for entry in top["building"]] == ["core.bst"]
        assert [entry["max_jobs"] for entry in top["building"]] == [1]
        assert top["busy_cores"] < top["capacity_cores"]

    def test_the_ranking_is_by_lost_core_seconds(self, analysed):
        lost = [row["lost_core_seconds"]
                for row in analysed.underutilized_intervals]
        assert lost == sorted(lost, reverse=True), lost

    def test_a_row_points_at_a_library_query_and_its_own_window(
            self, analysed):
        """`UX-368`'s rule: a row names a query in the library rather
        than shipping SQL of its own. The bounds are the row's, in
        nanoseconds, which is what `trace_processor` compares `ts` in."""
        top = analysed.underutilized_intervals[0]
        assert top["trace_query"] == envelope.ROW_QUERY
        bounds = top["trace_bounds"]
        assert bounds["start_ns"] == top["start_us"] * 1000
        assert bounds["end_ns"] == top["end_us"] * 1000
        assert bounds["end_ns"] > bounds["start_ns"]

    def test_this_capture_never_ran_past_its_cores(self, analysed):
        """The mirror table, empty on a build that did not overcommit -
        and empty is a fact about the run, which is why the share beside
        it says the same thing as a number."""
        assert analysed.overcommitted_intervals == []
        assert analysed.utilization_envelope["overcommitted_share"] == 0.0


class TestTheRulesAreWhatTheyClaim:
    """The clauses no capture can settle, on constructed windows."""

    def _run(self, tasks, successors=None):
        return {"builders": 4, "native_max_jobs": 4, "tasks": tasks,
                "max_jobs": {"a.bst": 1}, "successors": successors or {}}

    def _samples(self, busy, load=0.0, pswpout=0):
        """`busy` readings become `len(busy) - 1` intervals: a rate is a
        delta over a gap, so the first reading opens the first window
        and closes none."""
        header = {"schema": "host-samples/v1", "monotonic_at_start": 100.0,
                  "wall_at_start": 1_700_000_000.0}
        rows = [{"t": 100.0, "cores": 4, "load1": load, "pswpout": 0}]
        for index, value in enumerate(busy, start=1):
            rows.append({"t": 100.0 + 2.0 * index, "cores": 4, "load1": load,
                         "pswpout": pswpout * index,
                         "cpu_busy_cores": value})
        return {"header": header, "samples": rows}

    def _building(self):
        return [{"element": "a.bst", "start_us": 0,
                 "finish_us": 1_800_000_000_000_000, "ready_us": 0}]

    def test_an_idle_core_with_no_work_is_not_a_violation(self):
        """`UX-48`'s split, per window. A machine with three cores spare
        and nothing to run is the graph's shape, not a defect - and a
        table that listed it would send a reader after capacity they
        cannot use."""
        out = envelope.compute(self._samples([0.5, 0.5, 0.5]),
                               self._run([]))
        assert out["underutilized_intervals"] == []
        assert out["envelope"]["underutilized_share"] == 0.0

    def test_the_same_window_with_work_in_it_is(self):
        out = envelope.compute(self._samples([0.5, 0.5, 0.5]),
                               self._run(self._building()))
        assert len(out["underutilized_intervals"]) == 2
        assert out["envelope"]["underutilized_share"] == 1.0

    def test_less_than_one_idle_core_is_not_enough(self):
        """The floor is a whole core because BuildStream dispatches
        whole jobs: 0.4 of a core spare could not have started
        anything. 3.5 busy of 4 leaves 0.5 and does not qualify; 3.0
        leaves exactly 1.0 and does."""
        spare = envelope.compute(self._samples([3.5, 3.5, 3.5]),
                                 self._run(self._building()))
        assert spare["underutilized_intervals"] == []
        exact = envelope.compute(self._samples([3.0, 3.0, 3.0]),
                                 self._run(self._building()))
        assert len(exact["underutilized_intervals"]) == 2

    def test_load_above_the_cores_is_overcommit(self):
        out = envelope.compute(self._samples([1.0, 1.0, 1.0], load=5.0),
                               self._run(self._building()))
        assert len(out["overcommitted_intervals"]) == 2
        assert out["envelope"]["verdict"] == "overcommitted"

    def test_a_page_written_to_swap_is_overcommit_whatever_the_load(self):
        out = envelope.compute(self._samples([1.0, 1.0, 1.0], pswpout=7),
                               self._run(self._building()))
        assert len(out["overcommitted_intervals"]) == 2
        assert out["envelope"]["verdict"] == "overcommitted"

    def test_overcommit_beats_under_use_in_the_verdict(self):
        """Both are true of this run - an idle core *and* swapping - and
        the answer is overcommit: a build that is swapping is past
        capacity rather than short of it, and the two remedies point in
        opposite directions."""
        out = envelope.compute(self._samples([1.0, 1.0, 1.0], pswpout=7),
                               self._run(self._building()))
        assert out["envelope"]["underutilized_share"] > 0
        assert out["envelope"]["verdict"] == "overcommitted"
        assert "More builders will make it slower" in \
            out["envelope"]["headline"]

    def test_one_reading_is_not_a_gap(self):
        out = envelope.compute(self._samples([1.0]), self._run([]))
        assert out == {"available": False, "absence": out["absence"]}
        assert "not a gap" in out["absence"]

    def test_the_table_is_capped_and_the_cap_is_the_worst_rows(self):
        """A four-hour build sampled every two seconds has 7,200
        windows. The cap is what makes this a table rather than the
        series again, and it keeps the *worst* rows because the ranking
        runs first."""
        busy = [0.0] * (envelope.INTERVALS_MAX + 11)
        out = envelope.compute(self._samples(busy),
                               self._run(self._building()))
        rows = out["underutilized_intervals"]
        assert len(rows) == envelope.INTERVALS_MAX
        assert all(row["lost_core_seconds"] > 0 for row in rows)


class TestTheFixtureSaysWhatItMeasured:

    def test_the_readme_carries_the_numbers_the_clauses_assert(self):
        """`UX-511`'s rule: a fixture's own prose is where the next
        round reads what it holds, so a figure that moved must move
        there too."""
        text = (FIXTURE / "README.md").read_text(encoding="utf-8")
        for number in (str(BUSY_P50), str(BUSY_P95), "not_binding"):
            assert number in text, number

    def test_the_series_is_the_one_the_sampler_writes(self):
        """Not re-encoded, not trimmed: the file is what `UX-675`'s
        sampler wrote, so a reader of this fixture is reading the
        contract and not a transcription of it."""
        lines = [json.loads(line) for line
                 in (FIXTURE / "host-samples.jsonl").read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        assert lines[0]["schema"] == "host-samples/v1"
        readings = [row for row in lines[1:] if "cpu_busy_cores" in row]
        assert len(readings) == len(lines) - 2, (
            "exactly one sample - the first - has no reading, because a "
            "rate needs a gap and the header's read is the same instant")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
