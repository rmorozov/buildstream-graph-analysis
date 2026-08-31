"""UX-57: the hook flushes a full path window instead of dropping paths.

A real `freedesktop-sdk` build recorded **65,101 paths and dropped
149,053** — a 70% loss. That is not a cosmetic gap: `UX-46` deliberately
refuses to call a dependency unused when the read set was truncated, so
every element heavy enough to fill the buffer was excluded from
declared-vs-used analysis entirely. The heavier the element, the more
certainly it went unanalyzed.

Compression was measured before it was rejected. Front-coding the arena
against the previous path — the only kind available to a hook that must
store paths as they arrive — buys **1.41×** on a real 3,658-path set
(2.88× if they could be sorted, which they cannot). That moves the
ceiling from ~6,000 paths to ~8,500, still under `OPEN_SLOTS`, in
exchange for a wire-format change and a decoder. Flushing removes the
ceiling outright for the cost of an occasional `write()`.

These tests compile the real `hook.c` with a deliberately tiny window, so
the flush path runs for real rather than only on a build large enough to
fill a megabyte.
"""
import os
import re
import shutil
import subprocess
import textwrap

import pytest

from tools.bst_native_build_tracer import _HOOK_C, parse_open_records

pytestmark = pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("gcc") is None,
    reason="no C compiler on PATH",
)

# UX-56 added `inv=` between the element and the counts; optional here
# so this reads a pre-UX-56 header too.
HEADER_RE = re.compile(
    r"^OPENS pid=(\d+) element=(\S+)(?: inv=\S+)? unique=(\d+) dropped=(\d+) part=(\d+)$"
)


def _build_hook(tmp_path, slots, arena_bytes):
    cc = shutil.which("cc") or shutil.which("gcc")
    hook_so = tmp_path / "hook.so"
    subprocess.run(
        [cc, "-shared", "-fPIC", "-O2", "-Wall", "-Wextra",
         f"-DOPEN_SLOTS={slots}", f"-DOPEN_ARENA_BYTES={arena_bytes}",
         "-o", str(hook_so), _HOOK_C, "-ldl"],
        check=True, capture_output=True, text=True,
    )
    return hook_so


def _run_opener(tmp_path, hook_so, n_paths):
    """Open `n_paths` distinct absolute paths under the hook and return
    the trace log's text."""
    files = tmp_path / "files"
    files.mkdir()
    for i in range(n_paths):
        (files / f"a-rather-long-file-name-so-the-arena-fills-{i:04d}.txt").write_text("x")

    script = tmp_path / "opener.py"
    script.write_text(textwrap.dedent(f"""
        import glob
        for p in sorted(glob.glob({str(files)!r} + "/*.txt")):
            open(p).close()
    """))

    trace_log = tmp_path / "trace.log"
    env = dict(os.environ)
    env["LD_PRELOAD"] = str(hook_so)
    env["BST_TRACE_LOG"] = str(trace_log)
    env["BST_TRACE_OPENS"] = "1"
    env["BST_TRACE_ELEMENT"] = "probe.bst"
    subprocess.run(["python3", str(script)], env=env, check=True, capture_output=True)
    return trace_log.read_text(errors="replace")


def test_a_window_that_fills_flushes_instead_of_dropping(tmp_path):
    text = _run_opener(tmp_path, _build_hook(tmp_path, 16, 256), 60)

    headers = [HEADER_RE.match(line) for line in text.splitlines()]
    headers = [h for h in headers if h]

    assert len(headers) > 1, "a tiny window must have flushed more than once"
    assert all(int(h.group(4)) == 0 for h in headers), "nothing may be dropped"


def test_the_windows_are_numbered_in_order(tmp_path):
    text = _run_opener(tmp_path, _build_hook(tmp_path, 16, 256), 60)

    parts = [int(h.group(5)) for line in text.splitlines()
             if (h := HEADER_RE.match(line))]

    assert parts == sorted(parts)
    assert parts[0] == 0


def test_every_opened_path_survives_the_flushes(tmp_path):
    """The property that matters: windowing must lose nothing. The
    parser unions across windows, so a path recorded twice is harmless
    and a path recorded zero times is the bug."""
    n = 60
    text = _run_opener(tmp_path, _build_hook(tmp_path, 16, 256), n)

    recorded = parse_open_records(text)["probe.bst"]
    probe_paths = {p for p in recorded["paths"] if "a-rather-long-file-name" in p}

    assert len(probe_paths) == n
    assert recorded["dropped"] == 0
    assert recorded["windows"] > 1


def test_a_generous_window_never_flushes(tmp_path):
    """The common case, and the reason the budgets were also raised: a
    real examples/06 capture averages 32 paths and 1.4 KiB per process,
    so ordinary processes must still write exactly one window."""
    text = _run_opener(tmp_path, _build_hook(tmp_path, 32768, 1048576), 60)

    parts = [int(h.group(5)) for line in text.splitlines()
             if (h := HEADER_RE.match(line))]

    assert parts == [0]


def test_one_process_flushing_repeatedly_is_still_one_process(tmp_path):
    """Counting blocks would have reported a single busy compiler as
    dozens of processes."""
    text = _run_opener(tmp_path, _build_hook(tmp_path, 16, 256), 60)

    recorded = parse_open_records(text)["probe.bst"]

    assert recorded["processes"] == 1
    assert recorded["windows"] > 1


def test_a_header_without_part_still_parses():
    """Logs captured before UX-57 have no `part=` field at all."""
    text = "OPENS pid=7 element=core.bst unique=1 dropped=3\n/usr/include/stdio.h\n"

    recorded = parse_open_records(text)["core.bst"]

    assert recorded["paths"] == {"/usr/include/stdio.h"}
    assert recorded["dropped"] == 3
    assert recorded["processes"] == 1


def test_drops_are_not_multiplied_by_the_window_count():
    """`dropped` is a running per-process total re-reported in every
    window, so summing the blocks would multiply one process's drops by
    how many times it happened to flush."""
    text = (
        "OPENS pid=7 element=core.bst unique=1 dropped=2 part=0\n/a\n"
        "OPENS pid=7 element=core.bst unique=1 dropped=5 part=1\n/b\n"
        "OPENS pid=8 element=core.bst unique=1 dropped=1 part=0\n/c\n"
    )

    recorded = parse_open_records(text)["core.bst"]

    assert recorded["dropped"] == 6  # pid 7 contributes 5, pid 8 contributes 1
    assert recorded["processes"] == 2
