"""UX-1001: ninja 1.13's jobserver client never names itself in `--help`,
so both the probe and the wrapper read the version too, and a client ninja
gets a `fifo:` auth - it rejects the pipe style outright."""
import fcntl
import os
import struct
import subprocess
import termios

import pytest

from tests.unit.test_a_compiler_lto_shim_fills_the_box import BIND_DST, _bst_args, _makeflags_value
from tests.unit.test_bwrap_shim import (
    _NINJA_1_11_1_HELP,
    _argv_with_jobs,
    _decide_through_the_real_gate,
    _fake_bwrap_with_make,
)
from tools.native_trace.bwrap_shim import build_shim_argv, ninja_is_client, probe_ninja

WRAPPERS = os.path.join(os.path.dirname(__file__), "..", "..", "tools/native_trace/wrappers")

# Real, pasted: the first three lines of `ninja --help` from v1.13.2, built
# from its tag - the rest is 1.11.1's, word for word, with no "jobserver".
_NINJA_1_13_2_HELP = _NINJA_1_11_1_HELP.replace('("1.11.1")', '("1.13.2")')


def _ninja_body(version):
    return ('case "$*" in\n'
            f'  *"ninja --version") echo "{version}"; exit 0 ;;\n'
            '  *"ninja --help") printf \'usage: ninja [options]\\n\'; exit 0 ;;\n'
            "esac\n")


@pytest.mark.parametrize(("version", "client"), [
    ("1.11.1", False), ("1.12.1", False), ("1.13.0", True), ("1.13.2", True),
    ("1.20.0", True), ("2.0.0", True), (None, False)])
def test_the_version_decides_when_the_help_is_silent(version, client):
    assert "jobserver" not in _NINJA_1_13_2_HELP.lower()
    assert ninja_is_client(version, _NINJA_1_13_2_HELP) is client


def test_the_probe_reads_1_13_2_as_a_client(tmp_path):
    fake = tmp_path / "bwrap"
    fake.write_text("#!/bin/sh\n" + _ninja_body("1.13.2"))
    fake.chmod(0o755)
    assert probe_ninja(str(fake), [], None)["jobserver_client"] is True


def test_a_meson_element_on_1_13_2_reads_ninja_client(tmp_path, monkeypatch):
    policy, _marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, "meson", _argv_with_jobs("-j4"), _ninja_body("1.13.2"),
        wrappers_dir=str(tmp_path / "wrappers"))
    assert policy == "ninja_client"


def test_a_client_ninja_is_handed_a_fifo_not_the_raw_fd(tmp_path, monkeypatch):
    marker = tmp_path / "marker"
    fake = _fake_bwrap_with_make(tmp_path / "bwrap", marker, BIND_DST, "4.4.1")
    head, rest = open(fake, encoding="utf-8").read().split("\n", 1)
    with open(fake, "w", encoding="utf-8") as handle:
        handle.write(head + "\n" + _ninja_body("1.13.2") + rest)
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src)
    monkeypatch.setenv("BST_TRACE_JOBSERVER", os.path.join(bind_src, "jobserver"))
    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap=fake, bst_args=_bst_args("git-minimal"), bind_src=bind_src,
            bind_dst=BIND_DST, preload_so=f"{BIND_DST}/hook.so",
            trace_log=f"{BIND_DST}/trace.log", jobserver_fd=read_fd, element_kind="meson",
            ninja_probe=probe_ninja(fake, [], None))
    finally:
        os.close(read_fd)
        os.close(write_fd)
    assert _makeflags_value(argv) == f"--jobserver-auth=fifo:{BIND_DST}/jobserver"


def _unread(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        return struct.unpack("i", fcntl.ioctl(fd, termios.FIONREAD, struct.pack("i", 0)))[0]
    finally:
        os.close(fd)


@pytest.mark.parametrize(("version", "style", "expect", "held"), [
    ("1.13.2", "fifo", "REAL:-v -C out", 0),
    ("1.12.1", "fifo", "REAL:-j 4 -v -C out", 3),
    ("1.13.2", "fd", "REAL:-j 4 -v -C out", 3)])
def test_the_wrapper_steps_aside_only_for_a_client_on_a_fifo(
        tmp_path, version, style, expect, held):
    """fdsdk's meson recipe is `ninja -v -j ${JOBS} -C _builddir` with `JOBS`
    emptied; a dangling `-j` left on a client ninja would kill the build."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real = bin_dir / "ninja"
    real.write_text(
        "#!/bin/sh\n"
        f'case "$1" in --version) echo {version}; exit 0 ;; --help) echo usage; exit 0 ;; esac\n'
        f'printf \'REAL:%s\\n\' "$*"\n')
    real.chmod(0o755)
    pool = tmp_path / "jobserver"
    os.mkfifo(pool)
    keep = os.open(pool, os.O_RDWR | os.O_NONBLOCK)
    os.write(keep, b"+++")
    ledger = tmp_path / "ledger"
    auth = f"fifo:{pool}" if style == "fifo" else f"{keep},{keep}"
    try:
        done = subprocess.run(
            ["sh", "-c", 'ninja -v -j ${JOBS} -C out'], pass_fds=(keep,),
            env={"PATH": f"{os.path.abspath(WRAPPERS)}:{bin_dir}:/usr/bin:/bin", "JOBS": "",
                 "MAKEFLAGS": f"-j4 --jobserver-auth={auth}",
                 "BST_TRACE_JOBSERVER_LEDGER": str(ledger), "BST_TRACE_WRAPPER_CAP": "3"},
            capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stderr
        assert done.stdout.strip() == expect
        acquired = [line for line in (ledger.read_text().splitlines() if ledger.exists() else [])
                    if '"acquire"' in line]
        assert [f'"tokens":{held}' in line for line in acquired] == ([True] if held else [])
        assert _unread(pool) == 3
    finally:
        os.close(keep)
