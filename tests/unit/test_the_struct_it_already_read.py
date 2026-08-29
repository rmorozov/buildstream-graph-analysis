"""UX-379: `hook.c` reads a `struct rusage` and published three fields.

`getrusage` is called twice per process, at exit, and `UX-45` took
`utime`/`stime` from it and `UX-63` took `ru_maxrss` on the explicit
argument that it came "from the same struct already being read". Six
more counters sat in that struct untouched, and they are the only
measurement bga has of two axes it otherwise only models: what a
process actually read and wrote, and whether it was waiting or being
preempted.

**They discriminate, which is why they are worth carrying.** Measured
on this host (4 cores) with a standalone `getrusage` probe, the same
command reading the same 64 MiB file:

```text
                       inblock   oublock   majflt   minflt   nvcsw   nivcsw
gcc -O2 (compute)        74,368        48       15    1,934      81        0
cat 64MB (warm cache)         0         0        0      171       4        0
cat 64MB (cold cache)   135,264         0        5      165      60        0
sh -c true                    0         0        0       66       1        0
```

`inblock` is 0 warm and 135,264 cold for the *same* command - it counts
what reached the block layer, so it separates "read from cache" from
"read from disk", which no other number bga has can do. 135,264 blocks
x 512 = 69,255,168 B against a 67,108,864 B file plus the reader's own
binary; that is where `_IO_BLOCK_BYTES` comes from.

And through the real tool, one project captured twice with only `-j`
changed:

```text
make -jN      procs    preempted   vol. waits   majflt
-j1             603           36       31,227      208
-j16            603       12,706       31,805      221
```

Identical work, identical voluntary waits, identical faults -
**preemption rises 353x**. That is the contention axis, measured rather
than inferred from low CPU concurrency.

**The clause that matters most is `test_pairing_carries_them`.** The
first implementation parsed the fields onto the *event* correctly and
the fold never saw one, because pairing rebuilds a record from a named
list of keys and the new ones were not in it. Every other clause here
was green at that moment; the report said `available: false` on a
capture whose raw log carried all six.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bst_native_build_tracer import (    # noqa: E402
    _IO_BLOCK_BYTES,
    _PRESSURE_FIELDS,
    Plane2Fold,
    compute_resource_pressure,
    parse_trace_lines,
    stream_records,
    stream_trace_events,
)

HOOK = REPO / "tools/native_trace/hook.c"
DICTIONARY = REPO / "docs/spec/trace-dictionary.md"

#: The raw-log spellings, and the record field each becomes.
RAW_TO_RECORD = {
    "inblock": "read_bytes",
    "oublock": "written_bytes",
    "majflt": "major_faults",
    "minflt": "minor_faults",
    "nvcsw": "voluntary_switches",
    "nivcsw": "involuntary_switches",
}


def _line(event, pid, ts, **rusage):
    fields = " ".join(f"{k}={v}" for k, v in rusage.items())
    return (f"{event} pid={pid} ppid=1 ts={ts} element=a.bst inv=1 "
            f"{fields} cmd=cc1 x.c").replace("  ", " ")


FULL = dict(utime=0.1, stime=0.2, cutime=0.0, cstime=0.0,
            maxrss_kb=1000, cmaxrss_kb=0,
            inblock=200, oublock=8, majflt=3, minflt=99,
            nvcsw=17, nivcsw=41)


class TestTheHookWritesThem:
    def test_every_field_is_emitted(self):
        """Source-level, because the alternative is a capture - and a
        field the hook does not write is invisible to every clause
        below, which would then be asserting against a fixture."""
        source = HOOK.read_text(encoding="utf-8")
        missing = [raw for raw in RAW_TO_RECORD if f"{raw}=%ld" not in source]
        assert missing == [], f"hook.c writes no {missing} field"
        for member in ("ru_inblock", "ru_oublock", "ru_majflt", "ru_minflt",
                       "ru_nvcsw", "ru_nivcsw"):
            assert member in source, member

    def test_the_line_buffer_fits_what_it_now_writes(self):
        """`format_rusage` returns 0 when the line does not fit, which
        drops *every* rusage field rather than the ones that overflowed.
        A buffer sized for six fields and asked for twelve is a silent
        regression of `UX-45` and `UX-63`, not of this item."""
        source = HOOK.read_text(encoding="utf-8")
        sizes = [int(n) for n in
                 __import__("re").findall(r"char rusage\[(\d+)\]", source)]
        assert sizes, "no rusage buffer found in hook.c"
        # The longest line this can produce: six `%.6f`-ish seconds and
        # six longs, generously. Measured lines run ~200 bytes.
        assert min(sizes) >= 320, (
            f"rusage buffer is {min(sizes)}; twelve fields need more room "
            f"and format_rusage drops all of them when they do not fit")


class TestTheParserReadsThem:
    def test_a_full_line_yields_every_field(self):
        event = parse_trace_lines([_line("END", 7, 1.0, **FULL)])[0]
        for raw, field in RAW_TO_RECORD.items():
            assert field in event, f"{raw} did not become {field}"

    def test_blocks_become_bytes(self):
        """`ru_inblock` counts 512-byte blocks. Publishing the raw count
        as `read_bytes` would be off by 512x, which is the kind of unit
        error `UX-341` exists about."""
        event = parse_trace_lines([_line("END", 7, 1.0, **FULL)])[0]
        assert event["read_bytes"] == FULL["inblock"] * _IO_BLOCK_BYTES
        assert event["written_bytes"] == FULL["oublock"] * _IO_BLOCK_BYTES
        assert _IO_BLOCK_BYTES == 512

    def test_counts_are_carried_as_counts(self):
        event = parse_trace_lines([_line("END", 7, 1.0, **FULL)])[0]
        assert event["major_faults"] == FULL["majflt"]
        assert event["minor_faults"] == FULL["minflt"]
        assert event["voluntary_switches"] == FULL["nvcsw"]
        assert event["involuntary_switches"] == FULL["nivcsw"]

    def test_an_older_hooks_line_still_parses(self):
        """`UX-45`'s rule: zero or more known keys before `cmd=`. A
        capture taken before this item has none of the six and must
        parse as it always did rather than failing."""
        old = dict(utime=0.1, stime=0.2, maxrss_kb=1000)
        event = parse_trace_lines([_line("END", 7, 1.0, **old)])[0]
        assert event["cpu_us"] == 300000
        for field in _PRESSURE_FIELDS:
            assert field not in event, (
                f"{field} invented for a hook that never wrote it")


class TestPairingCarriesThem:
    """The clause the first implementation failed. Parsing is not
    enough: `stream_records` rebuilds a record from a named list, so a
    field can be perfectly parsed onto the event and never reach a
    single consumer."""

    def _records(self):
        lines = [_line("START", 7, 1.0), _line("END", 7, 2.0, **FULL)]
        return list(stream_records(stream_trace_events(lines)))

    def test_a_paired_record_has_every_field(self):
        records = self._records()
        assert len(records) == 1, records
        for field in _PRESSURE_FIELDS:
            assert field in records[0], (
                f"{field} was parsed onto the event and dropped by pairing - "
                f"the report then reads `available: false` on a capture whose "
                f"raw log carries it")

    def test_the_values_survive_the_pairing(self):
        record = self._records()[0]
        assert record["read_bytes"] == FULL["inblock"] * _IO_BLOCK_BYTES
        assert record["involuntary_switches"] == FULL["nivcsw"]


class TestTheFoldSumsThem:
    def _records(self, *pressures):
        out = []
        for index, pressure in enumerate(pressures):
            record = {"element": "a.bst", "cmd": "cc1", "open": False,
                      "start_ts": float(index), "end_ts": index + 1.0,
                      "duration_s": 1.0, "pid": index, "src": "hook",
                      "invocation": "1", "exec_chain": 1}
            record.update(pressure)
            out.append(record)
        return out

    def test_they_are_summed_and_not_maximised(self):
        """The opposite rule from `peak_memory`, and the reason the two
        aggregates look different: a block read is an event, so two
        processes that each read 100 MB did read 200 MB."""
        one = dict(zip(_PRESSURE_FIELDS, (100, 1, 2, 3, 4, 5)))
        result = compute_resource_pressure(self._records(one, one))
        entry = result["per_element"]["a.bst"]
        assert entry["read_bytes"] == 200
        assert entry["involuntary_switches"] == 10

    def test_coverage_counts_the_processes_that_could_not_say(self):
        one = dict(zip(_PRESSURE_FIELDS, (100, 1, 2, 3, 4, 5)))
        result = compute_resource_pressure(self._records(one, {}))
        entry = result["per_element"]["a.bst"]
        assert (entry["measured"], entry["unmeasured"]) == (1, 1)
        assert entry["coverage"] == 0.5

    def test_no_measurement_is_unavailable_and_not_zero(self):
        """A build that touched no disk and a capture that could not
        look are different claims, and `0 B read` states the first."""
        result = compute_resource_pressure(self._records({}, {}))
        assert result["available"] is False
        assert "unavailable" not in result  # the key is `available`
        assert result["note"], "an unavailable block must say why"

    def test_zero_is_a_measurement_when_something_measured(self):
        """A read served from the page cache never reaches the block
        layer. `read_bytes: 0` beside a non-zero fault count is the
        fact, not a gap."""
        cached = dict(zip(_PRESSURE_FIELDS, (0, 0, 7, 8, 9, 10)))
        result = compute_resource_pressure(self._records(cached))
        assert result["available"] is True
        assert result["per_element"]["a.bst"]["read_bytes"] == 0
        assert result["per_element"]["a.bst"]["major_faults"] == 7

    def test_the_fold_and_the_function_agree(self):
        """`UX-297`'s equality: `compute_resource_pressure` folds a list
        and `Plane2Fold` folds a stream, and they are one code path."""
        one = dict(zip(_PRESSURE_FIELDS, (512, 1024, 2, 3, 4, 5)))
        records = self._records(one, one)
        fold = Plane2Fold()
        for record in records:
            fold.add(record)
        assert fold.pressure.finish() == compute_resource_pressure(records)


class TestTheReportAndTheTraceCarryThem:
    def test_the_report_publishes_the_block(self):
        one = dict(zip(_PRESSURE_FIELDS, (512, 0, 1, 2, 3, 4)))
        record = {"element": "a.bst", "cmd": "cc1", "open": False,
                  "start_ts": 0.0, "end_ts": 1.0, "duration_s": 1.0,
                  "pid": 1, "src": "hook", "invocation": "1",
                  "exec_chain": 1}
        record.update(one)
        fold = Plane2Fold()
        fold.add(record)
        report = fold.report()
        assert "resource_pressure" in report
        assert report["resource_pressure"]["available"] is True

    def test_the_trace_annotates_a_slice_with_them(self):
        from tools.bga_timeline import PLANE2_ANNOTATIONS, _plane2_annotations
        named = {key for key, _ in PLANE2_ANNOTATIONS}
        for field in ("read_bytes", "written_bytes", "major_faults",
                      "involuntary_switches"):
            assert field in named, f"{field} is on no Plane 2 slice"
        record = {"element": "a.bst", "src": "hook", "read_bytes": 0,
                  "written_bytes": 4096, "major_faults": 2,
                  "involuntary_switches": 9}
        args = dict(_plane2_annotations(record))
        # Zero is a measurement here, so it must survive the emitter's
        # own absent-rather-than-empty rule.
        assert args["read_bytes"] == 0
        assert args["involuntary_switches"] == 9

    def test_a_record_without_them_gets_no_key(self):
        from tools.bga_timeline import _plane2_annotations
        args = dict(_plane2_annotations({"element": "a.bst", "src": "hook"}))
        for field in ("read_bytes", "major_faults", "involuntary_switches"):
            assert field not in args, (
                f"{field} written for a record that has none - a slice would "
                f"then say this process did no I/O rather than that nobody "
                f"looked")

    def test_the_dictionary_documents_each_one(self):
        """`UX-312`: one documented place. The guard in
        `test_the_questions_ask_what_the_trace_answers.py` holds the
        general rule; this names the four so a reader of *this* item
        sees which."""
        text = DICTIONARY.read_text(encoding="utf-8")
        for field in ("read_bytes", "written_bytes", "major_faults",
                      "involuntary_switches"):
            assert f"| `{field}` |" in text, f"{field} has no dictionary row"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
