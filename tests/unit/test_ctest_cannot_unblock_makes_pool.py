"""UX-1337: ctest >= 3.29 joins an fd-pair pool through libuv, which sets
O_NONBLOCK on the open file description it shares with make; make 4.2.1
then aborts on EAGAIN. The wrapper hands ctest a reopened copy.
"""

import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPERS = REPO / "tools/native_trace/wrappers"
# Does what libuv's uv_pipe_open does to a dup of the auth's read fd, then reports.
FAKE = """#!{py}
import os, re
flags = os.environ.get("MAKEFLAGS", "")
print("MAKEFLAGS:" + flags)
m = re.search(r"--jobserver-auth=(\\d+),(\\d+)", flags)
if m:
    fd = os.dup(int(m.group(1)))
    os.set_blocking(fd, False)
    os.write(int(m.group(2)), b"+")
"""


def _fake(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "ctest").write_text(FAKE.format(py=sys.executable))
    (real / "ctest").chmod(0o755)
    return real


def _run(tmp_path, makeflags, pass_fds=()):
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(WRAPPERS), str(_fake(tmp_path)), env["PATH"]])
    env["MAKEFLAGS"] = makeflags
    r = subprocess.run(
        ["sh", str(WRAPPERS / "ctest"), "--test-dir", "b"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        pass_fds=pass_fds,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    return r.stdout.split("MAKEFLAGS:", 1)[1].strip()


def test_an_fd_pair_pool_stays_blocking_for_make(tmp_path):
    rfd, wfd = os.pipe()
    flags = _run(tmp_path, f" -j --jobserver-auth={rfd},{wfd}", pass_fds=(rfd, wfd))
    blocking = os.get_blocking(rfd), os.get_blocking(wfd)
    os.set_blocking(rfd, False)
    token = os.read(rfd, 8)
    os.close(rfd)
    os.close(wfd)
    assert blocking == (True, True)
    assert flags == "-j --jobserver-auth=9,9"
    # The reopened copy is the same pipe: the fake's token reached make's end.
    assert token == b"+"


def test_a_fifo_pool_passes_through(tmp_path):
    fifo = tmp_path / "js"
    os.mkfifo(fifo)
    assert _run(tmp_path, f"--jobserver-auth=fifo:{fifo}") == f"--jobserver-auth=fifo:{fifo}"


def test_no_pool_passes_through(tmp_path):
    assert _run(tmp_path, " -j8") == "-j8"
