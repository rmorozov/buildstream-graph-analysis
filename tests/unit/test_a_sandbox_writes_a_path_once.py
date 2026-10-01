"""UX-1241: a path the processes of one sandbox all open is written once,
and the element's read set is the one every process writing it gives."""

import os
import re
import shutil
import subprocess

import pytest

from tools.bst_native_build_tracer import _HOOK_C, parse_open_lines
from tools.native_trace.bwrap_shim import build_shim_argv

pytestmark = pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("gcc") is None,
    reason="no C compiler on PATH",
)

COMMON, PROCESSES = 30, 12


def _build_hook(where, *defines):
    cc = shutil.which("cc") or shutil.which("gcc")
    hook_so = where / "hook.so"
    subprocess.run(
        [cc, "-shared", "-fPIC", "-O2", "-Wall", "-Wextra", *defines, "-o", str(hook_so), _HOOK_C, "-ldl"],
        check=True,
        capture_output=True,
        text=True,
    )
    return hook_so


@pytest.fixture(scope="module")
def hook_so(tmp_path_factory):
    return _build_hook(tmp_path_factory.mktemp("hook"))


def _build(tmp_path, hook_so, seen, tag):
    """`PROCESSES` cats, each reading the same `COMMON` files and one of its
    own, then one reading only the common ones."""
    files = tmp_path / "files"
    if not files.exists():
        files.mkdir()
        for i in range(COMMON):
            (files / f"common-{i:02d}.h").write_text("x")
        for k in range(PROCESSES):
            (files / f"own-{k:02d}.c").write_text("x")
    common = " ".join(str(files / f"common-{i:02d}.h") for i in range(COMMON))
    script = "; ".join(f"cat {common} {files}/own-{k:02d}.c >/dev/null" for k in range(PROCESSES)) + f"; cat {common}"
    log = tmp_path / f"{tag}.log"
    env = {**os.environ, "LD_PRELOAD": str(hook_so), "BST_TRACE_LOG": str(log)}
    env |= {"BST_TRACE_OPENS": "1", "BST_TRACE_ELEMENT": "probe.bst", "BST_TRACE_INVOCATION": "7"}
    env.pop("BST_TRACE_OPENS_SEEN", None)
    if seen is not None:
        env["BST_TRACE_OPENS_SEEN"] = str(seen)
    subprocess.run(["/bin/sh", "-c", script], env=env, check=True, capture_output=True)
    text = log.read_text()
    probe = [line for line in text.splitlines() if line.startswith(str(files))]
    return text, probe, parse_open_lines(text.splitlines(keepends=True))["probe.bst"]


def test_a_common_path_is_written_once_and_the_read_set_is_unchanged(tmp_path, hook_so):
    _, every, full = _build(tmp_path, hook_so, None, "full")
    _, once, deduped = _build(tmp_path, hook_so, tmp_path / "seen-7", "deduped")
    assert len(every) == PROCESSES * (COMMON + 1) + COMMON
    assert sorted(once) == sorted(set(every)) and len(once) == COMMON + PROCESSES
    assert set(deduped["paths"]) == set(full["paths"])


def test_a_process_with_nothing_new_still_writes_its_header(tmp_path, hook_so):
    full_text, _, full = _build(tmp_path, hook_so, None, "full")
    text, _, deduped = _build(tmp_path, hook_so, tmp_path / "seen-7", "deduped")
    assert deduped["processes"] == full["processes"] > PROCESSES
    assert re.search(r"^OPENS .* unique=0 ", text, re.M)


def test_a_crowded_table_writes_the_path_rather_than_losing_it(tmp_path):
    """16 slots fill on the first process; the rest must fall back to writing."""
    hook_so = _build_hook(tmp_path, "-DSEEN_SLOTS=16")
    _, every, full = _build(tmp_path, hook_so, None, "full")
    _, crowded, deduped = _build(tmp_path, hook_so, tmp_path / "seen-7", "crowded")
    assert set(crowded) == set(every)
    assert set(deduped["paths"]) == set(full["paths"])


def test_a_table_that_cannot_open_writes_every_path(tmp_path, hook_so):
    _, every, _ = _build(tmp_path, hook_so, None, "full")
    _, unopened, _ = _build(tmp_path, hook_so, tmp_path / "no-such-dir" / "seen-7", "unopened")
    assert sorted(unopened) == sorted(every)


def _setenv(argv, name):
    return next((argv[i + 2] for i, a in enumerate(argv) if a == "--setenv" and argv[i + 1] == name), None)


def test_the_shim_names_one_table_per_sandbox_in_the_bind_dir(monkeypatch):
    def argv(invocation_id):
        return build_shim_argv(
            "/usr/bin/bwrap", ["--dir", "/buildstream/p/a.bst", "sh"], "/host/bind", "/tmp/.t", "/tmp/.t/h.so",
            "/tmp/.t/trace.log", invocation_id=invocation_id,
        )  # fmt: skip

    monkeypatch.setenv("BST_TRACE_OPENS", "1")
    assert _setenv(argv(4), "BST_TRACE_OPENS_SEEN") == "/tmp/.t/opens-seen-4"
    assert _setenv(argv(5), "BST_TRACE_OPENS_SEEN") == "/tmp/.t/opens-seen-5"
    assert _setenv(argv(None), "BST_TRACE_OPENS_SEEN") is None
    monkeypatch.delenv("BST_TRACE_OPENS")
    assert _setenv(argv(4), "BST_TRACE_OPENS_SEEN") is None
