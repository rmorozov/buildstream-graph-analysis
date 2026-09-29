"""UX-1134: the Builders line names a memory bound and the pinned --jobserver N."""

from bga.cli import _builder_pool_text_lines
from bga.correlate import compute_builder_pool_recommendation

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
        "memory-bound: giant.bst peaks 2.7 GB per job x 16 = 43.2 GB > 31 GB; "
        "auto withholds past 11 jobs, --jobserver 11 pins it"
    ) in first


def test_under_host_memory_the_line_is_unchanged():
    recommendation = _recommend({"giant.bst": int(1.9 * GB)}, 31 * GB)
    assert recommendation["memory_bound"] is None
    assert "memory-bound" not in _builder_pool_text_lines(recommendation)[0]


def test_exactly_host_memory_is_not_bound():
    assert _recommend({"giant.bst": 2 * GB}, 32 * GB)["memory_bound"] is None


def test_no_memory_reading_leaves_the_line_unchanged():
    recommendation = compute_builder_pool_recommendation(25, 16, 8, memory=(None, None))
    assert recommendation["memory_bound"] is None
