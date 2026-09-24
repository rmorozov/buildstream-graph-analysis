"""UX-905: `tools/hang_witness.py` names the processes, the FIFOs they hold and
the pool's unread tokens once the host goes quiet - read off a real FIFO."""
import os
import subprocess
import sys

import pytest

from tools import hang_witness


@pytest.fixture
def held_pool(tmp_path):
    """A FIFO named `jobserver` with three tokens, held open by a child."""
    path = tmp_path / "jobserver"
    os.mkfifo(path)
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    os.write(fd, b"+++")
    child = subprocess.Popen(
        [sys.executable, "-c", f"import os,time; os.open({str(path)!r}, os.O_RDWR); time.sleep(30)"])
    try:
        for _ in range(100):
            rows = [r for r in hang_witness.process_rows() if r["pid"] == child.pid]
            if rows and rows[0]["fifos"]:
                break
            subprocess.run(["sleep", "0.05"], check=True)
        yield path, child
    finally:
        child.kill()
        child.wait()
        os.close(fd)


def test_the_holder_and_its_fifo_are_named(held_pool):
    path, child = held_pool
    row = next(r for r in hang_witness.process_rows() if r["pid"] == child.pid)
    assert [f["target"] for f in row["fifos"]] == [str(path)]
    assert row["state"] in {"S", "R"} and "time.sleep" in row["argv"]


def test_the_pools_unread_tokens_are_counted(held_pool):
    path, _child = held_pool
    lines = hang_witness.render(hang_witness.process_rows())
    assert f"jobserver fifo {path}: 3 token(s) unread" in lines


def test_one_dump_per_quiet_episode(held_pool, tmp_path, capsys):
    out = tmp_path / "witness.log"
    dumps = hang_witness.watch(0.05, 0.0, 1e9, str(out), rounds=3)
    assert dumps == 1
    printed = capsys.readouterr().out
    assert printed.startswith("::warning::hang witness:")
    assert printed.count("::warning::") == 1 and out.read_text() == printed


def test_a_busy_host_is_never_dumped(tmp_path, capsys):
    assert hang_witness.watch(0.05, 0.0, -1.0, str(tmp_path / "w.log"), rounds=2) == 0
    assert capsys.readouterr().out == ""
