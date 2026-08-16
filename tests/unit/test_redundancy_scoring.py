"""Tests for UX-37: Plane 2's redundant-operation findings summed
process time across elements BuildStream dispatched *concurrently*, and
ranked by that sum - so a 6x-repeated 50ms probe outranked a 2x-repeated
5s codegen step, and the list ran 37 entries deep down to `uname -r` at
0.001s.

Same category error `UX-26` fixed on Plane 1, plus a ranking problem the
fix surfaced: once findings are ranked by recoverable wall-clock, each
element's own `make -jN` takes every top slot, because its signature is
identical across elements by construction while doing entirely different
work in each.
"""
from tools.bst_native_build_tracer import (
    _elide_cmd, _is_element_build_driver, detect_redundant_operations,
)


def _record(element, cmd, start, end):
    return {
        "pid": 1, "ppid": 0, "element": element, "cmd": cmd,
        "start_ts": start, "end_ts": end,
        "duration_s": end - start, "open": False,
    }


def _findings(records):
    return {f["example_cmd"]: f for f in detect_redundant_operations(records)}


def test_wall_clock_figure_is_the_worst_element_not_the_sum():
    """Six elements ran concurrently, so eliminating five of six probes
    does not give the build back six probes' worth of time."""
    records = [
        _record(f"lib-{c}.bst", "/usr/bin/c++ CMakeCXXCompilerId.cpp", 0.0, 0.5)
        for c in "abcdef"
    ]
    finding = _findings(records)["/usr/bin/c++ CMakeCXXCompilerId.cpp"]
    assert finding["total_duration_s"] == 3.0
    assert finding["max_element_duration_s"] == 0.5


def test_worst_element_is_named():
    records = [
        _record("fast.bst", "/usr/bin/c++ probe.cpp", 0.0, 0.1),
        _record("slow.bst", "/usr/bin/c++ probe.cpp", 0.0, 2.0),
    ]
    finding = _findings(records)["/usr/bin/c++ probe.cpp"]
    assert finding["worst_element"] == "slow.bst"
    assert finding["max_element_duration_s"] == 2.0


def test_ranking_uses_recoverable_wall_clock_not_the_sum():
    """A 6x-repeated fast probe must not outrank a 2x-repeated slow one."""
    records = [
        _record(f"lib-{c}.bst", "/usr/bin/c++ fast-probe.cpp", 0.0, 0.05)
        for c in "abcdef"
    ] + [
        _record("x.bst", "/usr/bin/codegen big", 0.0, 5.0),
        _record("y.bst", "/usr/bin/codegen big", 0.0, 5.0),
    ]
    ranked = detect_redundant_operations(records)
    assert ranked[0]["example_cmd"] == "/usr/bin/codegen big"


def test_an_elements_own_build_driver_is_not_redundancy():
    """Every element runs `make -f Makefile -jN`; the signature matches
    across elements while the work does not."""
    records = [
        _record(f"lib-{c}.bst", "/usr/bin/make -f Makefile -j4", 0.0, 3.0)
        for c in "abcdef"
    ]
    assert detect_redundant_operations(records) == []


def test_build_drivers_are_recognized_through_the_wrappers_cmake_uses():
    assert _is_element_build_driver("/usr/bin/make -f Makefile -j4")
    assert _is_element_build_driver("/usr/bin/cmake -E env VERBOSE=1 /usr/bin/make -f Makefile -j4")
    assert _is_element_build_driver("env DESTDIR=/x cmake --build _builddir --target install")
    assert _is_element_build_driver("ninja -C _builddir")


def test_the_configure_step_is_still_considered_redundancy():
    """It really does repeat the same work in every element - and it is
    the class of finding UX-23 was built to catch."""
    cmd = 'cmake -B_builddir -H. -GUnix Makefiles -DCMAKE_VERBOSE_MAKEFILE=ON'
    assert not _is_element_build_driver(cmd)
    records = [_record(f"lib-{c}.bst", cmd, 0.0, 1.3) for c in "abcdef"]
    assert len(detect_redundant_operations(records)) == 1


def test_a_signature_seen_in_only_one_element_is_not_redundancy():
    records = [
        _record("a.bst", "/usr/bin/c++ only-here.cpp", 0.0, 1.0),
        _record("a.bst", "/usr/bin/c++ only-here.cpp", 1.0, 2.0),
    ]
    assert detect_redundant_operations(records) == []


def test_command_elision_keeps_the_binary_and_the_distinguishing_tail():
    """Truncating at a fixed prefix cut every real `cc1plus`/`ld`
    invocation off before anything that distinguished it."""
    cmd = "/usr/libexec/gcc/x86_64-linux-gnu/13/cc1plus -quiet " + ("-fboilerplate " * 20) + "-o /tmp/ccXYZ.s"
    elided = _elide_cmd(cmd)
    assert elided.startswith("/usr/libexec/gcc/x86_64-linux-gnu/13/cc1plus")
    assert elided.endswith("-o /tmp/ccXYZ.s")
    assert " ... " in elided


def test_a_short_command_is_not_elided():
    assert _elide_cmd("/usr/bin/uname -r") == "/usr/bin/uname -r"
