"""UX-378: the host's memory while the build runs, and how it ended.

bga talks about swapping in four separate places — `findings.py`,
`analyzer.py`, `report/text.py` and `questions.js` — and every sentence
was a model over `host_memory_mb` and a sum of per-process peaks.
Nothing sampled what the host was actually doing, so `grep -rn swap`
over the tree returned advice and never a reading.

**And an OOM was not merely undiagnosable — it was indistinguishable
from a normal exit.** `spine.c` writes `exit=signal:9` from the
kernel's exit-stop message; the parser keeps it; `bga timeline` renders
it and the trace dictionary documents it. `plane2/v2` had no key for
it, so neither the terminal report nor `bga view` could say a process
had been killed, and a killed process arrived as
`open_reason: no-observed-exit` — the same record a `sh -c` wrapper
that `_exit()`ed normally produces.

Measured on a real capture built for the question: an element that
kills a traced child with `SIGKILL`, captured twice.

```text
                       spine on            spine off
killed_by_signal       {"9": 1}            —
available              true                false
unknown                0                   23
```

The right-hand column is the clause that matters. "Nothing was killed"
is a claim a capture without a spine cannot make, and reporting zero
there is how a reader whose build was OOM-killed would be told their
build was healthy.

**The sampler shares the trace's clock**, which is the whole point:
`hook.c` stamps records with `clock_gettime(CLOCK_MONOTONIC)` and
`time.monotonic()` is that same clock, so a sample and a process record
sit on one timeline with no offset. On the capture above:

```text
trace records span   1317.6 .. 1319.1  (monotonic)
host samples span    1316.4 .. 1318.4  (monotonic)
```

One sample costs 37 microseconds — 1,000 reads of both `/proc` files in
0.037 s — so the two-second interval is set by how fast memory pressure
moves, not by what sampling costs.
"""
import json
import pathlib
import sys
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import run_store    # noqa: E402
from tools.bst_native_build_tracer import (    # noqa: E402
    HOST_SAMPLES_SCHEMA,
    HostSampler,
    Plane2Fold,
    compute_process_outcomes,
    read_host_sample,
    read_host_samples,
)

#: `UX-453`: the resolution `HostSampler._run` stamps each sample at -
#: `round(time.monotonic(), 3)`, one millisecond. Written here because
#: the clause below brackets a rounded value with unrounded readings and
#: has to say how far a stamp may legitimately have moved.
T_QUANTUM_S = 0.001


def _record(element="a.bst", **extra):
    record = {"element": element, "cmd": "cc -c x.c", "open": False,
              "start_ts": 0.0, "end_ts": 1.0, "duration_s": 1.0, "pid": 1,
              "src": "spine", "invocation": "1", "exec_chain": 1}
    record.update(extra)
    return record


@pytest.fixture(scope="module")
def sampled(tmp_path_factory):
    """One sampled series, and the bracket around it.

    Three clauses below assert three properties of the *same* kind of
    series - that it reads back, that its stamps are on the trace's
    clock, that its header pairs to wall time - and the first draft ran
    a sampler apiece, each with its own `time.sleep` so the thread had
    something to sample. 0.65s of sleeping for one series' worth of
    facts, in a file whose tier is a wall-clock budget: `UX-363`'s small
    tier is measured in CI and enforced as a `timeout`, so a sleep
    nobody needed is spent out of everyone's inner loop.

    The bracket has to be taken here rather than in a clause, because
    what the clock claim rests on is that the readings straddle the
    sampler - which they only do if the same call that starts it takes
    them.
    """
    path = tmp_path_factory.mktemp("host") / "host-samples.jsonl"
    before = time.monotonic()
    with HostSampler(str(path), interval_s=0.05):
        time.sleep(0.3)
    after = time.monotonic()
    return {"path": path, "before": before, "after": after,
            "back": read_host_samples(str(path))}


class TestTheHostIsSampled:
    def test_a_sample_names_what_it_read(self):
        sample = read_host_sample()
        if not sample:
            pytest.skip("this host exposes no /proc/meminfo")
        for key in ("mem_total_kb", "mem_available_kb", "swap_free_kb"):
            assert key in sample, key
        assert sample["mem_total_kb"] > 0

    def test_the_series_lands_and_reads_back(self, sampled):
        assert sampled["back"]["header"]["schema"] == HOST_SAMPLES_SCHEMA
        assert sampled["back"]["samples"], (
            "the sampler wrote a header and no samples")

    def test_it_stamps_the_traces_own_clock(self, sampled):
        """`hook.c` uses `clock_gettime(CLOCK_MONOTONIC)`; so does
        `time.monotonic()`. Asserted by bracketing, because the point is
        that no offset is needed - a sample taken between two readings
        of `time.monotonic()` must fall between them.

        `UX-453`: the bracket is widened by half of the sampler's own
        rounding quantum, and by nothing else. `_run` writes
        `round(time.monotonic(), 3)`; the readings around it are not
        rounded, so a sample taken within half a millisecond of an edge
        can round across it and this clause reddened once in a full
        `-n auto` run with nothing wrong. Measured over 400 sampled
        series at `interval_s=0.05`: worst excursion **0.000245 s**,
        inside `T_QUANTUM_S / 2` and nowhere near a real clock skew.
        The tolerance is tied to the sampler's resolution rather than
        set as slack - coarsen the `round` and this reddens again.
        """
        before, after = sampled["before"], sampled["after"]
        back = sampled["back"]
        if not back["samples"]:
            pytest.skip("this host exposes no /proc/meminfo")
        assert back["header"]["clock"] == "CLOCK_MONOTONIC"
        edge = T_QUANTUM_S / 2
        for sample in back["samples"]:
            assert before - edge <= sample["t"] <= after + edge, (
                f"sample at {sample['t']} is outside "
                f"[{before}, {after}] by more than the {T_QUANTUM_S}s "
                f"stamp resolution - the series is not on the trace's "
                f"clock and every join against a process record would be "
                f"silently wrong")

    def test_the_header_carries_the_pair_that_reaches_wall_time(self, sampled):
        """`UX-185`'s `bga-clocks` shape: a monotonic series is useless
        for "when did this happen" without one pairing to a wall clock."""
        header = sampled["back"]["header"]
        assert header["wall_at_start"] > 1_600_000_000
        assert isinstance(header["monotonic_at_start"], float)

    def test_a_truncated_last_line_is_tolerated(self, tmp_path):
        """What an interrupted capture leaves. `UX-157`'s rule: the file
        a reader gets is the file that was being written."""
        path = tmp_path / "host-samples.jsonl"
        path.write_text(
            json.dumps({"schema": HOST_SAMPLES_SCHEMA, "available": True})
            + "\n" + json.dumps({"t": 1.0, "mem_free_kb": 5}) + "\n"
            + '{"t": 2.0, "mem_fre',
            encoding="utf-8")
        back = read_host_samples(str(path))
        assert len(back["samples"]) == 1
        assert back["header"]["schema"] == HOST_SAMPLES_SCHEMA

    def test_the_store_names_the_file(self):
        """`UX-381` will tabulate the layout; the name must have one
        authority before it does."""
        assert run_store.HOST_SAMPLES_NAME == "host-samples.jsonl"


