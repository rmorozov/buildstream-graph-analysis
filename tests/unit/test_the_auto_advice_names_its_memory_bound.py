"""UX-1134: the Builders line names a memory bound and the pinned --jobserver N,
one job's memory held free past the fit."""

from bga.cli import _builder_pool_text_lines
from bga.correlate import MEMORY_RESERVE_JOBS, compute_builder_pool_recommendation
from tools.jobserver import memory

GB = 10**9


def _recommend(peaks, host):
    return compute_builder_pool_recommendation(
        ready_set_width=25, host_cpu_count=16, critical_path_max_jobs=8, memory=(peaks, host)
    )


def test_peak_times_pool_over_host_memory_names_the_bound_and_its_fit():
    recommendation = _recommend({"giant.bst": int(2.7 * GB), "small.bst": GB // 10}, 31 * GB)
    first = _builder_pool_text_lines(recommendation)[0]
    assert first.startswith("Builders: 8 with --jobserver auto")
    assert (
        "memory-bound: giant.bst peaks 2.7 GB per job x (16 + 1 held free) = 45.9 GB > 31 GB; "
        "auto withholds past 10 jobs, --jobserver 10 pins it"
    ) in first


def test_under_host_memory_the_line_is_unchanged():
    recommendation = _recommend({"giant.bst": int(1.7 * GB)}, 31 * GB)
    assert recommendation["memory_bound"] is None
    assert "memory-bound" not in _builder_pool_text_lines(recommendation)[0]


def test_a_pool_that_fits_only_with_no_reserve_is_bound():
    # 2 GB x 16 = 32 GB fits 32 GB exactly; with one job held free it does not.
    bound = _recommend({"giant.bst": 2 * GB}, 32 * GB)["memory_bound"]
    assert bound is not None and bound["fit_jobs"] == 15, bound


def test_a_pool_that_fits_with_its_reserve_is_not_bound():
    assert _recommend({"giant.bst": 2 * GB}, 34 * GB)["memory_bound"] is None


def test_the_advice_and_the_gate_hold_the_same_reserve():
    assert MEMORY_RESERVE_JOBS == memory.MEMORY_RESERVE_JOBS == 1


def test_no_memory_reading_leaves_the_line_unchanged():
    recommendation = compute_builder_pool_recommendation(25, 16, 8, memory=(None, None))
    assert recommendation["memory_bound"] is None
