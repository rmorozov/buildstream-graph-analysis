"""UX-1008: a sandbox with no width promise whose peak exceeds `max-jobs + 1` reads `outside the pool`."""

from bga.correlate import compute_jobserver_block, jobserver_verdict


def _report(project_max_jobs=4):
    return {
        "jobserver": 4,
        "project_max_jobs": project_max_jobs,
        "jobserver_pool": {"mode": "dynamic", "ceiling": 4, "capacity": 4},
        "jobserver_decisions": [
            {"element": "joined.bst", "max_jobs": 4, "decision": "joined"},
            {"element": "pinned.bst", "max_jobs": 1, "decision": "pinned"},
        ],
        "per_element_parallelism": [
            {"element": "go.bst", "peak_work_concurrency": 8},
            {"element": "serial.bst", "peak_work_concurrency": 1},
            {"element": "edge.bst", "peak_work_concurrency": 5},
            {"element": "joined.bst", "peak_work_concurrency": 8},
            {"element": "pinned.bst", "peak_work_concurrency": 6},
        ],
    }


def _verdicts(report=None):
    elements = ["go.bst", "serial.bst", "edge.bst", "joined.bst", "pinned.bst"]
    block = compute_jobserver_block(report or _report(), elements)
    return {uid: row["verdict"] for uid, row in block["per_element"].items()}


def test_a_peak_of_eight_with_no_promise_is_named():
    assert _verdicts()["go.bst"] == "outside the pool"


def test_a_peak_of_one_is_not_named():
    assert _verdicts()["serial.bst"] == "unknown_kind"


def test_a_peak_one_over_max_jobs_is_not_named():
    assert _verdicts()["edge.bst"] == "unknown_kind"


def test_a_joined_peak_of_eight_drew():
    assert _verdicts()["joined.bst"] == "drew"


def test_a_pinned_wide_peak_is_named():
    assert _verdicts()["pinned.bst"] == "outside the pool"


def test_no_max_jobs_anywhere_names_nothing():
    assert _verdicts(_report(project_max_jobs=None))["go.bst"] == "unknown_kind"
    assert jobserver_verdict("unknown_kind", 8, None) == "unknown_kind"
