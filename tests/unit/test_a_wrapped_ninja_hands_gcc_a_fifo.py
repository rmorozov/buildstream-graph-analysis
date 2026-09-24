"""UX-1006: behind the token-holding wrapper, ninja passes MAKEFLAGS to
gcc untouched, and gcc's lto1 deadlocks on a raw blocking fd pair - so an
old ninja's element gets a `fifo:` path, which lto1 opens non-blocking."""
import os

from tests.unit.test_a_compiler_lto_shim_fills_the_box import BIND_DST, _bst_args, _makeflags_value
from tests.unit.test_a_ninja_client_is_read_by_version import _ninja_body
from tests.unit.test_bwrap_shim import _fake_bwrap_with_make
from tools.native_trace.bwrap_shim import build_shim_argv, probe_ninja


def _argv(tmp_path, monkeypatch, make_version):
    fake = _fake_bwrap_with_make(tmp_path / "bwrap", tmp_path / "marker", BIND_DST, make_version)
    head, rest = open(fake, encoding="utf-8").read().split("\n", 1)
    with open(fake, "w", encoding="utf-8") as handle:
        handle.write(head + "\n" + _ninja_body("1.11.1") + rest)
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src)
    monkeypatch.setenv("BST_TRACE_JOBSERVER", os.path.join(bind_src, "jobserver"))
    wrappers = tmp_path / "wrappers"
    wrappers.mkdir()
    read_fd, write_fd = os.pipe()
    try:
        return build_shim_argv(
            real_bwrap=fake, bst_args=_bst_args("git-minimal"), bind_src=bind_src,
            bind_dst=BIND_DST, preload_so=f"{BIND_DST}/hook.so",
            trace_log=f"{BIND_DST}/trace.log", jobserver_fd=read_fd, element_kind="meson",
            ninja_probe=probe_ninja(fake, [], None), wrapper_dir=str(wrappers))
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_an_old_ninja_behind_the_wrapper_gets_a_fifo(tmp_path, monkeypatch):
    argv = _argv(tmp_path, monkeypatch, "4.4.1")
    assert _makeflags_value(argv) == f"--jobserver-auth=fifo:{BIND_DST}/jobserver"


def test_under_an_old_make_the_auth_and_jobs_are_both_dropped(tmp_path, monkeypatch):
    argv = _argv(tmp_path, monkeypatch, "4.3")
    assert "MAKEFLAGS" not in argv
    assert argv[argv.index("JOBS") + 1] == "-j4"
