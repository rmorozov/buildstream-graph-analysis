"""UX-846: `lld` below LLVM 22, gold, mold and ninja 1.11 do not read
`MAKEFLAGS` - each sizes itself to every core under the jobserver mode
unless something holds tokens for it. Runs the real wrapper scripts
under `sh` against a real FIFO or pipe pair - never a proxy for the
kernel object - with a fake tool standing in for `ld.lld`/`ninja`.
"""
import array
import fcntl
import os
import pathlib
import shutil
import subprocess
import termios
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPERS = REPO / "tools/native_trace/wrappers"


@pytest.fixture(autouse=True)
def _generous_acquire_budget(monkeypatch):
    """UX-846: every case here asserts token *accounting*, not
    scheduling - `make test`'s own 4 xdist workers can starve `dd`'s
    non-blocking reads past a 50ms production budget on a loaded box.
    `monkeypatch.setenv` mutates the real `os.environ`, which every
    subprocess call below either spreads directly or copies from, so
    one fixture reaches every wrapper invocation in this file."""
    monkeypatch.setenv("BGA_WRAPPER_ACQUIRE_MS", "2000")


def _readable(fd):
    buf = array.array("i", [0])
    fcntl.ioctl(fd, termios.FIONREAD, buf, True)
    return buf[0]


def _fake_tool(bin_dir, name, marker, out, hang):
    """A tool that echoes the width it was given, then either sleeps
    briefly (a clean exit) or forever (until the test SIGKILLs it).

    `--help` is silent and exits 0 - "empty help", the shape the
    incident's own mutation procedure asks for. Every real (non-`--help`)
    invocation also prints to its own stdout, which a wrapper that never
    `exec`s into it (it runs the tool as a foreground child) leaves in
    the *parent* subprocess's captured stdout too - so a re-entered
    wrapper that ran this fake tool more than once is countable there,
    unlike the file `out`, which the last invocation would just overwrite.
    """
    tool = bin_dir / name
    tool.write_text(
        "#!/bin/sh\n"
        'case "$1" in --help) exit 0 ;; esac\n'
        'printf \'RAN:%s\\n\' "$*"\n'
        f'printf \'%s\\n\' "$*" > "{out}"\n'
        f': > "{marker}"\n'
        + ("while :; do sleep 1; done\n" if hang else "sleep 0.2\n")
    )
    tool.chmod(0o755)


def _run(tool, args, path_dir, env_extra, pass_fds=()):
    env = dict(os.environ)
    env["PATH"] = f"{path_dir}{os.pathsep}{env['PATH']}"
    env.update(env_extra)
    return subprocess.run(["sh", str(WRAPPERS / tool), *args], env=env,
                          pass_fds=pass_fds, capture_output=True, text=True)


def _fifo(tmp_path, tokens=4):
    path = str(tmp_path / "jobserver")
    os.mkfifo(path)
    fd = os.open(path, os.O_RDWR)
    os.write(fd, b"+" * tokens)
    os.set_inheritable(fd, True)
    return path, fd


