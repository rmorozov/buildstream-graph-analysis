"""UX-1336: the pre-1.13 jobserver patch (ninja PR #1140) is a client of an fd pair.

Neither its version nor its `--help` says so; its binary carries the
warning it prints when an explicit `-j` turns the client off.
"""

import os
import pathlib
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPERS = REPO / "tools/native_trace/wrappers"
NEEDLE = "# ninja: warning: -jN forced on command line; ignoring GNU make jobserver.\n"
# Prints argv and MAKEFLAGS, then whether fd 9 reads a token from the pool.
REPORT = """case " $* " in *" --version "*) echo 1.10.2; exit 0 ;; *" --help "*) exit 0 ;; esac
echo "ARGV:$*"
echo "MAKEFLAGS:$MAKEFLAGS"
if [ -e /dev/fd/9 ]; then echo "FD9:$(dd bs=1 count=1 iflag=nonblock 2>/dev/null <&9)"; fi
"""


def _real(tmp_path, patched):
    real = tmp_path / "real"
    real.mkdir()
    (real / "ninja").write_text("#!/bin/sh\n" + (NEEDLE if patched else "") + REPORT)
    (real / "ninja").chmod(0o755)
    return real


def _run(tmp_path, real, makeflags):
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(WRAPPERS), str(real), env["PATH"]])
    env["MAKEFLAGS"] = makeflags
    r = subprocess.run(
        ["sh", str(WRAPPERS / "ninja"), "-j8", "all"], env=env, capture_output=True, text=True, timeout=10
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    return dict(line.split(":", 1) for line in r.stdout.splitlines() if ":" in line)


def _pool(tmp_path, tokens):
    fifo = tmp_path / "js"
    os.mkfifo(fifo)
    fd = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    os.write(fd, tokens)
    return fifo, fd


def _left(fd):
    try:
        return len(os.read(fd, 64))
    except BlockingIOError:
        return 0


def test_a_patched_ninja_on_a_fifo_gets_an_fd_pair_and_no_dash_j(tmp_path):
    fifo, fd = _pool(tmp_path, b"+++")
    out = _run(tmp_path, _real(tmp_path, patched=True), f"--jobserver-auth=fifo:{fifo}")
    left = _left(fd)
    os.close(fd)
    assert out["ARGV"] == "all"
    # The patch reads `--jobserver-fds=` first; the fifo auth stays last for gcc and make.
    assert out["MAKEFLAGS"] == f"--jobserver-fds=9,9 --jobserver-auth=fifo:{fifo}"
    assert out["FD9"] == "+"
    # The wrapper held nothing: the client took one of three, two are left.
    assert left == 2


def test_a_patched_ninja_on_an_fd_pair_keeps_it(tmp_path):
    rfd, wfd = os.pipe()
    os.set_inheritable(rfd, True)
    os.set_inheritable(wfd, True)
    os.write(wfd, b"++")
    env_flags = f"--jobserver-auth={rfd},{wfd}"
    real = _real(tmp_path, patched=True)
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(WRAPPERS), str(real), env["PATH"]])
    env["MAKEFLAGS"] = env_flags
    r = subprocess.run(
        ["sh", str(WRAPPERS / "ninja"), "-j8", "all"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        pass_fds=(rfd, wfd),
    )
    os.set_blocking(rfd, False)
    left = _left(rfd)
    os.close(rfd)
    os.close(wfd)
    assert r.returncode == 0, r.stderr
    out = dict(line.split(":", 1) for line in r.stdout.splitlines() if ":" in line)
    assert out["ARGV"] == "all"
    assert out["MAKEFLAGS"] == env_flags
    assert left == 2


def test_an_unpatched_1_10_still_gets_a_held_width(tmp_path):
    fifo, fd = _pool(tmp_path, b"+++")
    out = _run(tmp_path, _real(tmp_path, patched=False), f"--jobserver-auth=fifo:{fifo}")
    os.close(fd)
    assert out["ARGV"] == "-j 4 all"
    assert out["MAKEFLAGS"] == f"--jobserver-auth=fifo:{fifo}"
