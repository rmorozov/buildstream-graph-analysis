"""UX-1005 track C: `_admitted_via_broker` is the shim's half of the
Decision's "never deadlock" clause - a grant through the per-element
FIFO wins when one arrives, and a timeout (no broker, or one that never
answers) falls back within a bounded time rather than hanging."""
import os
import time

from tools.native_trace.bwrap_shim import _admitted_via_broker


def test_a_real_grant_on_the_fifo_is_used(tmp_path):
    broker_dir = str(tmp_path)
    fifo_path = tmp_path / "mod-a.bst.fifo"
    os.mkfifo(fifo_path)
    writer_fd = os.open(fifo_path, os.O_RDWR)  # keeps the FIFO's buffer alive
    os.write(writer_fd, b"+")

    try:
        assert _admitted_via_broker(broker_dir, "mod-a.bst", 4242, timeout_s=1.0) is True
        requests = (tmp_path / "requests.jsonl").read_text()
        assert '"element": "mod-a.bst"' in requests
        assert '"pid": 4242' in requests
    finally:
        os.close(writer_fd)


def test_no_fifo_for_the_element_falls_back_immediately():
    start = time.time()
    assert _admitted_via_broker(str(None) + "/nowhere", "mod-a.bst", 1, timeout_s=2.0) is False
    assert time.time() - start < 0.5, "a missing FIFO must not wait for the timeout"


def test_a_fifo_with_no_grant_times_out_and_falls_back(tmp_path):
    broker_dir = str(tmp_path)
    fifo_path = tmp_path / "mod-b.bst.fifo"
    os.mkfifo(fifo_path)
    keeper_fd = os.open(fifo_path, os.O_RDWR)  # keeps it open, never writes

    try:
        start = time.time()
        assert _admitted_via_broker(broker_dir, "mod-b.bst", 1, timeout_s=0.2) is False
        elapsed = time.time() - start
        assert 0.15 <= elapsed < 2.0, f"must time out near timeout_s, took {elapsed:.2f}s"
    finally:
        os.close(keeper_fd)


def test_no_broker_dir_is_a_no_op():
    assert _admitted_via_broker(None, "mod-a.bst", 1) is False