class TestTheReportSaysHowProcessesEnded:
    def test_a_killed_process_is_counted_by_its_signal(self):
        result = compute_process_outcomes([
            _record(exit_status="0"),
            _record(exit_status="signal:9"),
            _record(exit_status="signal:15"),
        ])
        assert result["available"] is True
        assert result["killed_by_signal"] == {"15": 1, "9": 1}
        assert result["killed"] == 2

    def test_a_non_zero_exit_is_not_a_kill(self):
        """`exit=1` and `exit=signal:1` are different facts, and the
        spine writes them differently for that reason."""
        result = compute_process_outcomes([_record(exit_status="1")])
        assert result["exited_nonzero"] == 1
        assert result["killed"] == 0

    def test_the_element_that_lost_a_process_is_named(self):
        result = compute_process_outcomes([
            _record(element="a.bst", exit_status="0"),
            _record(element="b.bst", exit_status="signal:9"),
        ])
        assert set(result["per_element"]) == {"b.bst"}, (
            "a clean element is listed, which makes the block O(elements) "
            "and buries the one that matters")
        assert result["per_element"]["b.bst"]["killed"] == 1

    def test_no_status_at_all_is_unavailable_and_not_zero_kills(self):
        """The clause the real capture proves: with no spine, every
        record is hook-written and carries no status. Reporting zero
        kills there tells a reader whose build was OOM-killed that
        nothing was killed."""
        result = compute_process_outcomes([_record(), _record()])
        assert result["available"] is False
        assert "killed" not in result, (
            "a count published for a capture that could not look")
        assert result["unknown"] == 2
        assert "spine" in result["note"]

    def test_the_fold_publishes_it(self):
        fold = Plane2Fold()
        fold.add(_record(exit_status="signal:9"))
        report = fold.report()
        assert report["process_outcomes"]["killed_by_signal"] == {"9": 1}

    def test_the_fold_and_the_function_agree(self):
        records = [_record(exit_status="0"), _record(exit_status="signal:9")]
        fold = Plane2Fold()
        for record in records:
            fold.add(record)
        assert fold.outcomes.finish() == compute_process_outcomes(records)


class TestTheCaptureAsksForIt:
    def test_the_snapshot_always_passes_the_flag(self):
        """Not behind an option. One sample is 37 microseconds and the
        question has no other source in a capture, so a snapshot that
        did not ask would be a snapshot that cannot answer."""
        source = (REPO / "tools/bga_snapshot.py").read_text(encoding="utf-8")
        assert '"--host-samples"' in source
        assert "HOST_SAMPLES_NAME" in source

    def test_the_tracer_takes_the_path_and_a_flag_offers_it(self):
        source = (REPO / "tools/bst_native_build_tracer.py").read_text(
            encoding="utf-8")
        assert "host_samples_path" in source
        assert '"--host-samples"' in source

    def test_the_sampler_wraps_the_build_and_only_the_build(self):
        """A series that included bga's own census, hook compile and
        shim probe would describe this tool rather than the build.

        Read off the parse tree rather than off string positions in the
        file. The first version of this clause compared `source.index`
        of three literals, which is the shape the fixing guide's item 9
        warns about - it asserts where text sits, not what runs, and it
        stays green for any rearrangement that keeps the order.
        """
        import ast
        tree = ast.parse((REPO / "tools/bst_native_build_tracer.py")
                         .read_text(encoding="utf-8"))
        func = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef)
                    and n.name == "run_traced_build")
        withs = [n for n in ast.walk(func) if isinstance(n, ast.With)
                 and any(isinstance(i.context_expr, ast.Name)
                         and i.context_expr.id == "sampler"
                         for i in n.items)]
        assert len(withs) == 1, "no single `with sampler:` in run_traced_build"
        called = {n.func.id for n in ast.walk(withs[0])
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "run_wrapped" in called, (
            "the sampler does not wrap the build, so its series describes "
            "some other interval than the one being measured")
        for tool_own_work in ("compile_hook", "compile_spine",
                              "probe_bwrap_shim", "install_bwrap_shim",
                              "census_project", "detect_stale_casd"):
            assert tool_own_work not in called, (
                f"{tool_own_work} runs inside the sampled window - the series "
                f"would describe bga's own startup as build memory pressure")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
