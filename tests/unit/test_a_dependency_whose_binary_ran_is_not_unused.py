"""UX-1360: a dependency whose binary the element ran is read, and one it may have only probed is not judged.

holds: the real hook records the binary a process runs, so an element that only executes a dependency's tool
reads that dependency; a dependency staging executables nobody opened or ran is skipped, never a candidate,
because the hook records no `stat`/`access` probe - and a library-only one still is.
"""

import os
import shutil
import subprocess

import pytest

from bga.correlate import _plane2_view
from tools.bst_native_build_tracer import _HOOK_C, compute_declared_vs_used, parse_open_records

ELEMENT = "gcc-stage1.bst"
DEP = "binutils-stage1.bst"
CC = shutil.which("cc") or shutil.which("gcc")


def _filler(root):
    return {f"{root}/share/doc/binutils/{i}.txt" for i in range(10)}


@pytest.mark.skipif(CC is None, reason="no C compiler on PATH")
def test_running_a_dependencys_binary_reads_it(tmp_path):
    hook_so = tmp_path / "hook.so"
    subprocess.run(
        [CC, "-shared", "-fPIC", "-O2", "-o", str(hook_so), _HOOK_C, "-ldl"], check=True, capture_output=True
    )
    tool = tmp_path / "cross" / "bin" / "cat"
    tool.parent.mkdir(parents=True)
    shutil.copy(shutil.which("cat"), tool)
    source = tmp_path / "src" / "input.c"
    source.parent.mkdir()
    source.write_text("int main(void) { return 0; }\n")
    trace = tmp_path / "trace.log"
    env = {**os.environ, "LD_PRELOAD": str(hook_so), "BST_TRACE_LOG": str(trace), "BST_TRACE_OPENS": "1"}
    subprocess.run([str(tool), str(source)], env={**env, "BST_TRACE_ELEMENT": ELEMENT}, check=True, capture_output=True)

    opens = parse_open_records(trace.read_text(errors="replace"))
    staged = {os.path.realpath(tool)} | _filler(tmp_path)
    result = compute_declared_vs_used(opens, {ELEMENT: [DEP]}, {DEP: staged})
    assert [(r["element"], r["dependency"]) for r in result["used"]] == [(ELEMENT, DEP)], result
    assert result["unused_candidates"] == []
    assert not _plane2_view({"declared_vs_used": result})[ELEMENT].get("unused_dependencies")


def test_an_executable_nobody_opened_or_ran_is_not_judged():
    opens = {ELEMENT: {"paths": {"/src/input.c"}, "dropped": 0}}
    staged = {"/cross/x86_64-unknown-linux-gnu/bin/ld", "/cross/x86_64-unknown-linux-gnu/bin/as"} | _filler("/cross")
    result = compute_declared_vs_used(opens, {ELEMENT: [DEP, "zlib.bst"]}, {DEP: staged, "zlib.bst": _filler("/usr")})
    assert [r["dependency"] for r in result["unused_candidates"]] == ["zlib.bst"], result
    (skipped,) = result["skipped"]
    assert skipped["dependency"] == DEP and "2 executable" in skipped["reason"], skipped
