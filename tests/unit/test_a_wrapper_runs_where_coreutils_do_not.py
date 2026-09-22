"""UX-918: a wrapper has to run on the sandbox it is mounted into.

`examples/stage_cpp_toolchain.sh` stages eighteen binaries and no
coreutils, and `_common.sh` opened on `dirname`/`basename` at source
time under `set -eu` - so the `flto/` shims, which shadow the staged
`cc`/`gcc`/`g++`/`c++`, failed every compile before any wrapper logic
ran (`bst-examples` exit 255, run 35610762079).

The `PATH` here is built from `stage_cpp_toolchain.sh`'s own `BINARIES`
list rather than a copy of it, so widening what the examples stage
relaxes this guard by itself and cannot drift from it.
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPERS = REPO / "tools/native_trace/wrappers"
STAGER = REPO / "examples/stage_cpp_toolchain.sh"

HELD_TOOLS = ("ninja", "ld.gold", "ld.lld", "lld", "mold")
FLTO_TOOLS = ("flto/cc", "flto/gcc", "flto/g++", "flto/c++")


def _staged_names():
    """The basenames `stage_cpp_toolchain.sh` puts in the sandbox, read
    from both of its axis arrays (`UX-914` split the one list in two; a
    regex that still matched only the composed `BINARIES=(...)` would
    read a set of zero paths and pass whatever the wrappers do)."""
    text = STAGER.read_text()
    names = set()
    for array in ("RUNTIME_BINARIES", "TOOLCHAIN_BINARIES"):
        block = re.search(rf"^{array}=\((.*?)^\)", text, re.DOTALL | re.MULTILINE)
        assert block, f"stage_cpp_toolchain.sh no longer declares {array}=(...)"
        names |= {pathlib.PurePosixPath(word).name
                  for word in block.group(1).split() if word.startswith("/")}
    assert names, "no absolute paths read out of the stager's axis arrays"
    return names


def _sandbox_path(tmp_path, tool_name):
    """A bin directory holding only what the stager stages, plus a fake
    tool standing in for the one the wrapper will exec into."""
    staged = _staged_names()
    assert "dirname" not in staged and "basename" not in staged, \
        "the stager now stages coreutils - this guard has nothing to prove"
    bin_dir = tmp_path / "staged-bin"
    bin_dir.mkdir()
    for name in sorted(staged):
        found = shutil.which(name)
        if found:
            (bin_dir / name).symlink_to(found)
    real = bin_dir / tool_name
    if real.exists():
        real.unlink()
    real.write_text("#!/bin/sh\nprintf 'REAL:%s\\n' \"$*\"\nexit 0\n")
    real.chmod(0o755)
    return bin_dir


def _run(wrapper, args, bin_dir, env_extra=None):
    """The wrapper, with `PATH` replaced rather than prepended - the
    whole point is that nothing outside the staged set is reachable."""
    env = {"PATH": str(bin_dir), "HOME": str(bin_dir)}
    env.update(env_extra or {})
    return subprocess.run(["sh", str(WRAPPERS / wrapper), *args],
                          env=env, capture_output=True, text=True)


@pytest.mark.parametrize("wrapper", HELD_TOOLS + FLTO_TOOLS)
def test_every_wrapper_execs_its_tool_with_no_coreutils_on_path(
        wrapper, tmp_path):
    """The defect itself: source-time `dirname` killed the wrapper
    before it could find, let alone run, the real tool."""
    tool = wrapper.rsplit("/", 1)[-1]
    bin_dir = _sandbox_path(tmp_path, tool)

    done = _run(wrapper, ["-c", "a.c"], bin_dir)

    assert done.returncode == 0, done.stderr
    assert "REAL:-c a.c" in done.stdout


def test_the_flto_shim_pins_the_cap_with_no_coreutils_on_path(tmp_path):
    """Past the exec: the shim's own transform runs on the same bare
    sandbox, so `-flto` is pinned and the auth stripped there too."""
    bin_dir = _sandbox_path(tmp_path, "cc")

    done = _run("flto/cc", ["-flto", "x.c"], bin_dir, {
        "BST_TRACE_FLTO_ACTIVE": "1",
        "BST_TRACE_LTO_CAP": "3",
        "MAKEFLAGS": "--jobserver-auth=7,8 -j4",
    })

    assert done.returncode == 0, done.stderr
    assert "REAL:-flto=3 x.c" in done.stdout


def test_the_recursion_marker_is_still_read_with_no_grep(tmp_path):
    """UX-846's guard is the one that cost a container restart, and a
    `head | grep` that dies 127 reads as "no marker" - which is the
    disarmed state. So the scan has to survive the bare sandbox too."""
    bin_dir = _sandbox_path(tmp_path, "cc")
    decoy_dir = bin_dir.parent / "decoy"
    decoy_dir.mkdir()
    decoy = decoy_dir / "cc"
    decoy.write_text("#!/bin/sh\n# UX-846 marker\nprintf 'DECOY\\n'\nexit 0\n")
    decoy.chmod(0o755)

    done = _run("flto/cc", ["-c", "a.c"], bin_dir,
                {"PATH": f"{decoy_dir}{os.pathsep}{bin_dir}"})

    assert done.returncode == 0, done.stderr
    assert "DECOY" not in done.stdout
    assert "REAL:-c a.c" in done.stdout
