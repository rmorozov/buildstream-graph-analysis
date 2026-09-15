"""UX-841: `UX-679`'s Outcome named the gap outright - the tracer's FIFO
lifecycle (`open_jobserver`/`close_jobserver`) had no guard, and the
verifier's own mutation passed the suite. This reads the lifecycle
directly (token count, removal, a build that raises) and the auth-style
choice `bwrap_shim.build_shim_argv` acts on.
"""
import os

import pytest

from tools import bst_native_build_tracer as tracer
from tools.native_trace.bwrap_shim import build_shim_argv


class TestOpenJobserverSeedsExactlyNMinusOneTokens:
    def test_a_pool_of_4_holds_three_readable_tokens_and_removes_on_close(self, tmp_path):
        path, fd, tokens = tracer.open_jobserver(4, str(tmp_path))
        assert tokens == 3
        assert os.read(fd, 4) == b"+++"

        tracer.close_jobserver(path, fd)

        assert not os.path.exists(path)

    def test_a_pool_of_1_writes_zero_tokens(self, tmp_path):
        """An empty pool: only the implicit token every client already
        holds - the FIFO exists, but nothing is readable from it."""
        path, fd, tokens = tracer.open_jobserver(1, str(tmp_path))
        assert tokens == 0
        os.set_blocking(fd, False)
        with pytest.raises(BlockingIOError):
            os.read(fd, 1)

        tracer.close_jobserver(path, fd)


class TestJobserverAuthStyleFollowsMake:
    """UX-841: `auto` reads the host's `make --version` - the version
    string is passed in here, never shelled out to, per the falsify
    skill's "instrument that reads a proxy" caution."""

    def test_gnu_make_4_4_picks_fifo(self):
        assert tracer.jobserver_auth_style(
            "auto", "GNU Make 4.4\nBuilt for x86_64-pc-linux-gnu\n"
        ) == "fifo"

    def test_gnu_make_4_3_picks_fd(self):
        assert tracer.jobserver_auth_style(
            "auto", "GNU Make 4.3\nBuilt for x86_64-pc-linux-gnu\n"
        ) == "fd"

    def test_an_explicit_style_is_never_overridden(self):
        assert tracer.jobserver_auth_style("fd", "GNU Make 4.4\n") == "fd"
        assert tracer.jobserver_auth_style("fifo", "GNU Make 4.3\n") == "fifo"


class TestTheShimsArgvCarriesTheChosenStyle:
    def test_a_4_4_version_string_carries_fifo_under_bind_dst_and_no_bind_of_its_own(self):
        """UX-869: `open_jobserver` makes the FIFO under `bind_src`
        (`scratch`), which is already bound whole at `bind_dst` - a
        second `--bind` of the FIFO onto its own host path failed on a
        read-only sandbox root whenever the project was not under
        `/tmp`."""
        bind_src = "/tmp/host-trace-dir"
        fifo_path = bind_src + "/jobserver"
        style = tracer.jobserver_auth_style("auto", "GNU Make 4.4\n")
        assert style == "fifo"

        argv = build_shim_argv(
            real_bwrap="/usr/bin/bwrap",
            bst_args=["--unshare-pid", "sh", "-c", "true"],
            bind_src=bind_src,
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            jobserver_fifo=fifo_path,
            element_kind="make",  # UX-843: the table needs a kind now
        )

        binds = [i for i, tok in enumerate(argv) if tok == "--bind"]
        assert len(binds) == 1, "only the general trace bind - none for the FIFO"
        assert fifo_path not in argv
        setenv = argv.index("MAKEFLAGS")
        assert argv[setenv + 1] == "--jobserver-auth=fifo:/tmp/.bst-native-trace/jobserver"

    def test_a_4_3_version_string_carries_fd_fd(self):
        style = tracer.jobserver_auth_style("auto", "GNU Make 4.3\n")
        assert style == "fd"

        read_fd, write_fd = os.pipe()
        try:
            argv = build_shim_argv(
                real_bwrap="/usr/bin/bwrap",
                bst_args=["--unshare-pid", "sh", "-c", "true"],
                bind_src="/tmp/host-trace-dir",
                bind_dst="/tmp/.bst-native-trace",
                preload_so="/tmp/.bst-native-trace/hook.so",
                trace_log="/tmp/.bst-native-trace/trace.log",
                jobserver_fd=read_fd,
                element_kind="make",  # UX-843: the table needs a kind now
            )
            setenv = argv.index("MAKEFLAGS")
            assert argv[setenv + 1] == f"--jobserver-auth={read_fd},{read_fd}"
            assert "--bind" not in argv[argv.index("MAKEFLAGS"):]
        finally:
            os.close(read_fd)
            os.close(write_fd)


class TestTheFifoLifecycleSurvivesAFailedBuild:
    def test_a_build_that_raises_inside_the_try_still_removes_the_fifo(
            self, tmp_path, monkeypatch):
        project = tmp_path / "proj"
        project.mkdir()
        raw_log = tmp_path / "trace.log"
        monkeypatch.setattr(tracer, "compile_hook", lambda d: None)
        monkeypatch.setattr(tracer, "install_bwrap_shim", lambda d: "/usr/bin/bwrap")
        monkeypatch.setattr(tracer, "write_bwrap_shim", lambda d: os.path.join(d, "bwrap"))
        monkeypatch.setattr(tracer, "probe_bwrap_shim", lambda p: None)

        seen = {}

        def fake_run(cmd, cwd=None, env=None, **kwargs):
            seen["path"] = env["BST_TRACE_JOBSERVER"]
            assert os.path.exists(seen["path"])
            raise RuntimeError("the build blew up")

        monkeypatch.setattr(tracer.subprocess, "Popen", fake_run)

        with pytest.raises(RuntimeError):
            tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                                    str(raw_log), jobserver=4)

        assert "path" in seen, "fake_run never ran - the fixture is wrong"
        assert not os.path.exists(seen["path"])
