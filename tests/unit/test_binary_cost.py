"""UX-69: rank binaries by time, not by how often they ran.

On the real `freedesktop-sdk` capture, for `cmake-stage1.bst` — the
element Plane 1 correctly calls 43.5% of the critical path — the report's
count ranking read `sh`, `as`, `ninja`, `gcc`, `cc1`. The cost ranking
reads:

    cc1plus    885 procs   4352.6 CPU s   81.3%
    as        1918 procs    397.5 CPU s    7.4%
    dwz          1 proc     137.0 CPU s    2.6%

`cc1plus` — the heavy-C++-template signal — is absent from the count top
five and dominates by 10x. `dwz` is a *single* process holding 138.6s of
wall time, which counting cannot see at all and which more parallelism
cannot fix.

Everything is computed from records already captured, so this is a
missing analysis rather than a missing measurement.
"""
from tools.bst_native_build_tracer import compute_binary_cost


def _p(element, cmd, cpu_us=None, duration_s=None):
    r = {"element": element, "cmd": cmd}
    if cpu_us is not None:
        r["cpu_us"] = cpu_us
    if duration_s is not None:
        r["duration_s"] = duration_s
    return r


def test_the_expensive_binary_outranks_the_frequent_one():
    """The real inversion: many cheap invocations against few expensive
    ones."""
    records = (
        [_p("a.bst", "/bin/sh -c x", cpu_us=1_000, duration_s=0.1)] * 2000
        + [_p("a.bst", "/usr/libexec/cc1plus -O2", cpu_us=5_000_000, duration_s=6.0)] * 10
    )

    result = compute_binary_cost(records)["a.bst"]

    assert result["by_cpu"][0]["binary"] == "cc1plus"
    assert result["by_count"][0]["binary"] == "sh"


def test_the_cpu_share_is_reported():
    records = [
        _p("a.bst", "/usr/bin/cc1plus", cpu_us=9_000_000, duration_s=9.0),
        _p("a.bst", "/bin/sh", cpu_us=1_000_000, duration_s=1.0),
    ]

    top = compute_binary_cost(records)["a.bst"]["by_cpu"][0]

    assert top["binary"] == "cc1plus"
    assert top["cpu_share"] == 0.9


def test_a_single_process_holding_wall_time_is_called_out():
    """`dwz`: one process, 138.6s. A different fix from N processes -
    more parallelism cannot help, so it is named separately."""
    records = [
        _p("a.bst", "/usr/bin/dwz -m x", cpu_us=137_000_000, duration_s=138.6),
        _p("a.bst", "/bin/sh", cpu_us=1_000, duration_s=0.1),
    ]

    result = compute_binary_cost(records)["a.bst"]

    assert result["single_process_costs"][0]["binary"] == "dwz"
    assert result["single_process_costs"][0]["wall_s"] == 138.6


def test_a_repeated_binary_is_not_a_serialization_point():
    records = [_p("a.bst", "/usr/bin/cc1plus", cpu_us=5_000_000, duration_s=5.0)] * 4

    result = compute_binary_cost(records)["a.bst"]

    assert result["single_process_costs"] == []


def test_no_cpu_coverage_says_so_rather_than_ranking_by_count():
    """UX-45's rule: a report that silently falls back to counts while
    looking like a cost ranking is worse than one that declines."""
    records = [_p("a.bst", "/bin/sh"), _p("a.bst", "/usr/bin/cc1plus")]

    result = compute_binary_cost(records)["a.bst"]

    assert result["available"] is False
    assert "no CPU time was measured" in result["note"]


def test_elements_are_kept_separate():
    records = [
        _p("a.bst", "/usr/bin/cc1plus", cpu_us=9_000_000, duration_s=9.0),
        _p("b.bst", "/usr/bin/rustc", cpu_us=4_000_000, duration_s=4.0),
    ]

    result = compute_binary_cost(records)

    assert result["a.bst"]["by_cpu"][0]["binary"] == "cc1plus"
    assert result["b.bst"]["by_cpu"][0]["binary"] == "rustc"


def test_a_record_without_an_element_is_skipped():
    assert compute_binary_cost([{"cmd": "/bin/sh", "cpu_us": 1}]) == {}
