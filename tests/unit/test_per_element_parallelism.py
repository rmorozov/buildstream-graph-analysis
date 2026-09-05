"""Tests for UX-32: Plane 2's report was a census - counts by binary,
counts by element, and one global concurrency number - and never answered
the question the plane exists for: is *this element's* native build
system achieving the parallelism it should?

Real repro from the doc: a real capture of
`examples/06-macro-micro-optimization` in which `core.bst` ran `make -j1`
(BuildStream's `notparallel: True`, see UX-31) and took 13s where its
siblings took 2.5s. Everything needed to see that was already in the
tracer's own emitted `processes[]`; nothing computed it.
"""
from tools.bst_native_build_tracer import (
    classify_binary,
    compute_per_element_parallelism,
)


def _record(element, cmd, start, end):
    return {
        "pid": 1, "ppid": 0, "element": element, "cmd": cmd,
        "start_ts": start, "end_ts": end,
        "duration_s": end - start, "open": False,
    }


def _open_record(element, cmd, start):
    return {
        "pid": 1, "ppid": 0, "element": element, "cmd": cmd,
        "start_ts": start, "end_ts": None, "duration_s": None, "open": True,
    }


def _serialized_element():
    """One element pinned to -j1: four compiles back to back."""
    records = [_record("core.bst", "/usr/bin/make -f Makefile -j1", 0.0, 12.0)]
    for i in range(4):
        records.append(
            _record("core.bst", "/usr/libexec/gcc/cc1plus -quiet a.cpp", i * 3.0, i * 3.0 + 3.0)
        )
    return records


def _parallel_element():
    """One element at -j4: four compiles overlapping."""
    records = [_record("lib-a.bst", "/usr/bin/make -f Makefile -j4", 0.0, 3.5)]
    for _i in range(4):
        records.append(
            _record("lib-a.bst", "/usr/libexec/gcc/cc1plus -quiet b.cpp", 0.1, 3.1)
        )
    return records


def _profiles(records):
    return {p["element"]: p for p in compute_per_element_parallelism(records)}


# --- classification --------------------------------------------------------

def test_compiler_drivers_are_orchestration_not_work():
    """`gcc`/`g++` exec cc1plus and as and then wait - counting the
    driver as work double-counts every compile."""
    assert classify_binary("cc1plus") == "work"
    assert classify_binary("as") == "work"
    assert classify_binary("gcc") == "orchestration"
    assert classify_binary("make") == "orchestration"
    assert classify_binary("sh") == "orchestration"


def test_an_unknown_binary_is_unclassified_not_silently_bucketed():
    assert classify_binary("some-vendor-codegen") == "unclassified"


def test_unclassified_binaries_are_reported():
    records = _parallel_element() + [
        _record("lib-a.bst", "/opt/vendor/codegen --emit x", 0.0, 0.5)
    ]
    assert _profiles(records)["lib-a.bst"]["unclassified_binaries"] == {"codegen": 1}


# --- the measurement -------------------------------------------------------

def test_serialized_element_reports_peak_one():
    profile = _profiles(_serialized_element())["core.bst"]
    assert profile["peak_work_concurrency"] == 1
    assert profile["requested_jobs"] == 1


def test_parallel_element_reports_its_real_peak():
    profile = _profiles(_parallel_element())["lib-a.bst"]
    assert profile["peak_work_concurrency"] == 4
    assert profile["requested_jobs"] == 4


def test_orchestration_processes_do_not_inflate_concurrency():
    """The `make` wrapper is alive for the element's whole span; counting
    it would add one to every sample."""
    assert _profiles(_serialized_element())["core.bst"]["peak_work_concurrency"] == 1


def test_open_records_are_excluded():
    """Same reasoning as compute_max_concurrency: a process with no
    observed exit is not assumed to run forever."""
    records = _serialized_element() + [
        _open_record("core.bst", "/usr/libexec/gcc/cc1plus -quiet ghost.cpp", 0.0)
    ]
    assert _profiles(records)["core.bst"]["peak_work_concurrency"] == 1


# --- the findings ----------------------------------------------------------

def test_an_element_pinned_to_one_job_is_flagged_against_its_siblings():
    """The `notparallel` case, and the reason achieved-vs-requested
    cannot be the headline: this element gets exactly what it asked for."""
    profiles = _profiles(_serialized_element() + _parallel_element())
    assert "pinned_to_one_job" in profiles["core.bst"]["findings"]
    assert profiles["lib-a.bst"]["findings"] == []


def test_a_build_that_is_uniformly_j1_is_not_flagged():
    """If nothing in the build asked for more, `-j1` is the project's own
    choice, not an outlier worth naming."""
    profiles = _profiles(_serialized_element())
    assert profiles["core.bst"]["findings"] == []


def test_an_element_that_asked_for_parallelism_and_got_none_is_flagged():
    records = [_record("slow.bst", "/usr/bin/make -f Makefile -j8", 0.0, 12.0)]
    for i in range(4):
        records.append(
            _record("slow.bst", "/usr/libexec/gcc/cc1plus -quiet c.cpp", i * 3.0, i * 3.0 + 3.0)
        )
    assert "underachieved_requested_jobs" in _profiles(records)["slow.bst"]["findings"]


def test_an_element_with_too_little_work_to_fill_its_slots_is_not_flagged():
    """UX-09 measured exactly this and found it harmless: two source
    files cannot fill `-j4`, and that is not a defect."""
    records = [
        _record("tiny.bst", "/usr/bin/make -f Makefile -j4", 0.0, 3.5),
        _record("tiny.bst", "/usr/libexec/gcc/cc1plus -quiet d.cpp", 0.1, 3.0),
        _record("tiny.bst", "/usr/libexec/gcc/cc1plus -quiet e.cpp", 0.1, 3.0),
    ]
    assert _profiles(records)["tiny.bst"]["findings"] == []


def test_requested_jobs_is_none_when_no_make_invocation_was_traced():
    records = [_record("x.bst", "/usr/libexec/gcc/cc1plus -quiet f.cpp", 0.0, 1.0)]
    profile = _profiles(records)["x.bst"]
    assert profile["requested_jobs"] is None
    assert profile["achieved_vs_requested"] is None
    assert profile["findings"] == []
