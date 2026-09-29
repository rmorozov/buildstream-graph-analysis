"""UX-1116: the hook and the spine build with no warnings, and the hook
runs a forking, exec'ing, file-opening process tree under ASan/UBSan."""

import os
import re
import shutil
import subprocess
import textwrap

import pytest

from tools.bst_native_build_tracer import _HOOK_C, _SPINE_C

CC = shutil.which("cc") or shutil.which("gcc")

pytestmark = pytest.mark.skipif(CC is None, reason="no C compiler on PATH")


def _libasan():
    out = subprocess.run([CC, "-print-file-name=libasan.so"], capture_output=True, text=True).stdout.strip()
    return out if os.sep in out else None


@pytest.mark.parametrize("source", [_HOOK_C, _SPINE_C], ids=["hook", "spine"])
def test_the_source_compiles_without_a_warning(source):
    result = subprocess.run(
        [CC, "-Wall", "-Wextra", "-Werror", "-O2", "-c", "-o", "/dev/null", source], capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr


def test_the_hook_runs_a_process_tree_under_asan_and_ubsan(tmp_path):
    libasan = _libasan()
    if libasan is None:
        pytest.skip("no sanitizer runtime (libasan) for the C compiler")
    hook_so = tmp_path / "hook.so"
    subprocess.run(
        [
            CC,
            "-shared",
            "-fPIC",
            "-O1",
            "-g",
            "-fno-omit-frame-pointer",
            "-fsanitize=address,undefined",
            "-DOPEN_SLOTS=16",
            "-DOPEN_ARENA_BYTES=256",
            "-o",
            str(hook_so),
            _HOOK_C,
            "-ldl",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    files = tmp_path / "files"
    files.mkdir()
    for i in range(60):
        (files / f"a-rather-long-file-name-so-the-arena-fills-{i:04d}.txt").write_text("x")
    script = tmp_path / "opener.py"
    script.write_text(
        textwrap.dedent(f"""
        import glob
        for p in sorted(glob.glob({str(files)!r} + "/*.txt")):
            open(p).close()
    """)
    )
    trace_log = tmp_path / "trace.log"
    env = dict(os.environ)
    env.update(
        {
            "LD_PRELOAD": f"{libasan}:{hook_so}",
            "BST_TRACE_LOG": str(trace_log),
            "BST_TRACE_OPENS": "1",
            "BST_TRACE_ELEMENT": "probe.bst",
            "ASAN_OPTIONS": "detect_leaks=0:exitcode=86",
            "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1",
        }
    )
    stderr = ""
    for cmd in (["python3", str(script)], ["sh", "-c", "cat /etc/hostname; ls /"]):
        run = subprocess.run(cmd, env=env, capture_output=True, text=True)
        stderr += run.stderr
        assert run.returncode == 0, run.stderr

    assert "Sanitizer" not in stderr, stderr
    pids = set(re.findall(r"^START pid=(\d+)", trace_log.read_text(errors="replace"), re.M))
    assert len(pids) > 1, pids
