"""UX-1012: `jobserver.per_element[].verdict` - `drew` is a joined
element whose peak width exceeded its own `max-jobs`; `joined == yes`
alone is the offer. Synthetic Plane 2 fixture; the terminal prints it.
"""

from types import SimpleNamespace

from bga.correlate import compute_jobserver_block
from bga.report.text import _render_jobserver_section


def _native_report():
    return {
        "jobserver": 4,
        "jobserver_pool": {"mode": "dynamic", "ceiling": 4, "capacity": 4},
        "jobserver_ledger": [{"event": "admission_wait", "element": "admitted.bst", "wait_us": 2_500_000}],
        "jobserver_decisions": [
            {"element": "giant.bst", "max_jobs": 8, "decision": "joined"},
            {"element": "level.bst", "max_jobs": 8, "decision": "joined"},
            {"element": "pinned.bst", "max_jobs": 1, "decision": "pinned"},
            {"element": "admitted.bst", "max_jobs": 8, "decision": "joined"},
        ],
        "per_element_parallelism": [
            {"element": "giant.bst", "peak_work_concurrency": 16},
            {"element": "level.bst", "peak_work_concurrency": 8},
            {"element": "pinned.bst", "peak_work_concurrency": 2},
            {"element": "admitted.bst", "peak_work_concurrency": 1},
        ],
        "jobserver_tokens_by_element": {},
    }


_ELEMENTS = ["admitted.bst", "giant.bst", "level.bst", "pinned.bst"]


def _per_element():
    return compute_jobserver_block(_native_report(), _ELEMENTS)["per_element"]


def test_a_peak_over_max_jobs_drew():
    row = _per_element()["giant.bst"]
    assert (row["peak_work_concurrency"], row["max_jobs"], row["verdict"]) == (16, 8, "drew")


def test_a_peak_at_max_jobs_was_offered_not_drawn():
    assert _per_element()["level.bst"]["verdict"] == "offered, not drawn"


def test_pinned_never_drew_whatever_its_peak():
    row = _per_element()["pinned.bst"]
    assert row["peak_work_concurrency"] > row["max_jobs"]
    assert row["verdict"] == "pinned"


def test_an_admission_token_alone_is_not_a_draw():
    """Under admission every sandbox holds one token; that is its slot."""
    row = _per_element()["admitted.bst"]
    assert (row["joined"], row["peak_work_concurrency"], row["admission_wait_us"]) == ("yes", 1, 2_500_000)
    assert row["verdict"] == "offered, not drawn"


def test_the_terminal_prints_the_row():
    result = SimpleNamespace(
        plane2_report=_native_report(),
        normalized_tasks=[SimpleNamespace(task_key=SimpleNamespace(element_uid=uid)) for uid in _ELEMENTS],
    )
    lines = _render_jobserver_section(result, None, False, frozenset(), False)
    assert lines[0] == "Jobserver:"
    giant = next(line for line in lines if "giant.bst" in line)
    assert "16/8" in giant and "drew" in giant
    admitted = next(line for line in lines if "admitted.bst" in line)
    assert "offered, not drawn" in admitted and "2.50s" in admitted
    assert lines.index(giant) < lines.index(admitted), "the draws are listed first"
