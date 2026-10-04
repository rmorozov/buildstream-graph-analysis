"""UX-1315: the ninja wrapper refuses a recursion, not a nested build.

A nested CMake configure under the real ninja probes `ninja --version`
through the wrapper again; only a wrapper that execs or forks itself
is a repeat.
"""

import os
import pathlib
import shutil
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPERS = REPO / "tools/native_trace/wrappers"
MSG = "wrapper re-entered itself"


def _fake_ninja(path, body):
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


def _env(tmp_path, *dirs):
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([*map(str, dirs), env["PATH"]])
    env.pop("MAKEFLAGS", None)
    return env


def test_a_nested_invocation_under_the_real_ninja_runs(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    child = tmp_path / "child.sh"
    child.write_text("#!/bin/sh\nninja --version\n")
    child.chmod(0o755)
    # ninja -> sh -> child -> wrapper: the owner's cmake probe.
    _fake_ninja(real / "ninja", f'case "$1" in --version) echo 1.11.1 ;; *) sh -c "{child}" ;; esac\n')
    r = subprocess.run(
        ["sh", str(WRAPPERS / "ninja"), "build"],
        env=_env(tmp_path, WRAPPERS, real),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert MSG not in r.stderr
    assert "1.11.1" in r.stdout


def test_a_rule_that_runs_ninja_directly_is_not_a_repeat(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    # The real ninja is exec'd (same PID as the wrapper) and its rule shell
    # execs the wrapper: PPID is the recorded PID, the fork marker is absent.
    _fake_ninja(real / "ninja", 'case "$1" in --version) echo 1.11.1 ;; *) sh -c "exec ninja --version" ;; esac\n')
    r = subprocess.run(
        ["sh", str(WRAPPERS / "ninja"), "build"],
        env=_env(tmp_path, WRAPPERS, real),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert MSG not in r.stderr


def _wrapper_copy(tmp_path):
    """A copy whose marker is past line 3, so `bga_find_real` picks it."""
    copy = tmp_path / "copy"
    copy.mkdir()
    shutil.copy(WRAPPERS / "_common.sh", copy / "_common.sh")
    lines = (WRAPPERS / "ninja").read_text().splitlines()
    (copy / "ninja").write_text("#!/bin/sh\n:\n:\n:\n" + "\n".join(lines[1:]) + "\n")
    (copy / "ninja").chmod(0o755)
    return copy


def test_a_wrapper_exec_ing_a_wrapper_copy_still_refuses(tmp_path):
    copy = _wrapper_copy(tmp_path)
    r = subprocess.run(
        ["sh", str(WRAPPERS / "ninja"), "--version"],
        env=_env(tmp_path, WRAPPERS, copy),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 127, (r.stdout, r.stderr)
    assert MSG in r.stderr


def test_a_wrapper_forking_a_wrapper_copy_still_refuses(tmp_path):
    copy = _wrapper_copy(tmp_path)
    fifo = tmp_path / "js"
    os.mkfifo(fifo)
    fd = os.open(fifo, os.O_RDWR)
    os.write(fd, b"++")
    env = _env(tmp_path, WRAPPERS, copy)
    env["MAKEFLAGS"] = f"--jobserver-auth=fifo:{fifo}"
    r = subprocess.run(["sh", str(WRAPPERS / "ninja"), "build"], env=env, capture_output=True, text=True, timeout=10)
    os.close(fd)
    assert r.returncode == 127, (r.stdout, r.stderr)
    assert MSG in r.stderr


def _pool(tmp_path):
    fifo = tmp_path / "js"
    os.mkfifo(fifo)
    fd = os.open(fifo, os.O_RDWR)
    os.write(fd, b"++")
    return fifo, fd


def test_a_nested_invocation_under_a_jobserver_runs(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    child = tmp_path / "child.sh"
    child.write_text("#!/bin/sh\nninja --version\n")
    child.chmod(0o755)
    # With an auth the real ninja is forked, not exec'd: the owner's `--jobserver auto` case.
    # The wrapper passes `-j N` ahead of the args, so the fake matches anywhere in argv.
    _fake_ninja(
        real / "ninja",
        f'case " $* " in *" --version "*) echo 1.11.1 ;; *" --help "*) : ;; *) sh -c "{child}" ;; esac\n',
    )
    fifo, fd = _pool(tmp_path)
    env = _env(tmp_path, WRAPPERS, real)
    env["MAKEFLAGS"] = f"--jobserver-auth=fifo:{fifo}"
    r = subprocess.run(["sh", str(WRAPPERS / "ninja"), "build"], env=env, capture_output=True, text=True, timeout=10)
    os.close(fd)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "1.11.1" in r.stdout


def test_a_recursion_through_an_intermediate_shell_is_bounded(tmp_path):
    copy = _wrapper_copy(tmp_path)
    tramp = tmp_path / "tramp"
    tramp.mkdir()
    # An unmarked "real" ninja that runs the copy through `sh -c`, no exec: neither marker matches.
    _fake_ninja(tramp / "ninja", f'sh -c \'"{copy}/ninja" "$@"; exit $?\' sh "$@"\n')
    r = subprocess.run(
        ["sh", str(WRAPPERS / "ninja"), "--version"],
        env=_env(tmp_path, WRAPPERS, tramp, copy),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r.returncode == 127, (r.stdout, r.stderr[-400:])
    assert "nested 16 deep" in r.stderr
