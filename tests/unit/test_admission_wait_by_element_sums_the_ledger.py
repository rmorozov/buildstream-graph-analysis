"""UX-1005 track B: `admission_wait_by_element` reads the shim's own
`admission_wait` ledger rows, keyed by element directly (no pid map)."""
from tools.jobserver.ledger import admission_wait_by_element


def test_two_waits_for_the_same_element_sum():
    rows = [
        {"event": "admission_wait", "element": "mod-a.bst", "pid": 1,
         "wait_us": 40_000, "t": 0},
        {"event": "admission_wait", "element": "mod-a.bst", "pid": 2,
         "wait_us": 60_000, "t": 1},
    ]

    assert admission_wait_by_element(rows) == {"mod-a.bst": 100_000}


def test_a_pool_tick_and_a_wrapper_row_are_not_admission_rows():
    rows = [
        {"action": "hold", "pool": 2, "busy_cores": 3},
        {"event": "acquire", "tool": "lld", "pid": 1, "tokens": 2, "t": 0},
    ]

    assert admission_wait_by_element(rows) == {}


def test_a_malformed_row_is_skipped_not_raised_on():
    rows = [{"event": "admission_wait", "element": None, "wait_us": 1},
            {"event": "admission_wait", "wait_us": 1},
            "not a dict"]

    assert admission_wait_by_element(rows) == {}


def test_no_rows_is_empty():
    assert admission_wait_by_element([]) == {}
    assert admission_wait_by_element(None) == {}