class TestAHeldToolReturnsItsTokens:
    """The Acceptance Test: a pool of 4, capped at 3 - 3 held during the
    run, 4 readable again after, for a clean exit and a killed fake."""

    def test_clean_exit_holds_three_and_returns_all_four(self, tmp_path):
        path, fd = _fifo(tmp_path)
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(tmp_path, "ld.lld", marker, out, hang=False)
        env = {"MAKEFLAGS": f"--jobserver-auth={fd},{fd}",
              "BST_TRACE_WRAPPER_CAP": "3"}
        proc = subprocess.Popen(
            ["sh", str(WRAPPERS / "ld.lld")],
            env={**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}", **env},
            pass_fds=(fd,), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(0.02)
        else:
            proc.kill()
            pytest.fail("the fake tool never started")

        assert _readable(fd) == 1, "3 of 4 tokens should be held mid-run"

        stdout, stderr = proc.communicate(timeout=10)
        assert proc.returncode == 0, stderr
        assert "--threads=4" in out.read_text(), "3 held + 1 implicit = 4"
        assert _readable(fd) == 4, "all 4 readable again once the trap ran"
        os.close(fd)

    def test_a_killed_fake_still_returns_its_tokens(self, tmp_path):
        """UX-846's documented gap: a SIGKILLed *wrapper* cannot run its
        own trap (UX-852's audit). Killing the *child* tool instead - the
        pattern this wrapper is built on, running the real tool as a
        foreground child rather than exec'ing into it - leaves the
        wrapper alive to give the tokens back anyway."""
        path, fd = _fifo(tmp_path)
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(tmp_path, "ld.lld", marker, out, hang=True)
        env = {"MAKEFLAGS": f"--jobserver-auth={fd},{fd}",
              "BST_TRACE_WRAPPER_CAP": "3"}
        proc = subprocess.Popen(
            ["sh", str(WRAPPERS / "ld.lld")],
            env={**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}", **env},
            pass_fds=(fd,), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(0.02)
        else:
            proc.kill()
            pytest.fail("the fake tool never started")

        assert _readable(fd) == 1

        killed = False
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                cmdline = open(f"/proc/{entry}/cmdline", "rb").read()
            except OSError:
                continue
            if str(tmp_path).encode() + b"/ld.lld" in cmdline and b"sh" in cmdline:
                os.kill(int(entry), 9)
                killed = True
        assert killed, "could not find the fake tool's own pid to kill"

        proc.communicate(timeout=10)
        assert _readable(fd) == 4, "the wrapper (parent) survives and returns the tokens"
        os.close(fd)


class TestNoAuthRunsTheToolUntouched:
    def test_no_jobserver_auth_in_makeflags_leaves_argv_alone(self, tmp_path):
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(tmp_path, "ld.lld", marker, out, hang=False)
        result = _run("ld.lld", ["-o", "a.out", "x.o"], tmp_path,
                      {"MAKEFLAGS": "-j8"})
        assert result.returncode == 0
        assert out.read_text().strip() == "-o a.out x.o"


class TestFifoStyleAuth:
    def test_fifo_colon_path_is_opened_by_the_wrapper_itself(self, tmp_path):
        fifo_path = str(tmp_path / "make44fifo")
        os.mkfifo(fifo_path)
        host_fd = os.open(fifo_path, os.O_RDWR)
        os.write(host_fd, b"++")  # 2 tokens
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(tmp_path, "ld.lld", marker, out, hang=False)
        result = _run("ld.lld", [], tmp_path,
                      {"MAKEFLAGS": f"--jobserver-auth=fifo:{fifo_path}",
                       "BST_TRACE_WRAPPER_CAP": "8"})
        assert result.returncode == 0
        assert "--threads=3" in out.read_text()  # 2 held + 1 implicit
        assert _readable(host_fd) == 2
        os.close(host_fd)


class TestFdStyleAuthWithDistinctReadAndWriteEnds:
    """A real `os.pipe()` pair, read end != write end - the shape GNU
    make itself hands out, unlike this project's own single dup'd fd."""

    def test_a_pipe_pair_is_read_from_r_and_released_to_w(self, tmp_path):
        r, w = os.pipe()
        os.write(w, b"+++")  # 3 tokens
        os.set_inheritable(r, True)
        os.set_inheritable(w, True)
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(tmp_path, "ld.lld", marker, out, hang=False)
        env = dict(os.environ)
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
        env["MAKEFLAGS"] = f"--jobserver-auth={r},{w}"
        env["BST_TRACE_WRAPPER_CAP"] = "8"
        result = subprocess.run(["sh", str(WRAPPERS / "ld.lld")], env=env,
                                pass_fds=(r, w), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert "--threads=4" in out.read_text()  # 3 held + 1 implicit
        assert _readable(r) == 3, "all 3 returned to the read end"
        os.close(r)
        os.close(w)


class TestNothingReadableFallsBackToOne:
    def test_an_empty_pool_runs_with_the_implicit_token_alone(self, tmp_path):
        r, w = os.pipe()
        os.set_inheritable(r, True)
        os.set_inheritable(w, True)
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(tmp_path, "ld.lld", marker, out, hang=False)
        env = dict(os.environ)
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
        env["MAKEFLAGS"] = f"--jobserver-auth={r},{w}"
        env["BST_TRACE_WRAPPER_CAP"] = "8"
        result = subprocess.run(["sh", str(WRAPPERS / "ld.lld")], env=env,
                                pass_fds=(r, w), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert "--threads=1" in out.read_text()
        os.close(r)
        os.close(w)


class TestTheNinjaWrapperUsesDashJ:
    def test_ninja_gets_dash_j_not_threads(self, tmp_path):
        r, w = os.pipe()
        os.write(w, b"++")  # 2 tokens
        os.set_inheritable(r, True)
        os.set_inheritable(w, True)
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(tmp_path, "ninja", marker, out, hang=False)
        env = dict(os.environ)
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
        env["MAKEFLAGS"] = f"--jobserver-auth={r},{w}"
        env["BST_TRACE_WRAPPER_CAP"] = "8"
        result = subprocess.run(["sh", str(WRAPPERS / "ninja")], env=env,
                                pass_fds=(r, w), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        text = out.read_text()
        assert "-j 3" in text  # 2 held + 1 implicit
        assert "--threads" not in text
        os.close(r)
        os.close(w)


class TestTheLedgerRowsShareTheFileWithThePoolController:
    """UX-846: a wrapper's acquire/release rows and `PoolController`'s
    own ticks land in the same `jobserver_ledger.jsonl` - a reader must
    not choke on the shape it does not recognise."""

    def test_summarize_jobserver_ledger_skips_wrapper_rows(self, tmp_path):
        from tools import bst_native_build_tracer as tracer

        ledger = tmp_path / "jobserver_ledger.jsonl"
        ledger.write_text(
            '{"event":"acquire","tool":"ld.lld","pid":1,"tokens":3,"t":1.0}\n'
            '{"t_us":1,"busy_cores":1.0,"psi_some10":null,"pool":2,'
            '"action":"withdraw","reason":"x"}\n'
            '{"event":"release","tool":"ld.lld","pid":1,"tokens":3,"t":1.1}\n'
        )
        moves, pool_min, pool_max = tracer.summarize_jobserver_ledger(str(ledger), 4)
        assert moves == 1
        assert pool_min == 2
        assert pool_max == 2


class TestASymlinkedInvocationFindsTheRealToolNotItself:
    """UX-846, post-merge incident: `$0`'s directory is the *invoked*
    path's directory - a symlink into `wrappers/`, reached from another
    directory, made `bga_self_dir` wrong. `bga_find_real`'s old
    self-directory-only skip then walked straight past the check and
    found the wrapper itself, genuinely present on `PATH` ahead of the
    real tool; `"$real" --help` re-entered it without bound (32,000
    processes, a container restart). This reproduces the exact shape:
    the wrapper directory first on `PATH`, a symlink to the wrapper
    elsewhere, a fake real tool further down."""

    def test_a_symlinked_invocation_runs_the_real_tool_once(self, tmp_path):
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        symlink = other_dir / "ld.lld"
        symlink.symlink_to(WRAPPERS / "ld.lld")

        fake_dir = tmp_path / "fake"
        fake_dir.mkdir()
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(fake_dir, "ld.lld", marker, out, hang=False)

        r, w = os.pipe()
        os.write(w, b"++")
        os.set_inheritable(r, True)
        os.set_inheritable(w, True)
        env = dict(os.environ)
        # The wrapper directory genuinely first on PATH - the shape
        # that made the old self-dir-only skip miss it entirely.
        env["PATH"] = (f"{WRAPPERS}{os.pathsep}{other_dir}{os.pathsep}"
                       f"{fake_dir}{os.pathsep}{env['PATH']}")
        env["MAKEFLAGS"] = f"--jobserver-auth={r},{w}"
        env["BST_TRACE_WRAPPER_CAP"] = "8"

        result = subprocess.run(["sh", str(symlink)], env=env, pass_fds=(r, w),
                                capture_output=True, text=True, timeout=5)
        os.close(r)
        os.close(w)
        assert result.returncode == 0, (result.stdout, result.stderr)
        # Exactly once: a re-entered wrapper ran the fake tool (or tried
        # to run itself, which prints nothing matching "RAN:") more than
        # zero and more than one times before either fork-bombing or the
        # BGA_WRAPPER_TOOL guard cutting it off.
        assert result.stdout.count("RAN:") == 1, (result.stdout, result.stderr)


class TestNoRealToolAnywhereRefusesFastWithNoTokensTouched:
    """UX-846: `bga_find_real` failing outright (nothing but wrapper
    copies of `ld.lld` on `PATH`) must refuse before any token is
    touched - it fails ahead of the auth parsing and the acquire."""

    def test_exits_127_within_2s_and_holds_nothing(self, tmp_path):
        # `bga_find_real`'s own machinery (`dirname`, `basename`, `head`,
        # `grep`, `readlink`) is external, not a `dash` builtin - a truly
        # empty `PATH` breaks the wrapper itself before it can even
        # answer "no real tool", which would test the wrong failure.
        minimal_bin = tmp_path / "minimal_bin"
        minimal_bin.mkdir()
        for util in ("dirname", "basename", "head", "grep", "readlink"):
            found = shutil.which(util)
            assert found, f"this box has no {util} to build the fixture from"
            (minimal_bin / util).symlink_to(found)
        path, fd = _fifo(tmp_path, tokens=4)
        env = dict(os.environ)
        env["PATH"] = str(minimal_bin)  # nothing named ld.lld anywhere
        env["MAKEFLAGS"] = f"--jobserver-auth={fd},{fd}"
        env["BST_TRACE_WRAPPER_CAP"] = "8"

        # An absolute `sh`, not a bare name resolved through `env["PATH"]`
        # - that PATH is deliberately empty of everything, `sh` included.
        result = subprocess.run(["/bin/sh", str(WRAPPERS / "ld.lld")], env=env,
                                pass_fds=(fd,), capture_output=True, text=True,
                                timeout=2)
        assert result.returncode == 127, (result.stdout, result.stderr)
        assert "no real tool found" in result.stderr
        assert _readable(fd) == 4, "bga_find_real fails before any read"
        os.close(fd)


class TestTheReentryGuardRefusesInIsolation:
    """The `BGA_WRAPPER_TOOL` guard, exercised on its own - independent
    of whatever `bga_find_real`'s identity/content checks conclude, so
    mutating *this* check has a test that discriminates on its own
    rather than relying on the symlink case also depending on it."""

    def test_already_marked_refuses_before_running_anything(self, tmp_path):
        fake_dir = tmp_path / "fake"
        fake_dir.mkdir()
        out, marker = tmp_path / "out", tmp_path / "marker"
        _fake_tool(fake_dir, "ld.lld", marker, out, hang=False)
        env = dict(os.environ)
        env["PATH"] = f"{fake_dir}{os.pathsep}{env['PATH']}"
        # Already "inside" a wrapper invocation for this same tool.
        env["BGA_WRAPPER_TOOL"] = "ld.lld"

        result = subprocess.run(["sh", str(WRAPPERS / "ld.lld")], env=env,
                                capture_output=True, text=True, timeout=2)
        assert result.returncode == 127, (result.stdout, result.stderr)
        assert "re-entered itself" in result.stderr
        assert not marker.exists(), "the fake tool must never have run"
