"""UX-865: a relative open is recorded against its opener's cwd.

The hook drops relative opens - it does not know the opener's cwd, and
`compute_declared_vs_used` matches exact absolute strings against `bst
artifact list-contents`. A compiler handed `-I../staged/include` opens
`../staged/include/foo.h`, and without the join that read is lost, so a
genuinely-used dependency reads as unused.

These tests compile the real `hook.c` and run a real child process
under it, so the join - and its invalidation on `chdir` - runs for
real rather than only being reasoned about.
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

HEADER_RE = re.compile(
    r"^OPENS pid=(\d+) element=(\S+)(?: inv=\S+)? unique=(\d+) dropped=(\d+)"
    r"(?: part=(\d+))?(?: relative=(\d+))?(?: dirfd=(\d+))?$"
)


def _build_hook(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc")
    hook_so = tmp_path / "hook.so"
    subprocess.run(
        [cc, "-shared", "-fPIC", "-O2", "-Wall", "-Wextra",
         "-o", str(hook_so), _HOOK_C, "-ldl"],
        check=True, capture_output=True, text=True,
    )
    return hook_so


def _run_chdir_opener(tmp_path, hook_so, script):
    trace_log = tmp_path / "trace.log"
    env = dict(os.environ)
    env["LD_PRELOAD"] = str(hook_so)
    env["BST_TRACE_LOG"] = str(trace_log)
    env["BST_TRACE_OPENS"] = "1"
    env["BST_TRACE_ELEMENT"] = "probe.bst"
    script_path = tmp_path / "opener.py"
    script_path.write_text(script)
    subprocess.run(["python3", str(script_path)], env=env, check=True,
                    capture_output=True, text=True)
    return trace_log.read_text(errors="replace")


def test_a_relative_open_is_recorded_absolute_with_relative_1(tmp_path):
    """`chdir` to a scratch dir, open `../include/foo.h` - the joined
    absolute path must be in the record, and `relative=1` must say so."""
    (tmp_path / "include").mkdir()
    (tmp_path / "include" / "foo.h").write_text("// foo\n")
    build_dir = tmp_path / "build"
    build_dir.mkdir()

    text = _run_chdir_opener(tmp_path, _build_hook(tmp_path), textwrap.dedent(f"""
        import os
        os.chdir({str(build_dir)!r})
        open("../include/foo.h").close()
    """))

    parsed = parse_open_records(text)["probe.bst"]
    # `getcwd()` (what the hook joins against) is kernel-canonical, so
    # the expectation is built the same way - `realpath` the cwd, then
    # collapse `..` purely lexically, matching the hook's own join.
    expected = os.path.normpath(
        os.path.join(os.path.realpath(str(build_dir)), "../include/foo.h"))
    assert expected in parsed["paths"]
    assert parsed["relative"] == 1

    headers = [h for h in (HEADER_RE.match(l) for l in text.splitlines()) if h]
    assert headers[-1].group(6) == "1"  # relative= in the raw record


def test_a_second_chdir_joins_against_the_new_cwd(tmp_path):
    """After a second `chdir`, a relative open must join against the
    *new* cwd, not the first one - the cached cwd has to be invalidated,
    not merely reused."""
    (tmp_path / "a" / "include").mkdir(parents=True)
    (tmp_path / "a" / "build").mkdir()
    (tmp_path / "a" / "include" / "foo.h").write_text("// foo\n")
    (tmp_path / "b" / "include").mkdir(parents=True)
    (tmp_path / "b" / "build").mkdir()
    (tmp_path / "b" / "include" / "bar.h").write_text("// bar\n")

    text = _run_chdir_opener(tmp_path, _build_hook(tmp_path), textwrap.dedent(f"""
        import os
        os.chdir({str(tmp_path / "a" / "build")!r})
        open("../include/foo.h").close()
        os.chdir({str(tmp_path / "b" / "build")!r})
        open("../include/bar.h").close()
    """))

    parsed = parse_open_records(text)["probe.bst"]
    expected_foo = os.path.normpath(os.path.join(
        os.path.realpath(str(tmp_path / "a" / "build")), "../include/foo.h"))
    expected_bar = os.path.normpath(os.path.join(
        os.path.realpath(str(tmp_path / "b" / "build")), "../include/bar.h"))
    assert expected_foo in parsed["paths"]
    assert expected_bar in parsed["paths"]
    assert parsed["relative"] == 2


def test_fchdir_also_joins_against_the_new_cwd(tmp_path):
    """`chdir`'s twin - `fchdir`'s own invalidation had no case."""
    (tmp_path / "a" / "include").mkdir(parents=True)
    (tmp_path / "a" / "build").mkdir()
    (tmp_path / "a" / "include" / "foo.h").write_text("// foo\n")
    (tmp_path / "b" / "include").mkdir(parents=True)
    (tmp_path / "b" / "build").mkdir()
    (tmp_path / "b" / "include" / "bar.h").write_text("// bar\n")

    text = _run_chdir_opener(tmp_path, _build_hook(tmp_path), textwrap.dedent(f"""
        import os
        os.chdir({str(tmp_path / "a" / "build")!r})
        open("../include/foo.h").close()
        fd = os.open({str(tmp_path / "b" / "build")!r}, os.O_RDONLY)
        os.fchdir(fd)
        os.close(fd)
        open("../include/bar.h").close()
    """))

    parsed = parse_open_records(text)["probe.bst"]
    expected_foo = os.path.normpath(os.path.join(
        os.path.realpath(str(tmp_path / "a" / "build")), "../include/foo.h"))
    expected_bar = os.path.normpath(os.path.join(
        os.path.realpath(str(tmp_path / "b" / "build")), "../include/bar.h"))
    assert expected_foo in parsed["paths"]
    assert expected_bar in parsed["paths"]
    assert parsed["relative"] == 2


def test_openat_on_a_real_dirfd_is_counted_not_joined(tmp_path):
    """`openat`'s `dirfd` is only in play when the path is relative and
    the fd is not `AT_FDCWD` - resolving what directory a real fd names
    needs a `/proc/self/fd/N` lookup, out of scope. It must be counted
    in `dirfd=` and never joined against the process's own cwd, which
    would silently name the wrong file."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "foo.h").write_text("// foo\n")
    build_dir = tmp_path / "build"
    build_dir.mkdir()  # no foo.h here - a wrong join would still record it

    text = _run_chdir_opener(tmp_path, _build_hook(tmp_path), textwrap.dedent(f"""
        import os
        os.chdir({str(build_dir)!r})
        fd = os.open({str(elsewhere)!r}, os.O_RDONLY)
        os.open("foo.h", os.O_RDONLY, dir_fd=fd)
        os.close(fd)
    """))

    parsed = parse_open_records(text)["probe.bst"]
    wrong_join = os.path.join(os.path.realpath(str(build_dir)), "foo.h")
    assert wrong_join not in parsed["paths"]
    assert parsed.get("relative", 0) == 0

    headers = [h for h in (HEADER_RE.match(l) for l in text.splitlines()) if h]
    assert headers[-1].group(7) == "1"  # dirfd= in the raw record


def test_a_deleted_cwd_is_dropped_not_crashed(tmp_path):
    """`getcwd` fails with ENOENT once the cwd itself has been unlinked
    - real for a build directory removed mid-build, not hypothetical.
    The open must be counted in `dropped` (the same bucket the arena-
    overflow case already uses, so a truncated read set is refused the
    same way), and the process must not crash."""
    doomed = tmp_path / "doomed"
    doomed.mkdir()

    text = _run_chdir_opener(tmp_path, _build_hook(tmp_path), textwrap.dedent(f"""
        import os
        os.chdir({str(doomed)!r})
        os.rmdir({str(doomed)!r})
        try:
            open("foo.h").close()
        except OSError:
            pass
    """))

    parsed = parse_open_records(text)["probe.bst"]
    assert parsed["dropped"] == 1
